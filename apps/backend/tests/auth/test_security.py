import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Event
from typing import Any
from uuid import UUID

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from ev_twin_api.core.security import (
    AuthenticationUnavailableError,
    BoundedVerificationExecutor,
    InvalidAccessTokenError,
    JwtVerifier,
    RefreshControlledJwksProvider,
    VerifiedIdentity,
)
from jwt.exceptions import PyJWKSetError

ISSUER = "https://project.supabase.co/auth/v1"
AUDIENCE = "authenticated"
USER_ID = UUID("1f5f709d-48f1-47fe-8f8f-7a98a5261312")


@dataclass
class StaticSigningKey:
    key: Any
    key_id: str = "test"


class StaticSigningKeyProvider:
    def __init__(self, key: Any) -> None:
        self._key = key

    def get_signing_key_from_jwt(self, token: str) -> StaticSigningKey:
        del token
        return StaticSigningKey(self._key)


class OfflineJwksClient:
    def __init__(self, key_sets: list[list[StaticSigningKey]]) -> None:
        self._key_sets = key_sets
        self.refresh_calls = 0

    def get_signing_keys(self, refresh: bool = False) -> list[StaticSigningKey]:
        assert refresh is True
        index = min(self.refresh_calls, len(self._key_sets) - 1)
        self.refresh_calls += 1
        return self._key_sets[index]


def token_payload(**updates: object) -> dict[str, object]:
    now = int(datetime.now(UTC).timestamp())
    return {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": str(USER_ID),
        "email": "designer@example.com",
        "iat": now - 10,
        "exp": now + 300,
        **updates,
    }


def build_verifier(public_key: Any) -> JwtVerifier:
    return JwtVerifier(
        issuer=ISSUER,
        audience=AUDIENCE,
        jwks_url="https://unused.invalid/jwks.json",
        leeway_seconds=0,
        signing_key_provider=StaticSigningKeyProvider(public_key),
    )


@pytest.mark.asyncio
async def test_verifies_signed_supabase_identity_without_network() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = jwt.encode(token_payload(), private_key, algorithm="RS256", headers={"kid": "test"})

    identity = await build_verifier(private_key.public_key()).verify(token)

    assert identity.id == USER_ID
    assert identity.email == "designer@example.com"
    assert identity.expires_at > int(datetime.now(UTC).timestamp())


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "claim_updates",
    [
        {"iss": "https://attacker.invalid/auth/v1"},
        {"aud": "wrong-audience"},
        {"exp": 1},
        {"sub": "not-a-uuid"},
        {"email": ""},
    ],
)
async def test_rejects_invalid_identity_claims(claim_updates: dict[str, object]) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = jwt.encode(
        token_payload(**claim_updates),
        private_key,
        algorithm="RS256",
        headers={"kid": "test"},
    )

    with pytest.raises(InvalidAccessTokenError):
        await build_verifier(private_key.public_key()).verify(token)


@pytest.mark.asyncio
async def test_rejects_token_signed_by_another_key() -> None:
    trusted_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    attacker_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = jwt.encode(token_payload(), attacker_key, algorithm="RS256", headers={"kid": "test"})

    with pytest.raises(InvalidAccessTokenError):
        await build_verifier(trusted_key.public_key()).verify(token)


async def _exercise_random_kid_refresh_limit() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    client = OfflineJwksClient([[StaticSigningKey(private_key.public_key(), key_id="trusted-key")]])
    provider = RefreshControlledJwksProvider(
        client,
        cache_ttl_seconds=3600,
        unknown_kid_refresh_cooldown_seconds=60,
    )
    verifier = JwtVerifier(
        issuer=ISSUER,
        audience=AUDIENCE,
        jwks_url="https://unused.invalid/jwks.json",
        leeway_seconds=0,
        signing_key_provider=provider,
    )
    random_kid_tokens = [
        jwt.encode(
            token_payload(),
            private_key,
            algorithm="RS256",
            headers={"kid": f"attacker-{index}"},
        )
        for index in range(40)
    ]

    async def rejected(token: str) -> Exception | None:
        try:
            await verifier.verify(token)
        except Exception as error:
            return error
        return None

    try:
        results = [await rejected(token) for token in random_kid_tokens]
        assert all(isinstance(result, InvalidAccessTokenError) for result in results)
        assert client.refresh_calls == 1

        valid_token = jwt.encode(
            token_payload(),
            private_key,
            algorithm="RS256",
            headers={"kid": "trusted-key"},
        )
        identity = await verifier.verify(valid_token)

        assert identity.id == USER_ID
        assert client.refresh_calls == 1
    finally:
        verifier.close()


def test_many_random_kids_force_only_one_refresh_and_cached_key_still_works() -> None:
    asyncio.run(_exercise_random_kid_refresh_limit())


async def _exercise_key_rotation_recovery() -> None:
    old_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    new_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    client = OfflineJwksClient(
        [
            [StaticSigningKey(old_key.public_key(), key_id="old-key")],
            [
                StaticSigningKey(old_key.public_key(), key_id="old-key"),
                StaticSigningKey(new_key.public_key(), key_id="new-key"),
            ],
        ]
    )
    clock = [100.0]
    provider = RefreshControlledJwksProvider(
        client,
        cache_ttl_seconds=3600,
        unknown_kid_refresh_cooldown_seconds=30,
        monotonic=lambda: clock[0],
    )
    verifier = JwtVerifier(
        issuer=ISSUER,
        audience=AUDIENCE,
        jwks_url="https://unused.invalid/jwks.json",
        leeway_seconds=0,
        signing_key_provider=provider,
    )
    old_token = jwt.encode(token_payload(), old_key, algorithm="RS256", headers={"kid": "old-key"})
    new_token = jwt.encode(token_payload(), new_key, algorithm="RS256", headers={"kid": "new-key"})

    try:
        assert (await verifier.verify(old_token)).id == USER_ID
        with pytest.raises(InvalidAccessTokenError):
            await verifier.verify(new_token)
        assert client.refresh_calls == 1

        clock[0] += 31
        assert (await verifier.verify(new_token)).id == USER_ID
        assert client.refresh_calls == 2
    finally:
        verifier.close()


def test_unknown_kid_can_recover_key_rotation_after_global_cooldown() -> None:
    asyncio.run(_exercise_key_rotation_recovery())


def test_verification_overload_fails_closed_without_unbounded_executor_queue() -> None:
    executor = BoundedVerificationExecutor(max_workers=1, max_in_flight=2)
    started = Event()
    release = Event()

    def blocking_verification(_: str) -> VerifiedIdentity:
        started.set()
        if not release.wait(timeout=5):
            raise RuntimeError("test did not release verification")
        return VerifiedIdentity(
            id=USER_ID,
            email="designer@example.com",
            expires_at=2_000_000_000,
        )

    try:
        first = executor.submit(blocking_verification, "first")
        assert started.wait(timeout=1)
        second = executor.submit(blocking_verification, "second")

        with pytest.raises(AuthenticationUnavailableError, match="overloaded"):
            executor.submit(blocking_verification, "must-not-be-queued")

        release.set()
        identities = [first.result(timeout=1), second.result(timeout=1)]
        assert [identity.id for identity in identities] == [USER_ID, USER_ID]
    finally:
        release.set()
        executor.close()


class MalformedJwksClient:
    def __init__(self) -> None:
        self.calls = 0

    def get_signing_keys(self, refresh: bool = False) -> list[StaticSigningKey]:
        assert refresh is True
        self.calls += 1
        raise PyJWKSetError("malformed remote JWKS")


@pytest.mark.asyncio
async def test_malformed_remote_jwks_fails_as_authentication_unavailable() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    client = MalformedJwksClient()
    provider = RefreshControlledJwksProvider(
        client,
        cache_ttl_seconds=3600,
        unknown_kid_refresh_cooldown_seconds=30,
    )
    verifier = JwtVerifier(
        issuer=ISSUER,
        audience=AUDIENCE,
        jwks_url="https://unused.invalid/jwks.json",
        leeway_seconds=0,
        signing_key_provider=provider,
    )
    token = jwt.encode(
        token_payload(), private_key, algorithm="RS256", headers={"kid": "trusted-key"}
    )

    with pytest.raises(AuthenticationUnavailableError):
        await verifier.verify(token)
    with pytest.raises(AuthenticationUnavailableError):
        await verifier.verify(token)
    assert client.calls == 1
