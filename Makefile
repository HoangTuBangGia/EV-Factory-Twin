ROS_DISTRO ?= jazzy
POSTGRES_IMAGE ?= postgres:17-alpine
CLOUD_SQL_PGPASSFILE ?= /tmp/ev-twin-cloudsql.pgpass
CLOUD_SQL_PROXY_HOST ?= 127.0.0.1
CLOUD_SQL_PROXY_PORT ?= 5433
GCP_PROJECT ?= ev-factory-twin
GCP_REGION ?= us-central1
GCP_ARTIFACT_REPOSITORY ?= ev-twin
GCP_BACKEND_SERVICE ?= ev-twin-api
GCP_BACKEND_SERVICE_ACCOUNT ?= ev-twin-api
GCP_BACKEND_SERVICE_ACCOUNT_EMAIL = $(GCP_BACKEND_SERVICE_ACCOUNT)@$(GCP_PROJECT).iam.gserviceaccount.com
GCP_CLOUD_BUILD_SERVICE_ACCOUNT ?= 849232336681-compute@developer.gserviceaccount.com
GCP_CLOUD_SQL_INSTANCE ?= ev-twin-postgres-01
GCP_CLOUD_SQL_CONNECTION_NAME = $(GCP_PROJECT):$(GCP_REGION):$(GCP_CLOUD_SQL_INSTANCE)
GCP_BACKEND_IMAGE_TAG ?= $(shell git rev-parse --short HEAD)
GCP_BACKEND_IMAGE = $(GCP_REGION)-docker.pkg.dev/$(GCP_PROJECT)/$(GCP_ARTIFACT_REPOSITORY)/backend:$(GCP_BACKEND_IMAGE_TAG)
GCP_BACKEND_CORS_ORIGINS ?= https://c3-app-078.vercel.app
GCP_DATABASE_URL_SECRET ?= ev-twin-database-url
GCP_AUTH_JWT_SECRET ?= ev-twin-auth-jwt-secret
GCP_EDGE_SECRET ?= ev-twin-edge-telemetry-secret

.PHONY: sync lint format format-check migration-check postgres-migrate postgres-migrate-docker postgres-migrations-baseline-docker postgres-seed-docker integration postgres-smoke test test-cov typecheck check backend user-create frontend-sync frontend frontend-lint frontend-typecheck frontend-test frontend-build frontend-check frontend-browser-install frontend-smoke frontend-e2e-list frontend-e2e docker-build gcp-backend-check gcp-backend-apis gcp-artifact-repository-create gcp-cloud-build-access gcp-backend-service-account-create gcp-backend-cloudsql-access gcp-backend-secrets-create gcp-backend-database-user-create gcp-secret-version-add gcp-backend-secret-access gcp-backend-build gcp-backend-deploy ros-deps ros-build ros-test ros-check

sync:
	uv sync --all-packages --dev

lint:
	uv run ruff check .

format:
	uv run ruff format .

format-check:
	uv run ruff format --check .

typecheck:
	uv run mypy packages/twin-core/src apps/backend/src services/simulation/src evaluation/src

migration-check:
	sh -n scripts/postgres_migrate.sh
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest -p pytest_asyncio.plugin tests/integration/test_postgres_migrations.py

postgres-migrate:
	@test -n "$(MIGRATION_DATABASE_URL)" || (echo "MIGRATION_DATABASE_URL is required" >&2; exit 2)
	DATABASE_URL="$(MIGRATION_DATABASE_URL)" \
		MIGRATION_DIRECTORY="$(CURDIR)/postgres/migrations" \
		sh scripts/postgres_migrate.sh apply

postgres-migrate-docker:
	@test -f "$(CLOUD_SQL_PGPASSFILE)" || \
		(echo "CLOUD_SQL_PGPASSFILE does not exist: $(CLOUD_SQL_PGPASSFILE)" >&2; exit 2)
	docker run --rm --network host \
		--env PGPASSFILE=/run/secrets/pgpass \
		--env PGHOST="$(CLOUD_SQL_PROXY_HOST)" --env PGPORT="$(CLOUD_SQL_PROXY_PORT)" \
		--env PGUSER=postgres --env PGDATABASE=postgres \
		--volume "$(CLOUD_SQL_PGPASSFILE):/run/secrets/pgpass:ro" \
		--volume "$(CURDIR)/postgres/migrations:/migrations:ro" \
		--volume "$(CURDIR)/scripts/postgres_migrate.sh:/postgres_migrate.sh:ro" \
		"$(POSTGRES_IMAGE)" sh /postgres_migrate.sh apply

postgres-migrations-baseline-docker:
	@test -f "$(CLOUD_SQL_PGPASSFILE)" || \
		(echo "CLOUD_SQL_PGPASSFILE does not exist: $(CLOUD_SQL_PGPASSFILE)" >&2; exit 2)
	docker run --rm --network host \
		--env PGPASSFILE=/run/secrets/pgpass \
		--env PGHOST="$(CLOUD_SQL_PROXY_HOST)" --env PGPORT="$(CLOUD_SQL_PROXY_PORT)" \
		--env PGUSER=postgres --env PGDATABASE=postgres \
		--volume "$(CLOUD_SQL_PGPASSFILE):/run/secrets/pgpass:ro" \
		--volume "$(CURDIR)/postgres/migrations:/migrations:ro" \
		--volume "$(CURDIR)/scripts/postgres_migrate.sh:/postgres_migrate.sh:ro" \
		"$(POSTGRES_IMAGE)" sh /postgres_migrate.sh baseline

postgres-seed-docker:
	@test -f "$(CLOUD_SQL_PGPASSFILE)" || \
		(echo "CLOUD_SQL_PGPASSFILE does not exist: $(CLOUD_SQL_PGPASSFILE)" >&2; exit 2)
	docker run --rm --network host \
		--env PGPASSFILE=/run/secrets/pgpass \
		--volume "$(CLOUD_SQL_PGPASSFILE):/run/secrets/pgpass:ro" \
		--volume "$(CURDIR)/postgres/seed.sql:/seed.sql:ro" \
		"$(POSTGRES_IMAGE)" psql \
			--host="$(CLOUD_SQL_PROXY_HOST)" --port="$(CLOUD_SQL_PROXY_PORT)" \
			--username=postgres --dbname=postgres --set=ON_ERROR_STOP=1 \
			--file=/seed.sql

integration:
	APP_ENV=test DATABASE_URL= PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest -p pytest_asyncio.plugin tests/integration

postgres-smoke:
	@test -n "$(TEST_DATABASE_URL)" || (echo "TEST_DATABASE_URL is required" >&2; exit 2)
	@APP_ENV=test DATABASE_URL= PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 TEST_DATABASE_URL="$(TEST_DATABASE_URL)" \
		uv run pytest -p pytest_asyncio.plugin \
		tests/integration/test_runtime_history_postgres.py \
		tests/integration/test_command_repository_postgres.py

test:
	APP_ENV=test DATABASE_URL= PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest -p pytest_asyncio.plugin

test-cov:
	APP_ENV=test DATABASE_URL= PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest -p pytest_asyncio.plugin \
		--cov=ev_twin_api \
		--cov=twin_core \
		--cov-report=term-missing \
		--cov-report=xml

check: lint format-check typecheck test

backend:
	uv run --package ev-twin-api \
		uvicorn ev_twin_api.main:app \
		--app-dir apps/backend/src \
		--reload

user-create:
	uv run --package ev-twin-api python -m ev_twin_api.cli.create_user \
		--email "$(EMAIL)" --display-name "$(DISPLAY_NAME)" --role "$(ROLE)"

frontend-sync:
	npm --prefix apps/frontend ci

frontend:
	npm --prefix apps/frontend run dev

frontend-lint:
	npm --prefix apps/frontend run lint

frontend-typecheck:
	npm --prefix apps/frontend run typecheck

frontend-test:
	npm --prefix apps/frontend run test -- --run

frontend-build:
	npm --prefix apps/frontend run build

frontend-check: frontend-lint frontend-typecheck frontend-test frontend-build

frontend-browser-install:
	npm --prefix apps/frontend exec -- playwright install chromium

frontend-smoke:
	npm --prefix apps/frontend run test:smoke

frontend-e2e-list:
	npm --prefix apps/frontend run test:e2e:list

frontend-e2e:
	npm --prefix apps/frontend run test:e2e

docker-build:
	docker build --file apps/backend/Dockerfile --tag ev-factory-twin-api:local .

gcp-backend-check: migration-check
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest -p pytest_asyncio.plugin \
		tests/integration/test_gcp_cloud_run_backend.py

gcp-backend-apis:
	gcloud services enable run.googleapis.com artifactregistry.googleapis.com \
		cloudbuild.googleapis.com secretmanager.googleapis.com \
		--project="$(GCP_PROJECT)"

gcp-artifact-repository-create:
	gcloud artifacts repositories create "$(GCP_ARTIFACT_REPOSITORY)" \
		--project="$(GCP_PROJECT)" --location="$(GCP_REGION)" \
		--repository-format=docker --description="EV Factory Twin container images"

gcp-cloud-build-access:
	gcloud projects add-iam-policy-binding "$(GCP_PROJECT)" \
		--member="serviceAccount:$(GCP_CLOUD_BUILD_SERVICE_ACCOUNT)" \
		--role=roles/cloudbuild.builds.builder

gcp-backend-service-account-create:
	gcloud iam service-accounts create "$(GCP_BACKEND_SERVICE_ACCOUNT)" \
		--project="$(GCP_PROJECT)" --display-name="EV Twin Cloud Run Backend"

gcp-backend-cloudsql-access:
	gcloud projects add-iam-policy-binding "$(GCP_PROJECT)" \
		--member="serviceAccount:$(GCP_BACKEND_SERVICE_ACCOUNT_EMAIL)" \
		--role=roles/cloudsql.client

gcp-backend-secrets-create:
	@for secret in "$(GCP_DATABASE_URL_SECRET)" "$(GCP_AUTH_JWT_SECRET)" "$(GCP_EDGE_SECRET)"; do \
		gcloud secrets create "$$secret" --project="$(GCP_PROJECT)" \
			--replication-policy=automatic || exit 1; \
	done

gcp-backend-database-user-create:
	@bash -eu -o pipefail -c '\
		read -rsp "New ev_twin_app database password: " password; echo; \
		read -rsp "Confirm database password: " confirmation; echo; \
		test "$${#password}" -ge 32 || { echo "password must be at least 32 characters" >&2; exit 2; }; \
		test "$$password" = "$$confirmation" || { echo "passwords do not match" >&2; exit 2; }; \
		gcloud sql users create ev_twin_app --instance="$(GCP_CLOUD_SQL_INSTANCE)" \
			--project="$(GCP_PROJECT)" --password="$$password"; \
		encoded_password=$$(printf "%s" "$$password" | python3 -c \
			"import sys, urllib.parse; print(urllib.parse.quote(sys.stdin.read(), safe=\"\"), end=\"\")"); \
		printf "postgresql+asyncpg://ev_twin_app:%s@/postgres?host=/cloudsql/$(GCP_CLOUD_SQL_CONNECTION_NAME)" \
			"$$encoded_password" | gcloud secrets versions add "$(GCP_DATABASE_URL_SECRET)" \
			--project="$(GCP_PROJECT)" --data-file=-; \
		unset password confirmation encoded_password'

gcp-secret-version-add:
	@test -n "$(SECRET_NAME)" || (echo "SECRET_NAME is required" >&2; exit 2)
	@bash -eu -o pipefail -c '\
		read -rsp "Secret value for $(SECRET_NAME): " secret_value; echo; \
		test -n "$$secret_value" || { echo "secret value must not be empty" >&2; exit 2; }; \
		printf "%s" "$$secret_value" | gcloud secrets versions add "$(SECRET_NAME)" \
			--project="$(GCP_PROJECT)" --data-file=-; \
		unset secret_value'

gcp-backend-secret-access:
	@for secret in "$(GCP_DATABASE_URL_SECRET)" "$(GCP_AUTH_JWT_SECRET)" "$(GCP_EDGE_SECRET)"; do \
		gcloud secrets add-iam-policy-binding "$$secret" --project="$(GCP_PROJECT)" \
			--member="serviceAccount:$(GCP_BACKEND_SERVICE_ACCOUNT_EMAIL)" \
			--role=roles/secretmanager.secretAccessor || exit 1; \
	done

gcp-backend-build:
	gcloud builds submit . --project="$(GCP_PROJECT)" \
		--config=deploy/gcp/cloudbuild.backend.yaml \
		--substitutions="_IMAGE=$(GCP_BACKEND_IMAGE)"

gcp-backend-deploy:
	gcloud run deploy "$(GCP_BACKEND_SERVICE)" --project="$(GCP_PROJECT)" \
		--region="$(GCP_REGION)" --platform=managed \
		--image="$(GCP_BACKEND_IMAGE)" \
		--service-account="$(GCP_BACKEND_SERVICE_ACCOUNT_EMAIL)" \
		--add-cloudsql-instances="$(GCP_CLOUD_SQL_CONNECTION_NAME)" \
		--set-secrets="DATABASE_URL=$(GCP_DATABASE_URL_SECRET):latest,AUTH_JWT_SECRET=$(GCP_AUTH_JWT_SECRET):latest,EDGE_TELEMETRY_SHARED_SECRET=$(GCP_EDGE_SECRET):latest" \
		--set-env-vars="^@^APP_ENV=production@DATABASE_SSL_MODE=disable@AUTH_JWT_ISSUER=ev-factory-twin-api@AUTH_JWT_AUDIENCE=ev-factory-twin-browser@AUTH_ACCESS_TOKEN_TTL_SECONDS=28800@CORS_ORIGINS=$(GCP_BACKEND_CORS_ORIGINS)@MOCK_FACTORY_ENABLED=false" \
		--port=8000 --cpu=1 --memory=512Mi --concurrency=80 \
		--min-instances=0 --max-instances=1 --timeout=300 \
		--allow-unauthenticated

ros-deps:
	python3 -c "from colcon_ros.task.ament_python.build import AmentPythonBuildTask"
	cd ros2_ws && rosdep check --rosdistro $(ROS_DISTRO) --from-paths src --ignore-src --skip-keys ament_python

ros-build:
	cd ros2_ws && colcon build --symlink-install

ros-test:
	cd ros2_ws && colcon test && colcon test-result --verbose

ros-check: ros-deps ros-build ros-test
