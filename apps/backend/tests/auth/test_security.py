from datetime import UTC, datetime
from uuid import UUID

import jwt
import pytest
from ev_twin_api.core.security import InvalidAccessTokenError, LocalJwtManager, PasswordHasher

SECRET = "test-secret-" * 8
USER_ID = UUID("1f5f709d-48f1-47fe-8f8f-7a98a5261312")


def manager(**overrides: object) -> LocalJwtManager:
    values = {
        "secret": SECRET,
        "issuer": "ev-factory-twin",
        "audience": "ev-factory-twin-browser",
        "ttl_seconds": 300,
        "leeway_seconds": 0,
        **overrides,
    }
    return LocalJwtManager(**values)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_scrypt_hash_is_salted_and_verifiable() -> None:
    hasher = PasswordHasher()
    first = await hasher.hash("correct horse battery staple")
    second = await hasher.hash("correct horse battery staple")
    assert first != second
    assert first.startswith("scrypt$")
    assert await hasher.verify("correct horse battery staple", first)
    assert not await hasher.verify("wrong password", first)
    assert not await hasher.verify("correct horse battery staple", "malformed")


@pytest.mark.asyncio
async def test_issues_and_verifies_local_access_token() -> None:
    codec = manager()
    token, expires_at = codec.issue(USER_ID, "designer@example.com")
    identity = await codec.verify(token)
    assert identity.id == USER_ID
    assert identity.email == "designer@example.com"
    assert identity.expires_at == expires_at


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload_update",
    [
        {"iss": "attacker"},
        {"aud": "attacker"},
        {"sub": "not-a-uuid"},
        {"email": ""},
        {"token_type": "refresh"},
    ],
)
async def test_rejects_invalid_local_claims(payload_update: dict[str, object]) -> None:
    now = int(datetime.now(UTC).timestamp())
    payload = {
        "iss": "ev-factory-twin",
        "aud": "ev-factory-twin-browser",
        "sub": str(USER_ID),
        "email": "designer@example.com",
        "iat": now,
        "exp": now + 300,
        "token_type": "access",
        **payload_update,
    }
    token = jwt.encode(payload, SECRET, algorithm="HS256")
    with pytest.raises(InvalidAccessTokenError):
        await manager().verify(token)


@pytest.mark.asyncio
async def test_rejects_token_signed_by_another_secret() -> None:
    token, _ = manager(secret="attacker-secret-" * 8).issue(USER_ID, "designer@example.com")
    with pytest.raises(InvalidAccessTokenError):
        await manager().verify(token)


def test_rejects_short_signing_secret() -> None:
    with pytest.raises(ValueError, match="at least 64"):
        manager(secret="too-short")
