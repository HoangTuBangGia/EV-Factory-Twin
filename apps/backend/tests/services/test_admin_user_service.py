from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest
from conftest import make_test_user
from ev_twin_api.schemas.admin import AdminInviteRequest, AdminUser, AdminUserUpdate
from ev_twin_api.schemas.auth import AppRole
from ev_twin_api.services.admin_user_service import (
    AdminUserChange,
    AdminUserService,
    InvitedIdentity,
    UserAdministrationUnavailableError,
)
from ev_twin_api.services.websocket_manager import WebSocketManager

ADMIN = make_test_user(AppRole.ADMIN)
TARGET_ID = UUID("00000000-0000-0000-0000-000000000008")
CREATED_AT = datetime(2026, 8, 14, 3, 0, tzinfo=UTC)


def user(*, active: bool = True, role: AppRole = AppRole.DESIGNER) -> AdminUser:
    return AdminUser(
        id=TARGET_ID,
        email="user@example.com",
        display_name="Factory User",
        role=role,
        is_active=active,
        created_at=CREATED_AT,
    )


class StubRepository:
    def __init__(self) -> None:
        self.users = [user()]
        self.update_error: Exception | None = None
        self.update_calls: list[tuple[UUID, AdminUserUpdate]] = []
        self.activation_calls: list[tuple[InvitedIdentity, AdminInviteRequest]] = []

    async def list(self) -> list[AdminUser]:
        return self.users

    async def update(self, user_id: UUID, update: AdminUserUpdate, **_: object) -> AdminUserChange:
        self.update_calls.append((user_id, update))
        if self.update_error is not None:
            raise self.update_error
        before = self.users[0]
        after = before.model_copy(
            update={
                "role": update.role or before.role,
                "is_active": (
                    update.is_active if update.is_active is not None else before.is_active
                ),
            }
        )
        self.users = [after]
        return AdminUserChange(before=before, after=after)

    async def activate_invited_user(
        self,
        identity: InvitedIdentity,
        invite: AdminInviteRequest,
        **_: object,
    ) -> AdminUser:
        self.activation_calls.append((identity, invite))
        invited = AdminUser(
            id=identity.id,
            email=identity.email,
            display_name=invite.display_name,
            role=invite.role,
            is_active=True,
            created_at=CREATED_AT,
        )
        self.users = [invited]
        return invited


class StubInvitations:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def invite(self, *, email: str, display_name: str) -> InvitedIdentity:
        self.calls.append((email, display_name))
        return InvitedIdentity(id=TARGET_ID, email=email)


class RecordingWebSocketManager:
    def __init__(self) -> None:
        self.disconnected: list[tuple[UUID, str]] = []

    async def disconnect_user(self, user_id: UUID, *, reason: str, **_: object) -> None:
        self.disconnected.append((user_id, reason))


def service(
    repository: StubRepository,
    *,
    invitations: StubInvitations | None = None,
    manager: RecordingWebSocketManager | None = None,
) -> AdminUserService:
    return AdminUserService(
        repository=repository,
        invitations=invitations,
        websocket_manager=cast(WebSocketManager, manager or RecordingWebSocketManager()),
    )


@pytest.mark.asyncio
async def test_disabling_user_disconnects_websocket_only_after_repository_succeeds() -> None:
    repository = StubRepository()
    manager = RecordingWebSocketManager()
    admin_service = service(repository, manager=manager)

    updated = await admin_service.update(
        TARGET_ID,
        AdminUserUpdate(is_active=False),
        actor=ADMIN,
    )

    assert updated.is_active is False
    assert manager.disconnected == [(TARGET_ID, "Account disabled by administrator")]


@pytest.mark.asyncio
async def test_failed_update_does_not_disconnect_websocket() -> None:
    repository = StubRepository()
    repository.update_error = UserAdministrationUnavailableError("database failed")
    manager = RecordingWebSocketManager()
    admin_service = service(repository, manager=manager)

    with pytest.raises(UserAdministrationUnavailableError):
        await admin_service.update(
            TARGET_ID,
            AdminUserUpdate(is_active=False),
            actor=ADMIN,
        )

    assert manager.disconnected == []


@pytest.mark.asyncio
async def test_invite_requires_server_side_gateway_and_activates_profile() -> None:
    repository = StubRepository()
    invite = AdminInviteRequest(
        email="new@example.com",
        display_name="New Monitor",
        role=AppRole.MONITOR,
    )

    with pytest.raises(UserAdministrationUnavailableError, match="not configured"):
        await service(repository).invite(invite, actor=ADMIN)

    gateway = StubInvitations()
    invited = await service(repository, invitations=gateway).invite(invite, actor=ADMIN)

    assert gateway.calls == [("new@example.com", "New Monitor")]
    assert repository.activation_calls[0][0].id == TARGET_ID
    assert invited.role == AppRole.MONITOR
    assert invited.is_active is True
