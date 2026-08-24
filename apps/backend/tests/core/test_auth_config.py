import pytest
from ev_twin_api.core.config import Settings
from ev_twin_api.core.database import Database, normalize_async_database_url
from pydantic import ValidationError


def test_local_auth_defaults_are_bounded() -> None:
    settings = Settings(_env_file=None)
    assert settings.auth_jwt_issuer == "ev-factory-twin"
    assert settings.auth_jwt_audience == "ev-factory-twin-browser"
    assert settings.auth_access_token_ttl_seconds == 28800


def test_plain_postgresql_url_is_normalized_for_asyncpg_without_connecting() -> None:
    url = normalize_async_database_url("postgresql://user:secret@db.example.com:5432/postgres")

    assert url.drivername == "postgresql+asyncpg"
    assert url.host == "db.example.com"


def test_database_may_be_absent_at_startup() -> None:
    assert Database(None).configured is False


def test_auth_jwt_secret_is_optional_but_must_be_long_when_set() -> None:
    assert Settings(_env_file=None).auth_jwt_secret is None
    with pytest.raises(ValidationError, match="at least 64 characters"):
        Settings(_env_file=None, auth_jwt_secret="too-short")


def test_edge_telemetry_secret_is_optional_but_must_be_long_when_set() -> None:
    assert Settings(_env_file=None).edge_telemetry_shared_secret is None

    with pytest.raises(ValidationError, match="at least 32 characters"):
        Settings(_env_file=None, edge_telemetry_shared_secret="too-short")

    configured = Settings(
        _env_file=None,
        edge_telemetry_shared_secret="0123456789abcdef0123456789abcdef",
    )
    assert configured.edge_telemetry_shared_secret is not None
    assert (
        configured.edge_telemetry_shared_secret.get_secret_value()
        == "0123456789abcdef0123456789abcdef"
    )


def test_edge_telemetry_future_skew_is_bounded() -> None:
    assert Settings(_env_file=None).edge_telemetry_max_future_skew_seconds == 5

    for invalid_value in (-1, 301):
        with pytest.raises(ValidationError):
            Settings(
                _env_file=None,
                edge_telemetry_max_future_skew_seconds=invalid_value,
            )


def test_telemetry_history_flush_cadence_is_bounded() -> None:
    assert Settings(_env_file=None).telemetry_history_flush_seconds == 1
    for invalid_value in (0, 61):
        with pytest.raises(ValidationError):
            Settings(_env_file=None, telemetry_history_flush_seconds=invalid_value)


def test_production_requires_durable_authenticated_runtime() -> None:
    with pytest.raises(
        ValidationError,
        match="production requires DATABASE_URL, AUTH_JWT_SECRET, EDGE_TELEMETRY_SHARED_SECRET",
    ):
        Settings(_env_file=None, app_env="production", mock_factory_enabled=False)

    configured = Settings(
        _env_file=None,
        app_env="production",
        cors_origins=["https://ev-factory-twin.vercel.app"],
        database_url="postgresql+asyncpg://user:password@db.example.com/postgres",
        auth_jwt_secret="a" * 64,
        edge_telemetry_shared_secret="0123456789abcdef0123456789abcdef",
        mock_factory_enabled=False,
    )
    assert configured.app_env == "production"


def test_production_rejects_mock_runtime_and_wildcard_cors() -> None:
    required = {
        "_env_file": None,
        "app_env": "production",
        "database_url": "postgresql+asyncpg://user:password@db.example.com/postgres",
        "auth_jwt_secret": "a" * 64,
        "edge_telemetry_shared_secret": "0123456789abcdef0123456789abcdef",
    }

    with pytest.raises(ValidationError, match="MOCK_FACTORY_ENABLED=false"):
        Settings(**required, mock_factory_enabled=True)

    with pytest.raises(ValidationError, match="explicit CORS_ORIGINS allowlist"):
        Settings(**required, mock_factory_enabled=False, cors_origins=["*"])
