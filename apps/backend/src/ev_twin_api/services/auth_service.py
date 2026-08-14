from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ev_twin_api.core.database import Database, DatabaseNotConfiguredError
from ev_twin_api.core.security import (
    AuthenticationUnavailableError,
    InvalidAccessTokenError,
    VerifiedIdentity,
)
from ev_twin_api.schemas.auth import AppRole, CurrentUser


class UserAccessDeniedError(PermissionError):
    pass


@dataclass(frozen=True)
class AuthenticatedSession:
    user: CurrentUser
    expires_at: int


@dataclass(frozen=True)
class ProfileRecord:
    id: UUID
    display_name: str
    role: AppRole
    is_active: bool


class ProfileRepository(Protocol):
    async def get(self, user_id: UUID) -> ProfileRecord | None: ...


class IdentityVerifier(Protocol):
    async def verify(self, token: str) -> VerifiedIdentity: ...


class SqlAlchemyProfileRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def get(self, user_id: UUID) -> ProfileRecord | None:
        try:
            async with self._database.session() as session:
                result = await session.execute(
                    text(
                        """
                        SELECT id, display_name, role::text AS role, is_active
                        FROM public.profiles
                        WHERE id = :user_id
                        """
                    ),
                    {"user_id": user_id},
                )
        except (DatabaseNotConfiguredError, SQLAlchemyError) as error:
            raise AuthenticationUnavailableError("profile database is unavailable") from error

        row = result.mappings().one_or_none()
        if row is None:
            return None

        try:
            profile_id = row["id"]
            return ProfileRecord(
                id=profile_id if isinstance(profile_id, UUID) else UUID(str(profile_id)),
                display_name=str(row["display_name"]),
                role=AppRole(str(row["role"])),
                is_active=bool(row["is_active"]),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise AuthenticationUnavailableError("profile record is invalid") from error


class AuthService:
    def __init__(
        self,
        *,
        verifier: IdentityVerifier | None,
        profiles: ProfileRepository,
    ) -> None:
        self._verifier = verifier
        self._profiles = profiles

    async def authenticate(self, token: str | None) -> AuthenticatedSession:
        if token is None or not token.strip():
            raise InvalidAccessTokenError("missing bearer token")
        if self._verifier is None:
            raise AuthenticationUnavailableError("JWT verification is not configured")

        identity = await self._verifier.verify(token)
        profile = await self._profiles.get(identity.id)
        if profile is None or not profile.is_active:
            raise UserAccessDeniedError("user account is not active")

        return AuthenticatedSession(
            user=CurrentUser(
                id=profile.id,
                email=identity.email,
                display_name=profile.display_name,
                role=profile.role,
                is_active=profile.is_active,
            ),
            expires_at=identity.expires_at,
        )
