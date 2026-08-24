"""Offline contract checks for the GCP-native PostgreSQL migration chain."""

from pathlib import Path

from pglast import parse_sql

ROOT = Path(__file__).parents[2]
MIGRATIONS = ROOT / "postgres" / "migrations"
SEED = ROOT / "postgres" / "seed.sql"


def migration_files() -> list[Path]:
    return sorted(MIGRATIONS.glob("*.sql"))


def test_migrations_are_ordered_and_parseable() -> None:
    files = migration_files()
    assert [path.name[:4] for path in files] == [f"{index:04d}" for index in range(1, 10)]
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
