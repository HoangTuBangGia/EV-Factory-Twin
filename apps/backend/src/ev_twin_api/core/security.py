import asyncio
import base64
import hashlib
import hmac
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import jwt
from jwt.exceptions import InvalidTokenError


class InvalidAccessTokenError(ValueError):
    pass


class AuthenticationUnavailableError(RuntimeError):
    pass


class InvalidCredentialsError(ValueError):
    pass


@dataclass(frozen=True)
class VerifiedIdentity:
    id: UUID
    email: str
    expires_at: int


class PasswordHasher:
    """Hash passwords with the standard-library scrypt KDF."""

    algorithm = "scrypt"
    n = 2**14
    r = 8
    p = 1
    salt_bytes = 16
    key_bytes = 32

    async def hash(self, password: str) -> str:
        return await asyncio.to_thread(self._hash_sync, password)

    async def verify(self, password: str, encoded: str) -> bool:
        return await asyncio.to_thread(self._verify_sync, password, encoded)

    def _hash_sync(self, password: str) -> str:
        salt = secrets.token_bytes(self.salt_bytes)
        derived = hashlib.scrypt(
            password.encode(), salt=salt, n=self.n, r=self.r, p=self.p, dklen=self.key_bytes
        )
        return "$".join(
            (
                self.algorithm,
                str(self.n),
                str(self.r),
                str(self.p),
                base64.urlsafe_b64encode(salt).decode().rstrip("="),
                base64.urlsafe_b64encode(derived).decode().rstrip("="),
            )
        )

    def _verify_sync(self, password: str, encoded: str) -> bool:
        try:
            algorithm, n, r, p, salt_text, expected_text = encoded.split("$")
            if algorithm != self.algorithm:
                return False
            salt = _decode_base64(salt_text)
            expected = _decode_base64(expected_text)
            parameters = (int(n), int(r), int(p))
            if parameters != (self.n, self.r, self.p):
                return False
            actual = hashlib.scrypt(
                password.encode(),
                salt=salt,
                n=parameters[0],
                r=parameters[1],
                p=parameters[2],
                dklen=len(expected),
            )
        except (ValueError, TypeError):
            return False
        return hmac.compare_digest(actual, expected)


def _decode_base64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class LocalJwtManager:
    algorithm = "HS256"

    def __init__(
        self,
        *,
        secret: str,
        issuer: str,
        audience: str,
        ttl_seconds: int,
        leeway_seconds: int = 30,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if len(secret) < 64:
            raise ValueError("JWT secret must be at least 64 characters")
        self._secret = secret
        self._issuer = issuer
        self._audience = audience
        self._ttl_seconds = ttl_seconds
        self._leeway_seconds = leeway_seconds
        self._clock = clock or (lambda: datetime.now(UTC))

    def issue(self, user_id: UUID, email: str) -> tuple[str, int]:
        issued_at = int(self._clock().timestamp())
        expires_at = issued_at + self._ttl_seconds
        token = jwt.encode(
            {
                "iss": self._issuer,
                "aud": self._audience,
                "sub": str(user_id),
                "email": email,
                "iat": issued_at,
                "exp": expires_at,
                "token_type": "access",
            },
            self._secret,
            algorithm=self.algorithm,
        )
        return token, expires_at

    async def verify(self, token: str) -> VerifiedIdentity:
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self.algorithm],
                audience=self._audience,
                issuer=self._issuer,
                leeway=self._leeway_seconds,
                options={"require": ["exp", "iat", "sub", "aud", "iss", "email"]},
            )
            subject = payload.get("sub")
            email = payload.get("email")
            expires_at = payload.get("exp")
            if payload.get("token_type") != "access":
                raise InvalidAccessTokenError("invalid token type")
            if not isinstance(subject, str) or not isinstance(email, str) or not email.strip():
                raise InvalidAccessTokenError("access token is missing identity claims")
            if not isinstance(expires_at, int):
                raise InvalidAccessTokenError("access token has an invalid expiry")
            user_id = UUID(subject)
        except (InvalidTokenError, ValueError, TypeError) as error:
            raise InvalidAccessTokenError("invalid access token") from error
        return VerifiedIdentity(id=user_id, email=email, expires_at=expires_at)
