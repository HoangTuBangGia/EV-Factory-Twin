from uuid import UUID

import pytest
from ev_twin_api.core.database import Database
from ev_twin_api.core.security import AuthenticationUnavailableError, VerifiedIdentity
from ev_twin_api.schemas.auth import AppRole
from ev_twin_api.services.auth_service import (
    AuthService,
    ProfileRecord,
    SqlAlchemyProfileRepository,
    UserAccessDeniedError,
)

USER_ID = UUID("1f5f709d-48f1-47fe-8f8f-7a98a5261312")


class StubVerifier:
    async def verify(self, token: str) -> VerifiedIdentity:
        assert token == "valid-token"
        return VerifiedIdentity(id=USER_ID, email="user@example.com", expires_at=2_000_000_000)


class StubProfiles:
    def __init__(self, profile: ProfileRecord | None) -> None:
        self._profile = profile

    async def get(self, user_id: UUID) -> ProfileRecord | None:
        assert user_id == USER_ID
        return self._profile


def profile(*, active: bool = True, role: AppRole = AppRole.DESIGNER) -> ProfileRecord:
    return ProfileRecord(
        id=USER_ID,
        display_name="Scenario Designer",
        role=role,
        is_active=active,
    )


@pytest.mark.asyncio
async def test_builds_current_user_from_verified_token_and_database_profile() -> None:
    service = AuthService(
        verifier=StubVerifier(),
        profiles=StubProfiles(profile()),
    )

    session = await service.authenticate("valid-token")

    assert session.user.id == USER_ID
    assert session.user.email == "user@example.com"
    assert session.user.display_name == "Scenario Designer"
    assert session.user.role == AppRole.DESIGNER
    assert session.user.is_active is True
    assert session.expires_at == 2_000_000_000


@pytest.mark.asyncio
@pytest.mark.parametrize("stored_profile", [None, profile(active=False)])
async def test_denies_missing_or_inactive_profile(stored_profile: ProfileRecord | None) -> None:
    service = AuthService(
        verifier=StubVerifier(),
        profiles=StubProfiles(stored_profile),
    )

    with pytest.raises(UserAccessDeniedError):
        await service.authenticate("valid-token")


@pytest.mark.asyncio
async def test_missing_jwt_configuration_fails_closed() -> None:
    service = AuthService(verifier=None, profiles=StubProfiles(profile()))

    with pytest.raises(AuthenticationUnavailableError):
        await service.authenticate("some-token")


@pytest.mark.asyncio
async def test_profile_repository_without_database_fails_closed() -> None:
    repository = SqlAlchemyProfileRepository(Database(None))

    with pytest.raises(AuthenticationUnavailableError):
        await repository.get(USER_ID)
