import pytest
from ev_twin_api.core.config import Settings
from ev_twin_api.core.database import Database, normalize_async_database_url
from pydantic import SecretStr, ValidationError


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


def test_service_role_key_is_optional_secret_server_configuration() -> None:
    without_key = Settings(_env_file=None)
    with_key = Settings(_env_file=None, supabase_service_role_key="server-secret")

    assert without_key.supabase_service_role_key is None
    assert isinstance(with_key.supabase_service_role_key, SecretStr)
    assert str(with_key.supabase_service_role_key) != "server-secret"
    assert with_key.supabase_service_role_key.get_secret_value() == "server-secret"


def test_jwt_verification_capacity_must_cover_worker_count() -> None:
    with pytest.raises(ValidationError, match="in-flight limit"):
        Settings(
            _env_file=None,
            supabase_jwt_verification_max_workers=4,
            supabase_jwt_verification_max_in_flight=3,
        )
