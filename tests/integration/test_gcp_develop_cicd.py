from pathlib import Path

ROOT = Path(__file__).parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "deploy-gcp.yml"
DEVELOP_WORKFLOW = ROOT / ".github" / "workflows" / "deploy-gcp-develop.yml"
PRODUCTION_WORKFLOW = ROOT / ".github" / "workflows" / "deploy-gcp-production.yml"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
MAKEFILE = ROOT / "Makefile"


def test_develop_deployment_is_branch_and_ci_gated() -> None:
    develop = DEVELOP_WORKFLOW.read_text(encoding="utf-8")
    production = PRODUCTION_WORKFLOW.read_text(encoding="utf-8")
    ci_workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_call:" in develop
    assert "github.ref == 'refs/heads/develop'" in develop
    assert "github.ref == 'refs/heads/main'" in production
    assert "needs: [database, backend, frontend]" in ci_workflow
    assert "uses: ./.github/workflows/deploy-gcp-develop.yml" in ci_workflow
    assert "github.event_name == 'push' && github.ref == 'refs/heads/develop'" in ci_workflow
    assert "uses: ./.github/workflows/deploy-gcp-production.yml" in ci_workflow
    assert "github.event_name == 'push' && github.ref == 'refs/heads/main'" in ci_workflow


def test_develop_deployment_is_isolated_and_immutable() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    develop = DEVELOP_WORKFLOW.read_text(encoding="utf-8")
    production = PRODUCTION_WORKFLOW.read_text(encoding="utf-8")

    assert "service: ev-twin-api-dev" in develop
    assert "origin: https://ev-factory-twin-gcp.vercel.app" in develop
    assert "ev-twin-postgres-01" in develop
    assert "service: ev-twin-api" in production
    assert "origin: https://c3-app-078.vercel.app" in production
    assert "ev-twin-postgres-prod-01" in production
    assert "ev-twin-prod-database-url" in production
    assert "${GCP_ARTIFACT_IMAGE}:${GITHUB_SHA}" in workflow
    assert "--max-instances=1" in workflow
    assert "MOCK_FACTORY_ENABLED=false" in workflow


def test_develop_deployment_uses_keyless_auth_and_migration_guard() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "id-token: write" in workflow
    assert "workload_identity_provider:" in workflow
    assert "service_account:" in workflow
    assert "credentials_json" not in workflow
    assert "Guard unapplied migrations" in workflow
    assert "migrations_applied" in workflow
    assert "postgres/migrations" in workflow


def test_develop_deployment_runs_hosted_contract_smoke() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert '"$service_url/health"' in workflow
    assert 'test "$status" = 401' in workflow
    assert 'test "$allowed_origin" = "$ORIGIN"' in workflow


def test_makefile_provisions_repository_scoped_workload_identity() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    assert "gcp-develop-cicd-wif-create:" in makefile
    assert "https://token.actions.githubusercontent.com" in makefile
    assert "assertion.repository == '$(GITHUB_REPOSITORY)'" in makefile
    assert "assertion.ref == 'refs/heads/develop'" in makefile
    assert "roles/iam.workloadIdentityUser" in makefile
    assert "roles/artifactregistry.writer" in makefile
    assert "roles/run.developer" in makefile
    assert "roles/iam.serviceAccountUser" in makefile
    assert "gcp-production-cicd-wif-create:" in makefile
    assert "assertion.ref == 'refs/heads/main'" in makefile
    assert "ev-twin-github-prod-deploy" in makefile
    assert "github-gcp-environments-configure:" in makefile
    assert "github-gcp-environments-list:" in makefile
    assert "--env gcp-develop" in makefile
    assert "--env gcp-production" in makefile
    assert "gcp-backend-smoke:" in makefile
    assert 'test "$$status" = 401' in makefile


def test_production_runtime_has_separate_database_identity_and_secrets() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    assert "GCP_PRODUCTION_CLOUD_SQL_INSTANCE ?= ev-twin-postgres-prod-01" in makefile
    assert "GCP_PRODUCTION_BACKEND_SERVICE_ACCOUNT ?= ev-twin-api-prod" in makefile
    assert "GCP_PRODUCTION_DATABASE_URL_SECRET ?= ev-twin-prod-database-url" in makefile
    assert "gcp-production-cloudsql-create:" in makefile
    assert "--edition=enterprise --tier=db-f1-micro" in makefile
    assert "cloudsql.enable_pg_cron=on" in makefile
    assert "gcp-production-pgpassfile-create:" in makefile
    assert "gcp-production-cloudsql-proxy-start:" in makefile
    assert "gcp-production-cloudsql-proxy-stop:" in makefile
    assert "gcp-production-user-create:" in makefile
    assert 'DATABASE_SSL_MODE=disable $(MAKE) user-create' in makefile
    assert "gcp-production-seed:" in makefile
    assert "gcp-production-postgres-smoke:" in makefile
