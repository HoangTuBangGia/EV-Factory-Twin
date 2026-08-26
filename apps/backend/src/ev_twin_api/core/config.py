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
    k_revision: str | None = None
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]
    database_url: SecretStr | None = None
    database_ssl_mode: Literal["disable", "prefer", "require"] = "require"
    auth_jwt_secret: SecretStr | None = None
    auth_jwt_issuer: str = "ev-factory-twin"
    auth_jwt_audience: str = "ev-factory-twin-browser"
    auth_access_token_ttl_seconds: int = Field(default=28800, ge=300, le=86400)
    auth_jwt_leeway_seconds: int = Field(default=30, ge=0, le=300)
    websocket_auth_timeout_seconds: float = 5.0
    edge_telemetry_shared_secret: SecretStr | None = None
    edge_telemetry_max_future_skew_seconds: float = Field(default=5.0, ge=0, le=300)
    telemetry_history_flush_seconds: float = Field(default=1.0, ge=0.1, le=60)
    runtime_health_sweep_seconds: float = Field(default=1.0, ge=0.1, le=60)
    command_timeout_sweep_seconds: float = Field(default=1.0, ge=0.1, le=60)
    stale_telemetry_seconds: float = Field(default=10.0, ge=1, le=3600)
    bridge_disconnect_seconds: float = Field(default=5.0, ge=1, le=3600)
    runtime_low_battery_percent: float = Field(default=20.0, ge=0, le=100)
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
        "database_url",
        "auth_jwt_secret",
        "edge_telemetry_shared_secret",
        mode="before",
    )
    @classmethod
    def empty_string_is_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @model_validator(mode="after")
    def validate_production_dependencies(self) -> Self:
        if self.app_env.lower() != "production":
            return self

        missing = [
            name
            for name, value in (
                ("DATABASE_URL", self.database_url),
                ("AUTH_JWT_SECRET", self.auth_jwt_secret),
                ("EDGE_TELEMETRY_SHARED_SECRET", self.edge_telemetry_shared_secret),
            )
            if value is None
        ]
        if missing:
            raise ValueError(f"production requires {', '.join(missing)}")
        if self.mock_factory_enabled:
            raise ValueError("production requires MOCK_FACTORY_ENABLED=false")
        if not self.cors_origins or "*" in self.cors_origins:
            raise ValueError("production requires an explicit CORS_ORIGINS allowlist")
        return self

    @field_validator("auth_jwt_secret")
    @classmethod
    def validate_auth_jwt_secret(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and len(value.get_secret_value()) < 64:
            raise ValueError("AUTH_JWT_SECRET must be at least 64 characters")
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
