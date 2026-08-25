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
GCP_BACKEND_CORS_ORIGINS ?= https://c3-app-078.vercel.app,https://ev-factory-twin-gcp.vercel.app
GCP_DATABASE_URL_SECRET ?= ev-twin-database-url
GCP_AUTH_JWT_SECRET ?= ev-twin-auth-jwt-secret
GCP_EDGE_SECRET ?= ev-twin-edge-telemetry-secret
GCP_GITHUB_DEPLOY_SERVICE_ACCOUNT ?= ev-twin-github-deploy
GCP_GITHUB_DEPLOY_SERVICE_ACCOUNT_EMAIL = $(GCP_GITHUB_DEPLOY_SERVICE_ACCOUNT)@$(GCP_PROJECT).iam.gserviceaccount.com
GCP_WORKLOAD_IDENTITY_POOL ?= github-actions
GCP_WORKLOAD_IDENTITY_PROVIDER ?= github-develop
GITHUB_REPOSITORY ?= HoangTuBangGia/EV-Factory-Twin
GCP_PRODUCTION_CLOUD_SQL_INSTANCE ?= ev-twin-postgres-prod-01
GCP_PRODUCTION_CLOUD_SQL_CONNECTION_NAME = $(GCP_PROJECT):$(GCP_REGION):$(GCP_PRODUCTION_CLOUD_SQL_INSTANCE)
GCP_PRODUCTION_BACKEND_SERVICE_ACCOUNT ?= ev-twin-api-prod
GCP_PRODUCTION_BACKEND_SERVICE_ACCOUNT_EMAIL = $(GCP_PRODUCTION_BACKEND_SERVICE_ACCOUNT)@$(GCP_PROJECT).iam.gserviceaccount.com
GCP_PRODUCTION_DATABASE_URL_SECRET ?= ev-twin-prod-database-url
GCP_PRODUCTION_AUTH_JWT_SECRET ?= ev-twin-prod-auth-jwt-secret
GCP_PRODUCTION_EDGE_SECRET ?= ev-twin-prod-edge-telemetry-secret
GCP_GITHUB_PRODUCTION_DEPLOY_SERVICE_ACCOUNT ?= ev-twin-github-prod-deploy
GCP_GITHUB_PRODUCTION_DEPLOY_SERVICE_ACCOUNT_EMAIL = $(GCP_GITHUB_PRODUCTION_DEPLOY_SERVICE_ACCOUNT)@$(GCP_PROJECT).iam.gserviceaccount.com
GCP_WORKLOAD_IDENTITY_MAIN_PROVIDER ?= github-main
GCP_PRODUCTION_CLOUD_SQL_PGPASSFILE ?= /tmp/ev-twin-production-cloudsql.pgpass
GCP_PRODUCTION_CLOUD_SQL_PROXY_NAME ?= ev-twin-production-cloud-sql-proxy
GCP_PRODUCTION_EDGE_VM ?= ev-twin-edge-prod-01
GCP_PRODUCTION_EDGE_ZONE ?= us-central1-a
GCP_PRODUCTION_EDGE_MACHINE_TYPE ?= e2-standard-4
GCP_PRODUCTION_EDGE_NETWORK ?= ev-twin-edge-vpc
GCP_PRODUCTION_EDGE_SUBNET ?= ev-twin-edge-us-central1
GCP_EDGE_ROUTER ?= ev-twin-edge-router
GCP_EDGE_NAT ?= ev-twin-edge-nat
CLOUD_SQL_PROXY_IMAGE ?= gcr.io/cloud-sql-connectors/cloud-sql-proxy:2.18.2

.PHONY: sync lint format format-check migration-check postgres-migrate postgres-migrate-docker postgres-migrations-baseline-docker postgres-seed-docker integration postgres-smoke test test-cov typecheck check backend user-create frontend-sync frontend frontend-lint frontend-typecheck frontend-test frontend-build frontend-check frontend-browser-install frontend-smoke frontend-e2e-list frontend-e2e docker-build gcp-backend-check gcp-backend-apis gcp-artifact-repository-create gcp-cloud-build-access gcp-backend-service-account-create gcp-backend-cloudsql-access gcp-backend-secrets-create gcp-backend-database-user-create gcp-secret-version-add gcp-backend-secret-access gcp-backend-build gcp-backend-deploy gcp-backend-smoke gcp-develop-cicd-apis gcp-develop-cicd-service-account-create gcp-develop-cicd-wif-create gcp-develop-cicd-access gcp-production-cloudsql-create gcp-production-postgres-password-set gcp-production-backend-service-account-create gcp-production-backend-cloudsql-access gcp-production-secrets-create gcp-production-database-user-create gcp-production-backend-secret-access gcp-production-pgpassfile-create gcp-production-cloudsql-proxy-start gcp-production-cloudsql-proxy-stop gcp-production-user-create gcp-production-seed gcp-production-postgres-smoke gcp-production-cicd-service-account-create gcp-production-cicd-wif-create gcp-production-cicd-access gcp-production-edge-vm-create gcp-production-edge-bootstrap gcp-edge-router-create gcp-edge-nat-create github-gcp-environments-configure github-gcp-environments-list ros-deps ros-build ros-test ros-check

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
		tests/integration/test_gcp_cloud_run_backend.py \
		tests/integration/test_gcp_develop_cicd.py

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

gcp-backend-smoke:
	@service_url=$$(gcloud run services describe "$(GCP_BACKEND_SERVICE)" \
		--project="$(GCP_PROJECT)" --region="$(GCP_REGION)" \
		--format='value(status.url)'); \
	test -n "$$service_url"; \
	curl --fail --silent --show-error "$$service_url/health"; echo; \
	status=$$(curl --silent --show-error --output /dev/null \
		--write-out '%{http_code}' "$$service_url/api/v1/factory"); \
	test "$$status" = 401; \
	allowed_origin=$$(curl --silent --show-error --dump-header - --output /dev/null \
		--request OPTIONS --header "Origin: $(GCP_BACKEND_CORS_ORIGINS)" \
		--header 'Access-Control-Request-Method: GET' \
		"$$service_url/api/v1/factory" | \
		sed -n 's/^access-control-allow-origin:[[:space:]]*//Ip' | tr -d '\r'); \
	test "$$allowed_origin" = "$(GCP_BACKEND_CORS_ORIGINS)"; \
	printf 'service_url=%s\nunauthenticated_factory=%s\nallowed_origin=%s\n' \
		"$$service_url" "$$status" "$$allowed_origin"

gcp-develop-cicd-apis:
	gcloud services enable iamcredentials.googleapis.com sts.googleapis.com \
		--project="$(GCP_PROJECT)"

gcp-develop-cicd-service-account-create:
	gcloud iam service-accounts create "$(GCP_GITHUB_DEPLOY_SERVICE_ACCOUNT)" \
		--project="$(GCP_PROJECT)" \
		--display-name="EV Twin GitHub Develop Deployer"

gcp-develop-cicd-wif-create:
	gcloud iam workload-identity-pools create "$(GCP_WORKLOAD_IDENTITY_POOL)" \
		--project="$(GCP_PROJECT)" --location=global \
		--display-name="GitHub Actions"
	gcloud iam workload-identity-pools providers create-oidc \
		"$(GCP_WORKLOAD_IDENTITY_PROVIDER)" \
		--project="$(GCP_PROJECT)" --location=global \
		--workload-identity-pool="$(GCP_WORKLOAD_IDENTITY_POOL)" \
		--display-name="EV Twin develop" \
		--issuer-uri="https://token.actions.githubusercontent.com" \
		--attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
		--attribute-condition="assertion.repository == '$(GITHUB_REPOSITORY)' && assertion.ref == 'refs/heads/develop'"

gcp-develop-cicd-access:
	@project_number=$$(gcloud projects describe "$(GCP_PROJECT)" \
		--format='value(projectNumber)'); \
	gcloud iam service-accounts add-iam-policy-binding \
		"$(GCP_GITHUB_DEPLOY_SERVICE_ACCOUNT_EMAIL)" \
		--project="$(GCP_PROJECT)" \
		--role=roles/iam.workloadIdentityUser \
		--member="principalSet://iam.googleapis.com/projects/$$project_number/locations/global/workloadIdentityPools/$(GCP_WORKLOAD_IDENTITY_POOL)/attribute.repository/$(GITHUB_REPOSITORY)"
	@for role in roles/run.developer roles/serviceusage.serviceUsageConsumer; do \
		gcloud projects add-iam-policy-binding "$(GCP_PROJECT)" \
			--member="serviceAccount:$(GCP_GITHUB_DEPLOY_SERVICE_ACCOUNT_EMAIL)" \
			--role="$$role" || exit 1; \
	done
	gcloud artifacts repositories add-iam-policy-binding "$(GCP_ARTIFACT_REPOSITORY)" \
		--project="$(GCP_PROJECT)" --location="$(GCP_REGION)" \
		--member="serviceAccount:$(GCP_GITHUB_DEPLOY_SERVICE_ACCOUNT_EMAIL)" \
		--role=roles/artifactregistry.writer
	gcloud iam service-accounts add-iam-policy-binding \
		"$(GCP_BACKEND_SERVICE_ACCOUNT_EMAIL)" \
		--project="$(GCP_PROJECT)" \
		--member="serviceAccount:$(GCP_GITHUB_DEPLOY_SERVICE_ACCOUNT_EMAIL)" \
		--role=roles/iam.serviceAccountUser

gcp-production-cloudsql-create:
	gcloud sql instances create "$(GCP_PRODUCTION_CLOUD_SQL_INSTANCE)" \
		--project="$(GCP_PROJECT)" --region="$(GCP_REGION)" \
		--database-version=POSTGRES_17 --edition=enterprise --tier=db-f1-micro \
		--availability-type=zonal --storage-type=SSD --storage-size=10 \
		--database-flags=cloudsql.enable_pg_cron=on

gcp-production-edge-vm-create:
	gcloud compute instances create "$(GCP_PRODUCTION_EDGE_VM)" \
		--project="$(GCP_PROJECT)" --zone="$(GCP_PRODUCTION_EDGE_ZONE)" \
		--machine-type="$(GCP_PRODUCTION_EDGE_MACHINE_TYPE)" \
		--network="$(GCP_PRODUCTION_EDGE_NETWORK)" \
		--subnet="$(GCP_PRODUCTION_EDGE_SUBNET)" \
		--no-address --no-service-account --no-scopes \
		--tags=ev-twin-iap-ssh \
		--image-family=ubuntu-2404-lts-amd64 --image-project=ubuntu-os-cloud \
		--boot-disk-type=pd-balanced --boot-disk-size=50GB \
		--boot-disk-auto-delete --provisioning-model=STANDARD \
		--maintenance-policy=MIGRATE --restart-on-failure \
		--shielded-secure-boot --shielded-vtpm \
		--shielded-integrity-monitoring --deletion-protection

gcp-production-edge-bootstrap:
	gcloud compute ssh "$(GCP_PRODUCTION_EDGE_VM)" \
		--project="$(GCP_PROJECT)" --zone="$(GCP_PRODUCTION_EDGE_ZONE)" \
		--tunnel-through-iap --command='sudo bash -s' < scripts/gcp_edge_bootstrap.sh

gcp-edge-router-create:
	gcloud compute routers create "$(GCP_EDGE_ROUTER)" \
		--project="$(GCP_PROJECT)" --region="$(GCP_REGION)" \
		--network="$(GCP_PRODUCTION_EDGE_NETWORK)"

gcp-edge-nat-create:
	gcloud compute routers nats create "$(GCP_EDGE_NAT)" \
		--project="$(GCP_PROJECT)" --router="$(GCP_EDGE_ROUTER)" \
		--router-region="$(GCP_REGION)" \
		--nat-custom-subnet-ip-ranges="$(GCP_PRODUCTION_EDGE_SUBNET)" \
		--auto-allocate-nat-external-ips

gcp-production-postgres-password-set:
	@bash -eu -o pipefail -c '\
		read -rsp "New production postgres password: " password; echo; \
		read -rsp "Confirm production postgres password: " confirmation; echo; \
		test "$${#password}" -ge 32 || { echo "password must be at least 32 characters" >&2; exit 2; }; \
		test "$$password" = "$$confirmation" || { echo "passwords do not match" >&2; exit 2; }; \
		gcloud sql users set-password postgres \
			--instance="$(GCP_PRODUCTION_CLOUD_SQL_INSTANCE)" \
			--project="$(GCP_PROJECT)" --password="$$password"; \
		unset password confirmation'

gcp-production-backend-service-account-create:
	gcloud iam service-accounts create "$(GCP_PRODUCTION_BACKEND_SERVICE_ACCOUNT)" \
		--project="$(GCP_PROJECT)" \
		--display-name="EV Twin Cloud Run Production Backend"

gcp-production-backend-cloudsql-access:
	gcloud projects add-iam-policy-binding "$(GCP_PROJECT)" \
		--member="serviceAccount:$(GCP_PRODUCTION_BACKEND_SERVICE_ACCOUNT_EMAIL)" \
		--role=roles/cloudsql.client

gcp-production-secrets-create:
	@for secret in "$(GCP_PRODUCTION_DATABASE_URL_SECRET)" "$(GCP_PRODUCTION_AUTH_JWT_SECRET)" "$(GCP_PRODUCTION_EDGE_SECRET)"; do \
		gcloud secrets create "$$secret" --project="$(GCP_PROJECT)" \
			--replication-policy=automatic || exit 1; \
	done

gcp-production-database-user-create:
	@bash -eu -o pipefail -c '\
		read -rsp "New production ev_twin_app password: " password; echo; \
		read -rsp "Confirm production database password: " confirmation; echo; \
		test "$${#password}" -ge 32 || { echo "password must be at least 32 characters" >&2; exit 2; }; \
		test "$$password" = "$$confirmation" || { echo "passwords do not match" >&2; exit 2; }; \
		gcloud sql users create ev_twin_app \
			--instance="$(GCP_PRODUCTION_CLOUD_SQL_INSTANCE)" \
			--project="$(GCP_PROJECT)" --password="$$password"; \
		encoded_password=$$(printf "%s" "$$password" | python3 -c \
			"import sys, urllib.parse; print(urllib.parse.quote(sys.stdin.read(), safe=\"\"), end=\"\")"); \
		printf "postgresql+asyncpg://ev_twin_app:%s@/postgres?host=/cloudsql/$(GCP_PRODUCTION_CLOUD_SQL_CONNECTION_NAME)" \
			"$$encoded_password" | gcloud secrets versions add \
			"$(GCP_PRODUCTION_DATABASE_URL_SECRET)" \
			--project="$(GCP_PROJECT)" --data-file=-; \
		unset password confirmation encoded_password'

gcp-production-backend-secret-access:
	@for secret in "$(GCP_PRODUCTION_DATABASE_URL_SECRET)" "$(GCP_PRODUCTION_AUTH_JWT_SECRET)" "$(GCP_PRODUCTION_EDGE_SECRET)"; do \
		gcloud secrets add-iam-policy-binding "$$secret" --project="$(GCP_PROJECT)" \
			--member="serviceAccount:$(GCP_PRODUCTION_BACKEND_SERVICE_ACCOUNT_EMAIL)" \
			--role=roles/secretmanager.secretAccessor || exit 1; \
	done

gcp-production-pgpassfile-create:
	@bash -eu -o pipefail -c '\
		read -rsp "Production postgres password: " password; echo; \
		test -n "$$password" || { echo "password must not be empty" >&2; exit 2; }; \
		escaped=$${password//\\/\\\\}; escaped=$${escaped//:/\\:}; \
		umask 077; \
		printf "%s:%s:%s:%s:%s\n" "$(CLOUD_SQL_PROXY_HOST)" "$(CLOUD_SQL_PROXY_PORT)" \
			postgres postgres "$$escaped" > "$(GCP_PRODUCTION_CLOUD_SQL_PGPASSFILE)"; \
		unset password escaped'

gcp-production-cloudsql-proxy-start:
	docker run --detach --rm \
		--name "$(GCP_PRODUCTION_CLOUD_SQL_PROXY_NAME)" \
		--user "$$(id -u):$$(id -g)" --network host \
		--volume "$$HOME/.config/gcloud/application_default_credentials.json:/credentials.json:ro" \
		"$(CLOUD_SQL_PROXY_IMAGE)" \
		--credentials-file=/credentials.json \
		--address="$(CLOUD_SQL_PROXY_HOST)" --port="$(CLOUD_SQL_PROXY_PORT)" \
		"$(GCP_PRODUCTION_CLOUD_SQL_CONNECTION_NAME)"

gcp-production-cloudsql-proxy-stop:
	docker stop "$(GCP_PRODUCTION_CLOUD_SQL_PROXY_NAME)"
	@test -f "$(GCP_PRODUCTION_CLOUD_SQL_PGPASSFILE)" && \
		shred -u "$(GCP_PRODUCTION_CLOUD_SQL_PGPASSFILE)" || true

gcp-production-user-create:
	@test -n "$(EMAIL)" || (echo "EMAIL is required" >&2; exit 2)
	@test -n "$(DISPLAY_NAME)" || (echo "DISPLAY_NAME is required" >&2; exit 2)
	@test -n "$(ROLE)" || (echo "ROLE is required" >&2; exit 2)
	@database_url=$$(gcloud secrets versions access latest \
		--secret="$(GCP_PRODUCTION_DATABASE_URL_SECRET)" --project="$(GCP_PROJECT)" | \
		python3 -c 'import sys; from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit; url = urlsplit(sys.stdin.read()); query = dict(parse_qsl(url.query)); query.update(host="$(CLOUD_SQL_PROXY_HOST)", port="$(CLOUD_SQL_PROXY_PORT)"); print(urlunsplit((url.scheme, url.netloc, url.path, urlencode(query), "")), end="")'); \
	DATABASE_URL="$$database_url" DATABASE_SSL_MODE=disable $(MAKE) user-create \
		EMAIL="$(EMAIL)" DISPLAY_NAME="$(DISPLAY_NAME)" ROLE="$(ROLE)"; \
	unset database_url

gcp-production-seed:
	$(MAKE) postgres-seed-docker \
		CLOUD_SQL_PGPASSFILE="$(GCP_PRODUCTION_CLOUD_SQL_PGPASSFILE)"

gcp-production-postgres-smoke:
	@database_url=$$(gcloud secrets versions access latest \
		--secret="$(GCP_PRODUCTION_DATABASE_URL_SECRET)" --project="$(GCP_PROJECT)" | \
		python3 -c 'import sys; from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit; url = urlsplit(sys.stdin.read()); query = dict(parse_qsl(url.query)); query.update(host="$(CLOUD_SQL_PROXY_HOST)", port="$(CLOUD_SQL_PROXY_PORT)"); print(urlunsplit((url.scheme, url.netloc, url.path, urlencode(query), "")), end="")'); \
	TEST_DATABASE_URL="$$database_url" $(MAKE) postgres-smoke; \
	unset database_url

gcp-production-cicd-service-account-create:
	gcloud iam service-accounts create "$(GCP_GITHUB_PRODUCTION_DEPLOY_SERVICE_ACCOUNT)" \
		--project="$(GCP_PROJECT)" \
		--display-name="EV Twin GitHub Production Deployer"

gcp-production-cicd-wif-create:
	gcloud iam workload-identity-pools providers create-oidc \
		"$(GCP_WORKLOAD_IDENTITY_MAIN_PROVIDER)" \
		--project="$(GCP_PROJECT)" --location=global \
		--workload-identity-pool="$(GCP_WORKLOAD_IDENTITY_POOL)" \
		--display-name="EV Twin main" \
		--issuer-uri="https://token.actions.githubusercontent.com" \
		--attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
		--attribute-condition="assertion.repository == '$(GITHUB_REPOSITORY)' && assertion.ref == 'refs/heads/main'"

gcp-production-cicd-access:
	@project_number=$$(gcloud projects describe "$(GCP_PROJECT)" \
		--format='value(projectNumber)'); \
	gcloud iam service-accounts add-iam-policy-binding \
		"$(GCP_GITHUB_PRODUCTION_DEPLOY_SERVICE_ACCOUNT_EMAIL)" \
		--project="$(GCP_PROJECT)" \
		--role=roles/iam.workloadIdentityUser \
		--member="principalSet://iam.googleapis.com/projects/$$project_number/locations/global/workloadIdentityPools/$(GCP_WORKLOAD_IDENTITY_POOL)/attribute.repository/$(GITHUB_REPOSITORY)"
	@for role in roles/run.developer roles/serviceusage.serviceUsageConsumer; do \
		gcloud projects add-iam-policy-binding "$(GCP_PROJECT)" \
			--member="serviceAccount:$(GCP_GITHUB_PRODUCTION_DEPLOY_SERVICE_ACCOUNT_EMAIL)" \
			--role="$$role" || exit 1; \
	done
	gcloud artifacts repositories add-iam-policy-binding "$(GCP_ARTIFACT_REPOSITORY)" \
		--project="$(GCP_PROJECT)" --location="$(GCP_REGION)" \
		--member="serviceAccount:$(GCP_GITHUB_PRODUCTION_DEPLOY_SERVICE_ACCOUNT_EMAIL)" \
		--role=roles/artifactregistry.writer
	gcloud iam service-accounts add-iam-policy-binding \
		"$(GCP_PRODUCTION_BACKEND_SERVICE_ACCOUNT_EMAIL)" \
		--project="$(GCP_PROJECT)" \
		--member="serviceAccount:$(GCP_GITHUB_PRODUCTION_DEPLOY_SERVICE_ACCOUNT_EMAIL)" \
		--role=roles/iam.serviceAccountUser

github-gcp-environments-configure:
	@project_number=$$(gcloud projects describe "$(GCP_PROJECT)" \
		--format='value(projectNumber)'); \
	for environment in gcp-develop gcp-production; do \
		gh api --method PUT \
			"repos/$(GITHUB_REPOSITORY)/environments/$$environment" >/dev/null || exit 1; \
	done; \
	gh variable set GCP_WORKLOAD_IDENTITY_PROVIDER \
		--repo "$(GITHUB_REPOSITORY)" --env gcp-develop \
		--body "projects/$$project_number/locations/global/workloadIdentityPools/$(GCP_WORKLOAD_IDENTITY_POOL)/providers/$(GCP_WORKLOAD_IDENTITY_PROVIDER)"; \
	gh variable set GCP_DEPLOY_SERVICE_ACCOUNT \
		--repo "$(GITHUB_REPOSITORY)" --env gcp-develop \
		--body "$(GCP_GITHUB_DEPLOY_SERVICE_ACCOUNT_EMAIL)"; \
	gh variable set GCP_WORKLOAD_IDENTITY_PROVIDER \
		--repo "$(GITHUB_REPOSITORY)" --env gcp-production \
		--body "projects/$$project_number/locations/global/workloadIdentityPools/$(GCP_WORKLOAD_IDENTITY_POOL)/providers/$(GCP_WORKLOAD_IDENTITY_MAIN_PROVIDER)"; \
	gh variable set GCP_DEPLOY_SERVICE_ACCOUNT \
		--repo "$(GITHUB_REPOSITORY)" --env gcp-production \
		--body "$(GCP_GITHUB_PRODUCTION_DEPLOY_SERVICE_ACCOUNT_EMAIL)"

github-gcp-environments-list:
	gh variable list --repo "$(GITHUB_REPOSITORY)" --env gcp-develop
	gh variable list --repo "$(GITHUB_REPOSITORY)" --env gcp-production

ros-deps:
	python3 -c "from colcon_ros.task.ament_python.build import AmentPythonBuildTask"
	cd ros2_ws && rosdep check --rosdistro $(ROS_DISTRO) --from-paths src --ignore-src --skip-keys ament_python

ros-build:
	cd ros2_ws && colcon build --symlink-install

ros-test:
	cd ros2_ws && colcon test && colcon test-result --verbose

ros-check: ros-deps ros-build ros-test
