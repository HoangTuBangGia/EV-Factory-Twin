from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ev_twin_api.core.database import Database, DatabaseNotConfiguredError
from ev_twin_api.core.security import (
    AuthenticationUnavailableError,
    InvalidAccessTokenError,
    InvalidCredentialsError,
    LocalJwtManager,
    PasswordHasher,
    VerifiedIdentity,
)
from ev_twin_api.schemas.auth import AppRole, CurrentUser, LoginResponse


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


@dataclass(frozen=True)
class UserRecord(ProfileRecord):
    email: str
    password_hash: str


class UserRepository(Protocol):
    async def get(self, user_id: UUID) -> ProfileRecord | None: ...
    async def get_by_email(self, email: str) -> UserRecord | None: ...


class IdentityVerifier(Protocol):
    async def verify(self, token: str) -> VerifiedIdentity: ...


class SqlAlchemyUserRepository:
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

    async def get_by_email(self, email: str) -> UserRecord | None:
        try:
            async with self._database.session() as session:
                result = await session.execute(
                    text(
                        """
                        SELECT u.id, u.email, u.password_hash, p.display_name,
                               p.role::text AS role, p.is_active
                        FROM public.app_users AS u
                        JOIN public.profiles AS p ON p.id = u.id
                        WHERE u.email = :email
                        """
                    ),
                    {"email": email},
                )
        except (DatabaseNotConfiguredError, SQLAlchemyError) as error:
            raise AuthenticationUnavailableError("user database is unavailable") from error

        row = result.mappings().one_or_none()
        if row is None:
            return None
        try:
            user_id = row["id"]
            return UserRecord(
                id=user_id if isinstance(user_id, UUID) else UUID(str(user_id)),
                email=str(row["email"]),
                password_hash=str(row["password_hash"]),
                display_name=str(row["display_name"]),
                role=AppRole(str(row["role"])),
                is_active=bool(row["is_active"]),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise AuthenticationUnavailableError("user record is invalid") from error


class AuthService:
    def __init__(
        self,
        *,
        verifier: IdentityVerifier | None,
        users: UserRepository,
        token_issuer: LocalJwtManager | None = None,
        password_hasher: PasswordHasher | None = None,
    ) -> None:
        self._verifier = verifier
        self._users = users
        self._token_issuer = token_issuer
        self._password_hasher = password_hasher or PasswordHasher()

    async def login(self, email: str, password: str) -> LoginResponse:
        if self._token_issuer is None:
            raise AuthenticationUnavailableError("JWT issuance is not configured")
        user = await self._users.get_by_email(email.strip().lower())
        if user is None or not await self._password_hasher.verify(password, user.password_hash):
            raise InvalidCredentialsError("invalid email or password")
        if not user.is_active:
            raise UserAccessDeniedError("user account is not active")
        token, expires_at = self._token_issuer.issue(user.id, user.email)
        return LoginResponse(
            access_token=token,
            expires_at=expires_at,
            user=_current_user(user, user.email),
        )

    async def authenticate(self, token: str | None) -> AuthenticatedSession:
        if token is None or not token.strip():
            raise InvalidAccessTokenError("missing bearer token")
        if self._verifier is None:
            raise AuthenticationUnavailableError("JWT verification is not configured")

        identity = await self._verifier.verify(token)
        profile = await self._users.get(identity.id)
        if profile is None or not profile.is_active:
            raise UserAccessDeniedError("user account is not active")

        return AuthenticatedSession(
            user=_current_user(profile, identity.email), expires_at=identity.expires_at
        )


def _current_user(profile: ProfileRecord, email: str) -> CurrentUser:
    return CurrentUser(
        id=profile.id,
        email=email,
        display_name=profile.display_name,
        role=profile.role,
        is_active=profile.is_active,
    )
