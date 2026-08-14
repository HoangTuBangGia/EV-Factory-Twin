import asyncio
import time
from collections.abc import Callable, Sequence
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from threading import BoundedSemaphore, Lock
from typing import Any, Protocol, cast
from uuid import UUID

import jwt
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError, PyJWKClientConnectionError, PyJWKClientError, PyJWKSetError


class InvalidAccessTokenError(ValueError):
    pass


class AuthenticationUnavailableError(RuntimeError):
    pass


class SigningKey(Protocol):
    key: Any


class JwksSigningKey(SigningKey, Protocol):
    key_id: str | None


class SigningKeyProvider(Protocol):
    def get_signing_key_from_jwt(self, token: str) -> SigningKey: ...


class JwksClient(Protocol):
    def get_signing_keys(self, refresh: bool = False) -> Sequence[JwksSigningKey]: ...


@dataclass(frozen=True)
class VerifiedIdentity:
    id: UUID
    email: str
    expires_at: int


class BoundedVerificationExecutor:
    """Thread executor with non-blocking bounded admission."""

    def __init__(self, *, max_workers: int, max_in_flight: int) -> None:
        if max_workers < 1:
            raise ValueError("JWT verification workers must be at least one")
        if max_in_flight < max_workers:
            raise ValueError("JWT verification in-flight limit must be at least the worker count")
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="jwt-jwks",
        )
        self._slots = BoundedSemaphore(max_in_flight)

    def submit(
        self,
        verifier: Callable[[str], VerifiedIdentity],
        token: str,
    ) -> Future[VerifiedIdentity]:
        if not self._slots.acquire(blocking=False):
            raise AuthenticationUnavailableError("JWT verification is overloaded")
        try:
            verification = self._executor.submit(verifier, token)
        except RuntimeError as error:
            self._slots.release()
            raise AuthenticationUnavailableError("JWT verification is unavailable") from error

        # Cancellation can remove queued work or abandon a running thread, but
        # its slot is released only when that concurrent work is truly done.
        verification.add_done_callback(self._release_slot)
        return verification

    def _release_slot(self, _: Future[VerifiedIdentity]) -> None:
        self._slots.release()

    def close(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)


class PyJwksClientAdapter:
    """Expose PyJWT's key objects through the local structural contract."""

    def __init__(self, client: PyJWKClient) -> None:
        self._client = client

    def get_signing_keys(self, refresh: bool = False) -> Sequence[JwksSigningKey]:
        # PyJWK exposes both ``key`` and ``key_id``. Keep the third-party
        # structural cast inside this small adapter instead of leaking it into
        # the refresh and verifier logic.
        return cast(
            Sequence[JwksSigningKey],
            self._client.get_signing_keys(refresh=refresh),
        )


class RefreshControlledJwksProvider:
    """Cache JWKS keys while rate-limiting refreshes caused by unknown kids.

    PyJWKClient normally refreshes the remote JWKS once for every unknown
    ``kid``. An attacker can therefore turn unsigned random headers into
    outbound HTTPS requests. This provider owns the key snapshot and permits
    at most one refresh attempt per global cooldown. A genuine rotated key is
    discovered by the first request after that short cooldown.
    """

    def __init__(
        self,
        client: JwksClient,
        *,
        cache_ttl_seconds: float,
        unknown_kid_refresh_cooldown_seconds: float,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if cache_ttl_seconds <= 0:
            raise ValueError("JWKS cache TTL must be greater than zero")
        if unknown_kid_refresh_cooldown_seconds <= 0:
            raise ValueError("JWKS refresh cooldown must be greater than zero")
        self._client = client
        self._cache_ttl_seconds = cache_ttl_seconds
        self._refresh_cooldown_seconds = unknown_kid_refresh_cooldown_seconds
        self._monotonic = monotonic
        self._keys: dict[str, JwksSigningKey] = {}
        self._loaded_at: float | None = None
        self._last_refresh_attempt_at: float | None = None
        self._last_refresh_was_unavailable = False
        self._lock = Lock()

    def get_signing_key_from_jwt(self, token: str) -> JwksSigningKey:
        kid = _validated_token_header(token)["kid"]
        assert isinstance(kid, str)

        with self._lock:
            now = self._monotonic()
            cached_key = self._keys.get(kid)
            cache_is_fresh = (
                self._loaded_at is not None and now - self._loaded_at < self._cache_ttl_seconds
            )
            if cached_key is not None and cache_is_fresh:
                return cached_key

            if (
                self._last_refresh_attempt_at is not None
                and now - self._last_refresh_attempt_at < self._refresh_cooldown_seconds
            ):
                if self._last_refresh_was_unavailable:
                    raise PyJWKClientConnectionError(
                        "JWKS refresh is cooling down after a connection failure"
                    )
                raise PyJWKClientError("No matching signing key in the cached JWKS")

            # Record the attempt before performing I/O. Failed endpoints are
            # rate-limited too, preventing retry storms while Supabase is down.
            self._last_refresh_attempt_at = now
            try:
                signing_keys = self._client.get_signing_keys(refresh=True)
            except (PyJWKClientConnectionError, PyJWKSetError):
                self._last_refresh_was_unavailable = True
                raise
            except PyJWKClientError:
                self._last_refresh_was_unavailable = False
                raise

            self._last_refresh_was_unavailable = False
            self._keys = {
                signing_key.key_id: signing_key
                for signing_key in signing_keys
                if isinstance(signing_key.key_id, str) and signing_key.key_id
            }
            self._loaded_at = self._monotonic()
            signing_key = self._keys.get(kid)
            if signing_key is None:
                raise PyJWKClientError("No matching signing key in the refreshed JWKS")
            return signing_key


def _validated_token_header(token: str) -> dict[str, object]:
    try:
        header = cast(dict[str, object], jwt.get_unverified_header(token))
    except (InvalidTokenError, ValueError, TypeError) as error:
        raise InvalidAccessTokenError("invalid access token header") from error

    algorithm = header.get("alg")
    kid = header.get("kid")
    if algorithm not in JwtVerifier.ALGORITHMS:
        raise InvalidAccessTokenError("access token uses an unsupported algorithm")
    if not isinstance(kid, str) or not kid or len(kid) > 256:
        raise InvalidAccessTokenError("access token has an invalid signing key id")
    return header


class JwtVerifier:
    """Verify Supabase access tokens against a cached JWKS signing key."""

    ALGORITHMS = ("ES256", "RS256")

    def __init__(
        self,
        *,
        issuer: str,
        audience: str,
        jwks_url: str,
        jwks_cache_ttl_seconds: int = 3600,
        leeway_seconds: int = 30,
        jwks_request_timeout_seconds: float = 5.0,
        unknown_kid_refresh_cooldown_seconds: float = 30.0,
        verification_max_workers: int = 4,
        verification_max_in_flight: int = 32,
        signing_key_provider: SigningKeyProvider | None = None,
        jwks_client: JwksClient | None = None,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if signing_key_provider is not None and jwks_client is not None:
            raise ValueError("configure either a signing key provider or a JWKS client, not both")
        if verification_max_workers < 1:
            raise ValueError("JWT verification workers must be at least one")
        if verification_max_in_flight < verification_max_workers:
            raise ValueError("JWT verification in-flight limit must be at least the worker count")
        if jwks_request_timeout_seconds <= 0:
            raise ValueError("JWKS request timeout must be greater than zero")

        self._issuer = issuer
        self._audience = audience
        self._leeway_seconds = leeway_seconds
        self._executor: BoundedVerificationExecutor | None = None
        if signing_key_provider is not None:
            self._signing_key_provider = signing_key_provider
        else:
            client: JwksClient
            if jwks_client is not None:
                client = jwks_client
            else:
                client = PyJwksClientAdapter(
                    PyJWKClient(
                        jwks_url,
                        cache_keys=False,
                        cache_jwk_set=False,
                        timeout=jwks_request_timeout_seconds,
                    )
                )
            self._signing_key_provider = RefreshControlledJwksProvider(
                client,
                cache_ttl_seconds=jwks_cache_ttl_seconds,
                unknown_kid_refresh_cooldown_seconds=(unknown_kid_refresh_cooldown_seconds),
                monotonic=monotonic,
            )
            # PyJWKClient performs a blocking HTTPS fetch on a cache miss. A
            # dedicated executor keeps that work off FastAPI's event loop and
            # avoids coupling authentication to the process-wide executor. A
            # non-blocking admission semaphore bounds both running and queued
            # work so ThreadPoolExecutor's unbounded internal queue is never
            # exposed to unauthenticated input.
            self._executor = BoundedVerificationExecutor(
                max_workers=verification_max_workers,
                max_in_flight=verification_max_in_flight,
            )

    async def verify(self, token: str) -> VerifiedIdentity:
        if self._executor is None:
            # Injected providers are used by deterministic, network-free tests.
            return self._verify_sync(token)

        verification = self._executor.submit(self._verify_sync, token)
        return await asyncio.wrap_future(verification)

    def close(self) -> None:
        if self._executor is not None:
            self._executor.close()

    def _verify_sync(self, token: str) -> VerifiedIdentity:
        try:
            _validated_token_header(token)
            signing_key = self._signing_key_provider.get_signing_key_from_jwt(token)
            payload = cast(
                dict[str, object],
                jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=list(self.ALGORITHMS),
                    audience=self._audience,
                    issuer=self._issuer,
                    leeway=self._leeway_seconds,
                    options={"require": ["exp", "iat", "sub", "aud", "iss"]},
                ),
            )
        except (PyJWKClientConnectionError, PyJWKSetError) as error:
            raise AuthenticationUnavailableError("JWT signing keys are unavailable") from error
        except (InvalidTokenError, PyJWKClientError, ValueError, TypeError) as error:
            raise InvalidAccessTokenError("invalid access token") from error

        subject = payload.get("sub")
        email = payload.get("email")
        expires_at = payload.get("exp")
        if not isinstance(subject, str) or not isinstance(email, str) or not email.strip():
            raise InvalidAccessTokenError("access token is missing identity claims")
        if not isinstance(expires_at, int):
            raise InvalidAccessTokenError("access token has an invalid expiry")

        try:
            user_id = UUID(subject)
        except ValueError as error:
            raise InvalidAccessTokenError("access token subject is not a UUID") from error

        return VerifiedIdentity(id=user_id, email=email, expires_at=expires_at)
