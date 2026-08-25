from uuid import UUID

import pytest
from ev_twin_api.core.database import Database
from ev_twin_api.core.security import (
    AuthenticationUnavailableError,
    InvalidCredentialsError,
    LocalJwtManager,
    PasswordHasher,
    VerifiedIdentity,
)
from ev_twin_api.schemas.auth import AppRole
from ev_twin_api.services.auth_service import (
    AuthService,
    ProfileRecord,
    SqlAlchemyUserRepository,
    UserAccessDeniedError,
    UserRecord,
)

USER_ID = UUID("1f5f709d-48f1-47fe-8f8f-7a98a5261312")
SECRET = "test-secret-" * 8


class StubVerifier:
    async def verify(self, token: str) -> VerifiedIdentity:
        assert token == "valid-token"
        return VerifiedIdentity(id=USER_ID, email="user@example.com", expires_at=2_000_000_000)


class StubUsers:
    def __init__(self, profile: ProfileRecord | None, login_user: UserRecord | None = None) -> None:
        self._profile = profile
        self._login_user = login_user

    async def get(self, user_id: UUID) -> ProfileRecord | None:
        assert user_id == USER_ID
        return self._profile

    async def get_by_email(self, email: str) -> UserRecord | None:
        assert email == "user@example.com"
        return self._login_user


def profile(*, active: bool = True, role: AppRole = AppRole.DESIGNER) -> ProfileRecord:
    return ProfileRecord(id=USER_ID, display_name="Scenario Designer", role=role, is_active=active)


async def login_user(*, active: bool = True) -> UserRecord:
    return UserRecord(
        **profile(active=active).__dict__,
        email="user@example.com",
        password_hash=await PasswordHasher().hash("correct password"),
    )


def token_manager() -> LocalJwtManager:
    return LocalJwtManager(
        secret=SECRET,
        issuer="ev-factory-twin",
        audience="ev-factory-twin-browser",
        ttl_seconds=300,
    )


@pytest.mark.asyncio
async def test_builds_current_user_from_verified_token_and_database_profile() -> None:
    service = AuthService(verifier=StubVerifier(), users=StubUsers(profile()))
    session = await service.authenticate("valid-token")
    assert session.user.email == "user@example.com"
    assert session.user.role == AppRole.DESIGNER
    assert session.expires_at == 2_000_000_000


@pytest.mark.asyncio
@pytest.mark.parametrize("stored_profile", [None, profile(active=False)])
async def test_denies_missing_or_inactive_profile(stored_profile: ProfileRecord | None) -> None:
    service = AuthService(verifier=StubVerifier(), users=StubUsers(stored_profile))
    with pytest.raises(UserAccessDeniedError):
        await service.authenticate("valid-token")


@pytest.mark.asyncio
async def test_login_returns_verifiable_token_for_active_user() -> None:
    user = await login_user()
    codec = token_manager()
    service = AuthService(verifier=codec, users=StubUsers(user, user), token_issuer=codec)
    result = await service.login("USER@example.com", "correct password")
    assert result.user.id == USER_ID
    assert (await codec.verify(result.access_token)).id == USER_ID


@pytest.mark.asyncio
async def test_login_rejects_wrong_password_and_inactive_user() -> None:
    active = await login_user()
    inactive = await login_user(active=False)
    codec = token_manager()
    service = AuthService(verifier=codec, users=StubUsers(active, active), token_issuer=codec)
    with pytest.raises(InvalidCredentialsError):
        await service.login("user@example.com", "wrong password")

    service = AuthService(verifier=codec, users=StubUsers(inactive, inactive), token_issuer=codec)
    with pytest.raises(UserAccessDeniedError):
        await service.login("user@example.com", "correct password")


@pytest.mark.asyncio
async def test_missing_jwt_configuration_fails_closed() -> None:
    service = AuthService(verifier=None, users=StubUsers(profile()))
    with pytest.raises(AuthenticationUnavailableError):
        await service.authenticate("some-token")


@pytest.mark.asyncio
async def test_user_repository_without_database_fails_closed() -> None:
    repository = SqlAlchemyUserRepository(Database(None))
    with pytest.raises(AuthenticationUnavailableError):
        await repository.get(USER_ID)
