ROS_DISTRO ?= jazzy

.PHONY: sync lint format format-check migration-check integration test test-cov typecheck check backend docker-build supabase-start supabase-status supabase-reset supabase-stop ros-deps ros-build ros-test ros-check

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
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest -p pytest_asyncio.plugin tests/integration/test_supabase_migrations.py

integration:
	APP_ENV=test DATABASE_URL= PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest -p pytest_asyncio.plugin tests/integration

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

docker-build:
	docker build --file apps/backend/Dockerfile --tag ev-factory-twin-api:local .

supabase-start:
	supabase start

supabase-status:
	supabase status

supabase-reset:
	supabase db reset

supabase-stop:
	supabase stop

ros-deps:
	python3 -c "from colcon_ros.task.ament_python.build import AmentPythonBuildTask"
	cd ros2_ws && rosdep check --rosdistro $(ROS_DISTRO) --from-paths src --ignore-src --skip-keys ament_python

ros-build:
	cd ros2_ws && colcon build --symlink-install

ros-test:
	cd ros2_ws && colcon test && colcon test-result --verbose

ros-check: ros-deps ros-build ros-test
