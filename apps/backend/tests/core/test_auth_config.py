import pytest
from ev_twin_api.core.config import Settings
from ev_twin_api.core.database import Database, normalize_async_database_url
from pydantic import ValidationError


def test_supabase_jwt_urls_are_derived_from_project_url() -> None:
    settings = Settings(
        _env_file=None,
        supabase_url="https://project.supabase.co/",
    )

    assert settings.effective_supabase_jwt_issuer == "https://project.supabase.co/auth/v1"
    assert (
        settings.effective_supabase_jwks_url
        == "https://project.supabase.co/auth/v1/.well-known/jwks.json"
    )


def test_plain_postgresql_url_is_normalized_for_asyncpg_without_connecting() -> None:
    url = normalize_async_database_url("postgresql://user:secret@db.example.com:5432/postgres")

    assert url.drivername == "postgresql+asyncpg"
    assert url.host == "db.example.com"


def test_database_may_be_absent_at_startup() -> None:
    assert Database(None).configured is False


def test_jwt_verification_capacity_must_cover_worker_count() -> None:
    with pytest.raises(ValidationError, match="in-flight limit"):
        Settings(
            _env_file=None,
            supabase_jwt_verification_max_workers=4,
            supabase_jwt_verification_max_in_flight=3,
        )


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


def test_production_requires_durable_authenticated_runtime() -> None:
    with pytest.raises(
        ValidationError,
        match="production requires DATABASE_URL, SUPABASE_URL, EDGE_TELEMETRY_SHARED_SECRET",
    ):
        Settings(_env_file=None, app_env="production", mock_factory_enabled=False)

    configured = Settings(
        _env_file=None,
        app_env="production",
        cors_origins=["https://ev-factory-twin.vercel.app"],
        database_url="postgresql+asyncpg://user:password@db.example.com/postgres",
        supabase_url="https://project.supabase.co",
        edge_telemetry_shared_secret="0123456789abcdef0123456789abcdef",
        mock_factory_enabled=False,
    )
    assert configured.app_env == "production"


def test_production_rejects_mock_runtime_and_wildcard_cors() -> None:
    required = {
        "_env_file": None,
        "app_env": "production",
        "database_url": "postgresql+asyncpg://user:password@db.example.com/postgres",
        "supabase_url": "https://project.supabase.co",
        "edge_telemetry_shared_secret": "0123456789abcdef0123456789abcdef",
    }

    with pytest.raises(ValidationError, match="MOCK_FACTORY_ENABLED=false"):
        Settings(**required, mock_factory_enabled=True)

    with pytest.raises(ValidationError, match="explicit CORS_ORIGINS allowlist"):
        Settings(**required, mock_factory_enabled=False, cors_origins=["*"])
