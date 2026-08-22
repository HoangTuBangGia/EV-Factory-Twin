"""Offline syntax and security-contract checks for Supabase migrations.

These tests deliberately do not connect to Supabase.  ``pglast`` uses the
PostgreSQL parser, while the assertions below guard the schema and RLS
invariants that are easy to lose during a migration edit.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import pytest
from pglast import ast, parse_sql
from pglast.stream import RawStream

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_DIRECTORY = REPOSITORY_ROOT / "supabase" / "migrations"
MIGRATION_NAME = re.compile(r"^(?P<version>[0-9]{14})_[a-z0-9_]+\.sql$")

EXPECTED_COLUMNS = {
    "profiles": {
        "id",
        "display_name",
        "role",
        "is_active",
        "created_at",
        "updated_at",
    },
    "scenarios": {
        "id",
        "name",
        "status",
        "num_robots",
        "num_tasks",
        "task_arrival_interval",
        "travel_time",
        "loading_time",
        "simulation_time",
        "completed_tasks",
        "unfinished_tasks",
        "completion_rate",
        "throughput_per_hour",
        "average_cycle_time",
        "average_waiting_time",
        "duration_ms",
        "created_by",
        "reviewed_by",
        "applied_by",
        "created_at",
        "reviewed_at",
        "applied_at",
        "updated_at",
        "version",
    },
    "audit_events": {
        "id",
        "actor_id",
        "actor_role",
        "action",
        "resource_type",
        "resource_id",
        "before_data",
        "after_data",
        "request_id",
        "created_at",
    },
    "kpi_snapshots": {
        "id",
        "scenario_id",
        "recorded_at",
        "simulated_elapsed_seconds",
        "completed_tasks",
        "throughput_per_hour",
        "average_cycle_time_seconds",
        "active_tasks",
        "queued_tasks",
        "starvation_events",
        "fleet_utilization_percent",
    },
    "layouts": {
        "id",
        "name",
        "latest_version",
        "created_by",
        "created_at",
        "updated_at",
        "archived_at",
    },
    "layout_versions": {
        "layout_id",
        "version",
        "content",
        "created_by",
        "created_at",
    },
    "scenario_reviews": {"id", "scenario_id", "decision", "actor_id", "created_at"},
    "commands": {
        "operation_id",
        "scenario_id",
        "status",
        "payload",
        "timeout_seconds",
        "max_retries",
        "requested_by",
        "created_at",
        "updated_at",
    },
    "command_attempts": {
        "operation_id",
        "attempt_number",
        "status",
        "leased_by",
        "leased_at",
        "lease_expires_at",
        "acknowledged_at",
        "completed_at",
        "detail",
    },
    "command_acknowledgements": {
        "id",
        "operation_id",
        "attempt_number",
        "status",
        "bridge_id",
        "detail",
        "created_at",
    },
}


def _migration_files() -> list[Path]:
    return sorted(MIGRATION_DIRECTORY.glob("*.sql"))


def _statements() -> list[ast.Node]:
    statements: list[ast.Node] = []
    for migration in _migration_files():
        statements.extend(raw_statement.stmt for raw_statement in parse_sql(migration.read_text()))
    return statements


def _role_name(role: ast.RoleSpec) -> str:
    if role.roletype.name == "ROLESPEC_PUBLIC":
        return "public"
    return (role.rolename or "").lower()


def _relation_name(relation: ast.RangeVar) -> tuple[str, str]:
    return relation.schemaname or "public", relation.relname


def _table_grants(statements: list[ast.Node]) -> list[ast.GrantStmt]:
    return [
        statement
        for statement in statements
        if isinstance(statement, ast.GrantStmt) and statement.objtype.name == "OBJECT_TABLE"
    ]


def test_migration_names_are_unique_and_ordered() -> None:
    migrations = _migration_files()
    assert migrations, "supabase/migrations must contain at least one SQL migration"

    versions: list[str] = []
    for migration in migrations:
        match = MIGRATION_NAME.fullmatch(migration.name)
        assert match, f"{migration.name} must use <14-digit UTC timestamp>_<snake_case>.sql"
        versions.append(match.group("version"))

    assert versions == sorted(versions)
    assert len(versions) == len(set(versions)), "migration timestamps must be unique"


@pytest.mark.parametrize("migration", _migration_files(), ids=lambda path: path.name)
def test_migration_is_valid_postgresql_syntax(migration: Path) -> None:
    # parse_sql raises ParseError with a line/column when PostgreSQL syntax is invalid.
    statements = parse_sql(migration.read_text())
    assert statements, f"{migration.name} must not be empty"


def test_public_schema_contract_contains_required_tables_and_columns() -> None:
    created_columns: dict[str, set[str]] = {}

    for statement in _statements():
        if not isinstance(statement, ast.CreateStmt):
            continue
        if _relation_name(statement.relation)[0] != "public":
            continue
        created_columns[statement.relation.relname] = {
            element.colname
            for element in statement.tableElts or ()
            if isinstance(element, ast.ColumnDef)
        }

    assert set(created_columns) == set(EXPECTED_COLUMNS)
    for table, required_columns in EXPECTED_COLUMNS.items():
        assert required_columns <= created_columns[table], (
            f"public.{table} is missing: {sorted(required_columns - created_columns[table])}"
        )


def test_application_enums_match_the_api_contract() -> None:
    enums: dict[str, tuple[str, ...]] = {}

    for statement in _statements():
        if not isinstance(statement, ast.CreateEnumStmt):
            continue
        qualified_name = ".".join(part.sval for part in statement.typeName)
        enums[qualified_name] = tuple(value.sval for value in statement.vals)

    assert enums["public.app_role"] == ("DESIGNER", "MONITOR")
    assert enums["public.scenario_status"] == (
        "DRAFT",
        "SIMULATED",
        "APPROVED",
        "REJECTED",
        "APPLIED",
    )
    lifecycle_migration = (
        MIGRATION_DIRECTORY / "20260822000350_add_submitted_scenario_status.sql"
    ).read_text()
    assert "add value if not exists 'submitted'" in lifecycle_migration.lower()
    assert enums["public.command_status"] == (
        "PENDING",
        "ACKNOWLEDGED",
        "COMPLETED",
        "FAILED",
        "TIMED_OUT",
    )


def test_every_public_table_enables_rls_and_never_disables_it() -> None:
    statements = _statements()
    created_tables = {
        _relation_name(statement.relation)
        for statement in statements
        if isinstance(statement, ast.CreateStmt)
        and _relation_name(statement.relation)[0] == "public"
    }
    rls_enabled: set[tuple[str, str]] = set()
    rls_disabled: set[tuple[str, str]] = set()

    for statement in statements:
        if not isinstance(statement, ast.AlterTableStmt):
            continue
        relation = _relation_name(statement.relation)
        for command in statement.cmds or ():
            if command.subtype.name == "AT_EnableRowSecurity":
                rls_enabled.add(relation)
            if command.subtype.name == "AT_DisableRowSecurity":
                rls_disabled.add(relation)

    assert not rls_disabled, f"migrations disable RLS on: {sorted(rls_disabled)}"
    assert created_tables <= rls_enabled, (
        f"public tables without ENABLE ROW LEVEL SECURITY: {sorted(created_tables - rls_enabled)}"
    )


def test_public_tables_do_not_grant_anon_or_authenticated_writes() -> None:
    statements = _statements()
    created_tables = {
        _relation_name(statement.relation)
        for statement in statements
        if isinstance(statement, ast.CreateStmt)
        and _relation_name(statement.relation)[0] == "public"
    }
    revoked_all: defaultdict[tuple[str, str], set[str]] = defaultdict(set)

    for grant in _table_grants(statements):
        targets = {
            _relation_name(relation)
            for relation in grant.objects or ()
            if isinstance(relation, ast.RangeVar)
        }
        targets &= created_tables
        if not targets:
            continue

        roles = {_role_name(role) for role in grant.grantees or ()}
        privileges = (
            {privilege.priv_name.lower() for privilege in grant.privileges}
            if grant.privileges
            else {"all"}
        )

        if not grant.is_grant and "all" in privileges:
            for target in targets:
                revoked_all[target].update(roles)
            continue

        if not grant.is_grant:
            continue

        assert not roles & {"public", "anon"}, (
            f"{sorted(targets)} grant {sorted(privileges)} to {sorted(roles)}"
        )
        if "authenticated" in roles:
            assert privileges <= {"select"}, (
                "authenticated clients must use FastAPI for writes; "
                f"{sorted(targets)} grant {sorted(privileges)}"
            )

    for table in created_tables:
        assert "anon" in revoked_all[table], f"public.{table[1]} must REVOKE ALL FROM anon"
        assert "authenticated" in revoked_all[table], (
            f"public.{table[1]} must REVOKE ALL FROM authenticated before SELECT is granted"
        )


def test_authenticated_policies_are_select_only_and_cover_each_public_table() -> None:
    statements = _statements()
    public_tables = {
        _relation_name(statement.relation)
        for statement in statements
        if isinstance(statement, ast.CreateStmt)
        and _relation_name(statement.relation)[0] == "public"
    }
    covered_tables: set[tuple[str, str]] = set()

    for policy in (
        statement for statement in statements if isinstance(statement, ast.CreatePolicyStmt)
    ):
        # PostgreSQL defaults a policy with no TO clause to PUBLIC.
        roles = {_role_name(role) for role in policy.roles} if policy.roles else {"public"}
        assert not roles & {"public", "anon"}, (
            f"policy {policy.policy_name} must not expose rows to anonymous clients"
        )
        if "authenticated" in roles:
            assert policy.cmd_name.lower() == "select", (
                f"policy {policy.policy_name} gives authenticated clients write access"
            )
            covered_tables.add(_relation_name(policy.table))

    assert public_tables <= covered_tables, (
        "public tables without an authenticated SELECT policy: "
        f"{sorted(public_tables - covered_tables)}"
    )


@pytest.mark.parametrize(
    ("policy_name", "required_fragments"),
    [
        (
            "profiles_select_own",
            ("private.is_active_user", "auth.uid"),
        ),
        ("scenarios_select_active_users", ("private.is_active_user",)),
        (
            "audit_events_select_monitor",
            ("private.is_active_user", "private.current_app_role", "'MONITOR'"),
        ),
        ("kpi_snapshots_select_active_users", ("private.is_active_user",)),
        ("layouts_select_active_users", ("private.is_active_user",)),
        ("layout_versions_select_active_users", ("private.is_active_user",)),
    ],
)
def test_required_rls_policy_predicates(
    policy_name: str, required_fragments: tuple[str, ...]
) -> None:
    policies = {
        statement.policy_name: statement
        for statement in _statements()
        if isinstance(statement, ast.CreatePolicyStmt)
    }
    assert policy_name in policies

    rendered_policy = RawStream()(policies[policy_name])
    for fragment in required_fragments:
        assert fragment in rendered_policy


def test_security_definer_functions_are_private_and_pin_search_path() -> None:
    for statement in _statements():
        if not isinstance(statement, ast.CreateFunctionStmt):
            continue
        rendered_function = RawStream()(statement)
        if "SECURITY DEFINER" not in rendered_function:
            continue

        qualified_name = tuple(part.sval for part in statement.funcname)
        assert qualified_name[0] == "private", (
            f"SECURITY DEFINER function {'.'.join(qualified_name)} must live in private"
        )
        assert "SET search_path TO ''" in rendered_function, (
            f"SECURITY DEFINER function {'.'.join(qualified_name)} must pin an empty search_path"
        )


def test_audit_events_remains_append_only() -> None:
    statements = _statements()
    audit_grants: defaultdict[str, set[str]] = defaultdict(set)

    for grant in _table_grants(statements):
        targets = {
            _relation_name(relation)
            for relation in grant.objects or ()
            if isinstance(relation, ast.RangeVar)
        }
        if ("public", "audit_events") not in targets or not grant.is_grant:
            continue
        privileges = (
            {privilege.priv_name.lower() for privilege in grant.privileges}
            if grant.privileges
            else {"all"}
        )
        for role in grant.grantees or ():
            audit_grants[_role_name(role)].update(privileges)

    assert audit_grants["authenticated"] == {"select"}
    assert audit_grants["service_role"] == {"select", "insert"}

    triggers = {
        statement.trigname: RawStream()(statement)
        for statement in statements
        if isinstance(statement, ast.CreateTrigStmt)
        and _relation_name(statement.relation) == ("public", "audit_events")
    }
    update_delete = triggers["audit_events_reject_update_delete"]
    truncate = triggers["audit_events_reject_truncate"]

    assert "BEFORE" in update_delete
    assert "UPDATE" in update_delete
    assert "DELETE" in update_delete
    assert "private.reject_audit_event_mutation" in update_delete
    assert "BEFORE TRUNCATE" in truncate
    assert "private.reject_audit_event_mutation" in truncate


def test_layout_versions_are_immutable() -> None:
    triggers = {
        statement.trigname: RawStream()(statement)
        for statement in _statements()
        if isinstance(statement, ast.CreateTrigStmt)
        and _relation_name(statement.relation) == ("public", "layout_versions")
    }

    assert "UPDATE" in triggers["layout_versions_reject_update_delete"]
    assert "DELETE" in triggers["layout_versions_reject_update_delete"]
    assert "BEFORE TRUNCATE" in triggers["layout_versions_reject_truncate"]


def test_migrations_contain_no_destructive_schema_statements() -> None:
    destructive = {
        RawStream()(statement)
        for statement in _statements()
        if isinstance(statement, (ast.DropStmt, ast.TruncateStmt))
    }
    reviewed_role_reduction = {
        "DROP POLICY profiles_select_own_or_admin ON public.profiles",
        "DROP POLICY audit_events_select_admin ON public.audit_events",
        "DROP TRIGGER ev_twin_on_auth_user_created ON auth.users",
        "DROP FUNCTION private.handle_new_auth_user ()",
        "DROP FUNCTION private.current_app_role ()",
        "DROP TYPE public.app_role_legacy",
    }
    unexpected = destructive - reviewed_role_reduction
    assert not unexpected, f"destructive migration statement(s): {sorted(unexpected)}"
