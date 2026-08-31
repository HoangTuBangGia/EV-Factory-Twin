"""Offline contract checks for the GCP-native PostgreSQL migration chain."""

from pathlib import Path

from pglast import parse_sql

ROOT = Path(__file__).parents[2]
MIGRATIONS = ROOT / "postgres" / "migrations"
SEED = ROOT / "postgres" / "seed.sql"
RUNNER = ROOT / "scripts" / "postgres_migrate.sh"


def migration_files() -> list[Path]:
    return sorted(MIGRATIONS.glob("*.sql"))


def test_migrations_are_ordered_and_parseable() -> None:
    files = migration_files()
    assert [path.name[:4] for path in files] == [f"{index:04d}" for index in range(1, 16)]
    for path in files:
        assert parse_sql(path.read_text(encoding="utf-8")), path.name


def test_migrations_have_no_supabase_principals_or_auth_schema() -> None:
    sql = "\n".join(path.read_text(encoding="utf-8").lower() for path in migration_files())
    forbidden = ("supabase", "service_role", "to authenticated", "from anon", "auth.users")
    assert not [token for token in forbidden if token in sql]


def test_auth_schema_has_only_mvp_roles_and_local_credentials() -> None:
    sql = (MIGRATIONS / "0001_gcp_native_auth.sql").read_text(encoding="utf-8")
    assert "create table public.app_users" in sql.lower()
    assert "'DESIGNER', 'MONITOR'" in sql
    assert "ADMIN" not in sql


def test_seed_is_parseable_and_contains_no_credentials() -> None:
    sql = SEED.read_text(encoding="utf-8")
    assert parse_sql(sql)
    lowered = sql.lower()
    assert "layout-default" in lowered
    assert "password" not in lowered
    assert "password_hash" not in lowered


def test_audit_and_layout_versions_remain_append_only() -> None:
    sql = "\n".join(path.read_text(encoding="utf-8") for path in migration_files())
    assert "audit_events_reject_update_delete" in sql
    assert "layout_versions_reject_update_delete" in sql


def test_updated_at_trigger_preserves_explicit_domain_time() -> None:
    sql = (MIGRATIONS / "0009_preserve_authoritative_updated_at.sql").read_text(encoding="utf-8")
    normalized = " ".join(sql.lower().split())
    assert "new.updated_at is not distinct from old.updated_at" in normalized
    assert "new.updated_at := now()" in normalized


def test_default_layout_repair_creates_parent_before_version() -> None:
    sql = (MIGRATIONS / "0013_ensure_default_layout.sql").read_text(encoding="utf-8")
    normalized = " ".join(sql.lower().split())
    assert "from public.profiles" in normalized
    assert "where role = 'designer' and is_active" in normalized
    assert normalized.index("insert into public.layouts") < normalized.index(
        "insert into public.layout_versions"
    )
    assert "on conflict (layout_id, version) do nothing" in normalized


def test_scenario_revision_workflow_is_persisted_and_audited() -> None:
    status_sql = (MIGRATIONS / "0014_add_revision_requested_status.sql").read_text(encoding="utf-8")
    workflow_sql = (MIGRATIONS / "0015_add_scenario_revision_workflow.sql").read_text(
        encoding="utf-8"
    )
    assert "'REVISION_REQUESTED'" in status_sql
    assert "review_note text" in workflow_sql
    assert "revision_of text references public.scenarios" in workflow_sql
    assert "REVISION_REQUESTED" in workflow_sql


def test_migration_runner_tracks_checksum_and_interrupted_state() -> None:
    script = RUNNER.read_text(encoding="utf-8")
    assert "schema_migrations" in script
    assert "sha256sum" in script
    assert "checksum mismatch" in script
    assert "APPLYING" in script
    assert "operator recovery" in script
    assert "psql_run --file" in script
    assert "--command=" not in script
    assert script.index("ledger_records=$(psql_run") < script.index("for migration in")
