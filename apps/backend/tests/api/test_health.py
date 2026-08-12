import tomllib
from pathlib import Path

import pytest
from ev_twin_api.main import app
from ev_twin_api.schemas.health import HealthResponse
from httpx import ASGITransport, AsyncClient

PYPROJECT_PATH = Path(__file__).resolve().parents[2] / "pyproject.toml"


def _pyproject_version() -> str:
    with PYPROJECT_PATH.open("rb") as f:
        data = tomllib.load(f)
    version = data["project"]["version"]
    assert isinstance(version, str)
    return version


@pytest.mark.asyncio
async def test_health() -> None:
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://test") as client,
    ):
        response = await client.get("/health")

    assert response.status_code == 200

    body = HealthResponse.model_validate(response.json())
    assert body.status == "ok"
    assert body.uptime_seconds >= 0
    assert body.version == _pyproject_version()


@pytest.mark.asyncio
async def test_health_not_under_api_v1_prefix() -> None:
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://test") as client,
    ):
        response = await client.get("/api/v1/health")

    assert response.status_code == 404
