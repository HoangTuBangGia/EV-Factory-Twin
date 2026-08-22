FROM ghcr.io/astral-sh/uv:0.8.22-python3.12-bookworm-slim

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY apps/backend ./apps/backend
COPY packages/twin-core ./packages/twin-core
COPY services/simulation ./services/simulation
COPY evaluation ./evaluation

RUN uv sync --locked --no-dev --package ev-twin-api \
    && useradd --create-home --uid 10001 app

USER app

EXPOSE 8000

CMD ["sh", "-c", "exec uv run --no-sync --package ev-twin-api uvicorn ev_twin_api.main:app --app-dir apps/backend/src --host 0.0.0.0 --port \"${PORT:-8000}\""]

