import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from uuid import UUID, uuid4

from pydantic import SecretStr, ValidationError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ev_twin_api.core.database import Database, DatabaseNotConfiguredError
from ev_twin_api.schemas.admin import AdminInviteRequest, AdminUser, AdminUserUpdate
from ev_twin_api.schemas.audit import AuditAction
from ev_twin_api.schemas.auth import CurrentUser
from ev_twin_api.services.audit_service import PendingAuditEvent, insert_audit_event
from ev_twin_api.services.websocket_manager import WebSocketManager

ADMIN_USER_COLUMNS_SQL = """
profiles.id,
auth_users.email,
profiles.display_name,
profiles.role::text AS role,
profiles.is_active,
profiles.created_at
"""

ADMIN_USERS_SELECT_SQL = f"""
SELECT {ADMIN_USER_COLUMNS_SQL}
FROM public.profiles AS profiles
JOIN auth.users AS auth_users ON auth_users.id = profiles.id
"""

LOCK_ACTIVE_ADMINS_SQL = """
SELECT id
FROM public.profiles
WHERE role = 'ADMIN'::public.app_role
  AND is_active
ORDER BY id
FOR UPDATE
"""

ADMIN_USER_UPDATE_SQL = """
UPDATE public.profiles
SET
    role = CAST(:role AS public.app_role),
    is_active = :is_active
WHERE id = :user_id
"""


class AdminUserNotFoundError(LookupError):
    pass


class LastActiveAdminError(RuntimeError):
    pass


class AdminUserConflictError(RuntimeError):
    pass


class UserAdministrationUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class AdminUserChange:
    before: AdminUser
    after: AdminUser


@dataclass(frozen=True)
class InvitedIdentity:
    id: UUID
    email: str


class AdminUserRepository(Protocol):
    async def list(self) -> list[AdminUser]: ...

    async def update(
        self,
        user_id: UUID,
        update: AdminUserUpdate,
        *,
        actor: CurrentUser,
        request_id: UUID,
        occurred_at: datetime,
    ) -> AdminUserChange: ...

    async def activate_invited_user(
        self,
        identity: InvitedIdentity,
        invite: AdminInviteRequest,
        *,
        actor: CurrentUser,
        request_id: UUID,
        occurred_at: datetime,
    ) -> AdminUser: ...


class UserInvitationGateway(Protocol):
    async def invite(self, *, email: str, display_name: str) -> InvitedIdentity: ...


def _admin_user_from_mapping(row: Any) -> AdminUser:
    try:
        return AdminUser.model_validate(dict(row))
    except (TypeError, ValueError, ValidationError) as error:
        raise UserAdministrationUnavailableError("admin user record is invalid") from error


def _user_audit_data(user: AdminUser) -> dict[str, Any]:
    return user.model_dump(mode="json")


def _audit_event(
    *,
    actor: CurrentUser,
    action: AuditAction,
    before: AdminUser | None,
    after: AdminUser,
    request_id: UUID,
    occurred_at: datetime,
) -> PendingAuditEvent:
    return PendingAuditEvent(
        actor_id=actor.id,
        actor_role=actor.role,
        action=action,
        resource_type="user",
        resource_id=str(after.id),
        before_data=_user_audit_data(before) if before is not None else None,
        after_data=_user_audit_data(after),
        request_id=request_id,
        created_at=occurred_at,
    )


class SqlAlchemyAdminUserRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def list(self) -> list[AdminUser]:
        try:
            async with self._database.session() as session:
                result = await session.execute(
                    text(f"{ADMIN_USERS_SELECT_SQL} ORDER BY profiles.created_at DESC")
                )
        except (DatabaseNotConfiguredError, SQLAlchemyError) as error:
            raise UserAdministrationUnavailableError(
                "admin user database is unavailable"
            ) from error
        return [_admin_user_from_mapping(row) for row in result.mappings().all()]

    async def update(
        self,
        user_id: UUID,
        update: AdminUserUpdate,
        *,
        actor: CurrentUser,
        request_id: UUID,
        occurred_at: datetime,
    ) -> AdminUserChange:
        try:
            async with self._database.session() as session, session.begin():
                active_admin_result = await session.execute(text(LOCK_ACTIVE_ADMINS_SQL))
                active_admin_ids = {
                    UUID(str(row["id"])) for row in active_admin_result.mappings().all()
                }
                target_result = await session.execute(
                    text(
                        f"{ADMIN_USERS_SELECT_SQL} WHERE profiles.id = :user_id "
                        "FOR UPDATE OF profiles"
                    ),
                    {"user_id": user_id},
                )
                target_row = target_result.mappings().one_or_none()
                if target_row is None:
                    raise AdminUserNotFoundError(f"User '{user_id}' not found")
                before = _admin_user_from_mapping(target_row)
                after = before.model_copy(
                    update={
                        "role": update.role if update.role is not None else before.role,
                        "is_active": (
                            update.is_active if update.is_active is not None else before.is_active
                        ),
                    }
                )

                removes_active_admin = (
                    before.role.value == "ADMIN"
                    and before.is_active
                    and (after.role.value != "ADMIN" or not after.is_active)
                )
                if removes_active_admin and len(active_admin_ids) == 1:
                    raise LastActiveAdminError(
                        "The final active administrator cannot be disabled or demoted"
                    )

                if after == before:
                    return AdminUserChange(before=before, after=after)

                # Audit before the profile update. The database trigger snapshots
                # the actor's current authoritative role and requires an active
                # profile, including when an admin changes their own account.
                if before.role != after.role:
                    await insert_audit_event(
                        session,
                        _audit_event(
                            actor=actor,
                            action=AuditAction.ROLE_CHANGED,
                            before=before,
                            after=after,
                            request_id=request_id,
                            occurred_at=occurred_at,
                        ),
                    )
                if before.is_active != after.is_active:
                    action = (
                        AuditAction.USER_ENABLED if after.is_active else AuditAction.USER_DISABLED
                    )
                    await insert_audit_event(
                        session,
                        _audit_event(
                            actor=actor,
                            action=action,
                            before=before,
                            after=after,
                            request_id=request_id,
                            occurred_at=occurred_at,
                        ),
                    )

                await session.execute(
                    text(ADMIN_USER_UPDATE_SQL),
                    {
                        "user_id": user_id,
                        "role": after.role.value,
                        "is_active": after.is_active,
                    },
                )
        except (AdminUserNotFoundError, LastActiveAdminError):
            raise
        except (DatabaseNotConfiguredError, SQLAlchemyError) as error:
            raise UserAdministrationUnavailableError(
                "admin user database is unavailable"
            ) from error
        return AdminUserChange(before=before, after=after)

    async def activate_invited_user(
        self,
        identity: InvitedIdentity,
        invite: AdminInviteRequest,
        *,
        actor: CurrentUser,
        request_id: UUID,
        occurred_at: datetime,
    ) -> AdminUser:
        try:
            async with self._database.session() as session, session.begin():
                target_result = await session.execute(
                    text(
                        f"{ADMIN_USERS_SELECT_SQL} WHERE profiles.id = :user_id "
                        "FOR UPDATE OF profiles"
                    ),
                    {"user_id": identity.id},
                )
                target_row = target_result.mappings().one_or_none()
                if target_row is None:
                    raise UserAdministrationUnavailableError(
                        "invited user profile was not provisioned"
                    )
                before = _admin_user_from_mapping(target_row)
                if before.email.casefold() != identity.email.casefold():
                    raise UserAdministrationUnavailableError(
                        "invited user identity does not match its profile"
                    )
                after = before.model_copy(
                    update={
                        "email": identity.email.casefold(),
                        "display_name": invite.display_name,
                        "role": invite.role,
                        "is_active": True,
                    }
                )
                await insert_audit_event(
                    session,
                    _audit_event(
                        actor=actor,
                        action=AuditAction.USER_INVITED,
                        before=None,
                        after=after,
                        request_id=request_id,
                        occurred_at=occurred_at,
                    ),
                )
                await session.execute(
                    text(
                        """
                        UPDATE public.profiles
                        SET
                            display_name = :display_name,
                            role = CAST(:role AS public.app_role),
                            is_active = true
                        WHERE id = :user_id
                        """
                    ),
                    {
                        "user_id": identity.id,
                        "display_name": invite.display_name,
                        "role": invite.role.value,
                    },
                )
        except UserAdministrationUnavailableError:
            raise
        except (DatabaseNotConfiguredError, SQLAlchemyError) as error:
            raise UserAdministrationUnavailableError(
                "admin user database is unavailable"
            ) from error
        return after


class SupabaseUserInvitationGateway:
    """Minimal server-side client for Supabase Auth's invite endpoint."""

    def __init__(
        self,
        *,
        supabase_url: str,
        service_role_key: SecretStr,
        timeout_seconds: float = 10.0,
    ) -> None:
        parsed_url = urlsplit(supabase_url)
        local_hosts = {"localhost", "127.0.0.1", "::1"}
        if (
            parsed_url.scheme not in {"http", "https"}
            or not parsed_url.hostname
            or parsed_url.username is not None
            or parsed_url.password is not None
            or parsed_url.query
            or parsed_url.fragment
            or (parsed_url.scheme == "http" and parsed_url.hostname not in local_hosts)
        ):
            raise ValueError("SUPABASE_URL must be an HTTPS URL or a local HTTP URL")
        if not 0.1 <= timeout_seconds <= 30:
            raise ValueError("Supabase invitation timeout must be between 0.1 and 30 seconds")
        self._endpoint = f"{supabase_url.rstrip('/')}/auth/v1/invite"
        self._service_role_key = service_role_key
        self._timeout_seconds = timeout_seconds

    async def invite(self, *, email: str, display_name: str) -> InvitedIdentity:
        return await asyncio.to_thread(
            self._invite_sync,
            email=email,
            display_name=display_name,
        )

    def _invite_sync(self, *, email: str, display_name: str) -> InvitedIdentity:
        service_role_key = self._service_role_key.get_secret_value()
        request = Request(
            self._endpoint,
            data=json.dumps(
                {
                    "email": email,
                    "data": {"display_name": display_name},
                }
            ).encode(),
            headers={
                "Authorization": f"Bearer {service_role_key}",
                "apikey": service_role_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                payload = json.loads(response.read())
        except HTTPError as error:
            if error.code in {400, 409, 422}:
                raise AdminUserConflictError("Supabase could not invite that email") from error
            raise UserAdministrationUnavailableError(
                "Supabase user invitation is unavailable"
            ) from error
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
            raise UserAdministrationUnavailableError(
                "Supabase user invitation is unavailable"
            ) from error

        user_payload = payload.get("user", payload) if isinstance(payload, dict) else {}
        try:
            invited_id = UUID(str(user_payload["id"]))
            invited_email = str(user_payload.get("email") or email).casefold()
        except (KeyError, TypeError, ValueError) as error:
            raise UserAdministrationUnavailableError(
                "Supabase returned an invalid invited user"
            ) from error
        return InvitedIdentity(id=invited_id, email=invited_email)


class AdminUserService:
    def __init__(
        self,
        *,
        repository: AdminUserRepository,
        invitations: UserInvitationGateway | None,
        websocket_manager: WebSocketManager,
    ) -> None:
        self._repository = repository
        self._invitations = invitations
        self._websocket_manager = websocket_manager

    async def list(self) -> list[AdminUser]:
        return await self._repository.list()

    async def update(
        self,
        user_id: UUID,
        update: AdminUserUpdate,
        *,
        actor: CurrentUser,
    ) -> AdminUser:
        change = await self._repository.update(
            user_id,
            update,
            actor=actor,
            request_id=uuid4(),
            occurred_at=datetime.now(UTC),
        )
        if change.before.is_active and not change.after.is_active:
            await self._websocket_manager.disconnect_user(
                user_id,
                reason="Account disabled by administrator",
            )
        return change.after

    async def invite(
        self,
        invite: AdminInviteRequest,
        *,
        actor: CurrentUser,
    ) -> AdminUser:
        if self._invitations is None:
            raise UserAdministrationUnavailableError(
                "Supabase service-role invitation is not configured"
            )
        identity = await self._invitations.invite(
            email=invite.email,
            display_name=invite.display_name,
        )
        return await self._repository.activate_invited_user(
            identity,
            invite,
            actor=actor,
            request_id=uuid4(),
            occurred_at=datetime.now(UTC),
        )
