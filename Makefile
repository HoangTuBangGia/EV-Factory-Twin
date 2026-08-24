ROS_DISTRO ?= jazzy
POSTGRES_IMAGE ?= postgres:17-alpine
CLOUD_SQL_PGPASSFILE ?= /tmp/ev-twin-cloudsql.pgpass
CLOUD_SQL_PROXY_HOST ?= 127.0.0.1
CLOUD_SQL_PROXY_PORT ?= 5433

.PHONY: sync lint format format-check migration-check postgres-migrate postgres-migrate-docker postgres-migrate-file-docker postgres-seed-docker integration postgres-smoke test test-cov typecheck check backend user-create frontend-sync frontend frontend-lint frontend-typecheck frontend-test frontend-build frontend-check frontend-browser-install frontend-smoke frontend-e2e-list frontend-e2e docker-build ros-deps ros-build ros-test ros-check

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
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest -p pytest_asyncio.plugin tests/integration/test_postgres_migrations.py

postgres-migrate:
	@test -n "$(MIGRATION_DATABASE_URL)" || (echo "MIGRATION_DATABASE_URL is required" >&2; exit 2)
	@for migration in postgres/migrations/*.sql; do \
		echo "Applying $$migration"; \
		psql "$(MIGRATION_DATABASE_URL)" -v ON_ERROR_STOP=1 -f "$$migration" || exit 1; \
	done

postgres-migrate-docker:
	@test -f "$(CLOUD_SQL_PGPASSFILE)" || \
		(echo "CLOUD_SQL_PGPASSFILE does not exist: $(CLOUD_SQL_PGPASSFILE)" >&2; exit 2)
	docker run --rm --network host \
		--env PGPASSFILE=/run/secrets/pgpass \
		--volume "$(CLOUD_SQL_PGPASSFILE):/run/secrets/pgpass:ro" \
		--volume "$(CURDIR)/postgres/migrations:/migrations:ro" \
		"$(POSTGRES_IMAGE)" sh -eu -c 'for migration in /migrations/*.sql; do \
			echo "Applying $$migration"; \
			psql --host="$(CLOUD_SQL_PROXY_HOST)" --port="$(CLOUD_SQL_PROXY_PORT)" \
				--username=postgres --dbname=postgres --set=ON_ERROR_STOP=1 \
				--file="$$migration"; \
		done'

postgres-migrate-file-docker:
	@test -n "$(MIGRATION_FILE)" || (echo "MIGRATION_FILE is required" >&2; exit 2)
	@case "$(MIGRATION_FILE)" in */*) echo "MIGRATION_FILE must be a basename" >&2; exit 2;; esac
	@test -f "postgres/migrations/$(MIGRATION_FILE)" || \
		(echo "migration does not exist: $(MIGRATION_FILE)" >&2; exit 2)
	@test -f "$(CLOUD_SQL_PGPASSFILE)" || \
		(echo "CLOUD_SQL_PGPASSFILE does not exist: $(CLOUD_SQL_PGPASSFILE)" >&2; exit 2)
	docker run --rm --network host \
		--env PGPASSFILE=/run/secrets/pgpass \
		--volume "$(CLOUD_SQL_PGPASSFILE):/run/secrets/pgpass:ro" \
		--volume "$(CURDIR)/postgres/migrations:/migrations:ro" \
		"$(POSTGRES_IMAGE)" psql \
			--host="$(CLOUD_SQL_PROXY_HOST)" --port="$(CLOUD_SQL_PROXY_PORT)" \
			--username=postgres --dbname=postgres --set=ON_ERROR_STOP=1 \
			--file="/migrations/$(MIGRATION_FILE)"

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

ros-deps:
	python3 -c "from colcon_ros.task.ament_python.build import AmentPythonBuildTask"
	cd ros2_ws && rosdep check --rosdistro $(ROS_DISTRO) --from-paths src --ignore-src --skip-keys ament_python

ros-build:
	cd ros2_ws && colcon build --symlink-install

ros-test:
	cd ros2_ws && colcon test && colcon test-result --verbose

ros-check: ros-deps ros-build ros-test
