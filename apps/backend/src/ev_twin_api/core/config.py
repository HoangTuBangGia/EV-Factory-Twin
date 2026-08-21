from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", BACKEND_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = "development"
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]
    database_url: SecretStr | None = None
    database_ssl_mode: Literal["disable", "prefer", "require"] = "require"
    supabase_url: str | None = None
    supabase_jwt_issuer: str | None = None
    supabase_jwks_url: str | None = None
    supabase_jwt_audience: str = "authenticated"
    supabase_jwks_cache_ttl_seconds: int = 3600
    supabase_jwks_request_timeout_seconds: float = 5.0
    supabase_jwks_unknown_kid_cooldown_seconds: float = 30.0
    supabase_jwt_leeway_seconds: int = 30
    supabase_jwt_verification_max_workers: int = 4
    supabase_jwt_verification_max_in_flight: int = 32
    websocket_auth_timeout_seconds: float = 5.0
    edge_telemetry_shared_secret: SecretStr | None = None
    edge_telemetry_max_future_skew_seconds: float = Field(default=5.0, ge=0, le=300)
    mock_factory_enabled: bool = True
    mock_robot_count: int = 5
    mock_task_interval_seconds: float = 8
    mock_robot_speed_mps: float = 1.2
    mock_simulation_speed: float = 1

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator(
        "supabase_url",
        "supabase_jwt_issuer",
        "supabase_jwks_url",
        "database_url",
        "edge_telemetry_shared_secret",
        mode="before",
    )
    @classmethod
    def empty_string_is_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("supabase_jwks_cache_ttl_seconds")
    @classmethod
    def validate_jwks_cache_ttl(cls, value: int) -> int:
        if value < 60:
            raise ValueError("SUPABASE_JWKS_CACHE_TTL_SECONDS must be at least 60")
        return value

    @field_validator(
        "supabase_jwks_request_timeout_seconds",
        "supabase_jwks_unknown_kid_cooldown_seconds",
    )
    @classmethod
    def validate_jwks_network_limits(cls, value: float) -> float:
        if not 0.1 <= value <= 300:
            raise ValueError("JWKS timeout and cooldown must be between 0.1 and 300 seconds")
        return value

    @field_validator("supabase_jwt_verification_max_workers")
    @classmethod
    def validate_verification_workers(cls, value: int) -> int:
        if not 1 <= value <= 16:
            raise ValueError("JWT verification workers must be between 1 and 16")
        return value

    @field_validator("supabase_jwt_verification_max_in_flight")
    @classmethod
    def validate_verification_in_flight(cls, value: int) -> int:
        if not 1 <= value <= 256:
            raise ValueError("JWT verification in-flight limit must be between 1 and 256")
        return value

    @model_validator(mode="after")
    def validate_verification_capacity(self) -> Self:
        if self.supabase_jwt_verification_max_in_flight < (
            self.supabase_jwt_verification_max_workers
        ):
            raise ValueError("JWT verification in-flight limit must cover every worker")
        return self

    @field_validator("supabase_jwt_leeway_seconds")
    @classmethod
    def validate_jwt_leeway(cls, value: int) -> int:
        if not 0 <= value <= 300:
            raise ValueError("SUPABASE_JWT_LEEWAY_SECONDS must be between 0 and 300")
        return value

    @field_validator("websocket_auth_timeout_seconds")
    @classmethod
    def validate_websocket_auth_timeout(cls, value: float) -> float:
        if not 0.1 <= value <= 30:
            raise ValueError("WEBSOCKET_AUTH_TIMEOUT_SECONDS must be between 0.1 and 30")
        return value

    @field_validator("edge_telemetry_shared_secret")
    @classmethod
    def validate_edge_telemetry_shared_secret(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and len(value.get_secret_value()) < 32:
            raise ValueError("EDGE_TELEMETRY_SHARED_SECRET must be at least 32 characters")
        return value

    @property
    def effective_supabase_jwt_issuer(self) -> str | None:
        if self.supabase_jwt_issuer:
            return self.supabase_jwt_issuer.rstrip("/")
        if self.supabase_url:
            return f"{self.supabase_url.rstrip('/')}/auth/v1"
        return None

    @property
    def effective_supabase_jwks_url(self) -> str | None:
        if self.supabase_jwks_url:
            return self.supabase_jwks_url
        issuer = self.effective_supabase_jwt_issuer
        return f"{issuer}/.well-known/jwks.json" if issuer else None


@lru_cache
def get_settings() -> Settings:
    return Settings()
