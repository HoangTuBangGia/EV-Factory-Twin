from pathlib import Path

from pglast import parse_sql

ROOT = Path(__file__).parents[2]
MAKEFILE = ROOT / "Makefile"
CLOUD_BUILD = ROOT / "deploy" / "gcp" / "cloudbuild.backend.yaml"
ENV_EXAMPLE = ROOT / "deploy" / "gcp" / "backend.env.example"
RUNTIME_GRANTS = ROOT / "postgres" / "migrations" / "0010_grant_runtime_database_access.sql"


def test_runtime_database_grants_are_parseable_and_least_privilege() -> None:
    sql = RUNTIME_GRANTS.read_text(encoding="utf-8")
    normalized = " ".join(sql.lower().split())

    assert parse_sql(sql)
    assert "ev_twin_app" in normalized
    assert "grant select, insert, update, delete on all tables" in normalized
    assert "grant usage, select on all sequences" in normalized
    assert "superuser" not in normalized
    assert "create on schema" not in normalized


def test_cloud_build_uses_backend_dockerfile_and_immutable_image_input() -> None:
    config = CLOUD_BUILD.read_text(encoding="utf-8")

    assert "apps/backend/Dockerfile" in config
    assert "${_IMAGE}" in config
    assert "latest" not in config


def test_cloud_run_target_preserves_mvp_runtime_boundaries() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    assert "gcp-cloud-build-access:" in makefile
    assert "--role=roles/cloudbuild.builds.builder" in makefile
    assert '--service-account="$(GCP_BACKEND_SERVICE_ACCOUNT_EMAIL)"' in makefile
    assert '--add-cloudsql-instances="$(GCP_CLOUD_SQL_CONNECTION_NAME)"' in makefile
    assert "--max-instances=1" in makefile
    assert "--min-instances=0" in makefile
    assert "MOCK_FACTORY_ENABLED=false" in makefile
    assert "DATABASE_URL=$(GCP_DATABASE_URL_SECRET):latest" in makefile


def test_committed_backend_environment_contains_no_secrets() -> None:
    content = ENV_EXAMPLE.read_text(encoding="utf-8")

    assert "APP_ENV=production" in content
    assert "MOCK_FACTORY_ENABLED=false" in content
    assert "DATABASE_URL=" not in content
    assert "AUTH_JWT_SECRET=" not in content
    assert "EDGE_TELEMETRY_SHARED_SECRET=" not in content
