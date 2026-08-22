from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from ev_twin_api.core.config import Settings, get_settings
from ev_twin_api.main import app
from ev_twin_api.schemas.telemetry import TelemetryIngressResponse, TelemetryIngressStatus
from httpx2 import AsyncClient

EDGE_SECRET = "0123456789abcdef0123456789abcdef"


@pytest_asyncio.fixture
async def edge_client(client: AsyncClient) -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None,
        edge_telemetry_shared_secret=EDGE_SECRET,
    )
    await app.state.mock_factory.stop()
    original_broadcast = app.state.websocket_manager.broadcast
    try:
        yield client
    finally:
        app.state.websocket_manager.broadcast = original_broadcast
        app.dependency_overrides.pop(get_settings, None)


def telemetry_payload(robot_id: str = "AMR-01") -> dict[str, object]:
    robot = app.state.factory_state.get_robot("AMR-01")
    assert robot is not None
    return {
        "timestamp": (robot.last_seen_at + timedelta(seconds=1)).isoformat(),
        "robot_id": robot_id,
        "pose": {"x": 9.0, "y": 5.0, "yaw": 0.5},
        "velocity": {"linear": 1.0, "angular": 0.0},
        "battery": 80.0,
        "status": "DELIVERING",
        "task_id": "TASK-0001",
        "payload_id": "BP-0001",
    }


def edge_headers(secret: str = EDGE_SECRET) -> dict[str, str]:
    return {"Authorization": f"Bearer {secret}"}


@pytest.mark.asyncio
async def test_missing_or_invalid_edge_credential_returns_401(edge_client: AsyncClient) -> None:
    missing = await edge_client.post("/internal/v1/telemetry", json=telemetry_payload())
    invalid = await edge_client.post(
        "/internal/v1/telemetry",
        json=telemetry_payload(),
        headers=edge_headers("x" * 32),
    )

    assert missing.status_code == 401
    assert missing.headers["www-authenticate"] == "Bearer"
    assert invalid.status_code == 401
    assert EDGE_SECRET not in missing.text + invalid.text


@pytest.mark.asyncio
async def test_unconfigured_edge_ingress_fails_closed(edge_client: AsyncClient) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)

    response = await edge_client.post(
        "/internal/v1/telemetry",
        json=telemetry_payload(),
        headers=edge_headers(),
    )

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_valid_edge_telemetry_updates_state_and_broadcasts(edge_client: AsyncClient) -> None:
    broadcast = AsyncMock()
    app.state.websocket_manager.broadcast = broadcast
    payload = telemetry_payload()

    response = await edge_client.post(
        "/internal/v1/telemetry",
        json=payload,
        headers=edge_headers(),
    )

    assert response.status_code == 200
    result = TelemetryIngressResponse.model_validate(response.json())
    assert result.status == TelemetryIngressStatus.ACCEPTED
    robot = app.state.factory_state.get_robot("AMR-01")
    assert robot is not None
    assert robot.pose.x == 9.0
    assert robot.battery == 80.0
    broadcast.assert_awaited_once()


@pytest.mark.asyncio
async def test_unknown_robot_returns_404(edge_client: AsyncClient) -> None:
    response = await edge_client.post(
        "/internal/v1/telemetry",
        json=telemetry_payload("AMR-99"),
        headers=edge_headers(),
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_active_mock_source_returns_409(edge_client: AsyncClient) -> None:
    await app.state.mock_factory.start()
    try:
        response = await edge_client.post(
            "/internal/v1/telemetry",
            json=telemetry_payload(),
            headers=edge_headers(),
        )
    finally:
        await app.state.mock_factory.stop()

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_invalid_telemetry_returns_422(edge_client: AsyncClient) -> None:
    response = await edge_client.post(
        "/internal/v1/telemetry",
        json={**telemetry_payload(), "battery": 101},
        headers=edge_headers(),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_timestamp_without_timezone_returns_422(edge_client: AsyncClient) -> None:
    response = await edge_client.post(
        "/internal/v1/telemetry",
        json={**telemetry_payload(), "timestamp": "2026-08-11T04:00:00.125"},
        headers=edge_headers(),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_timestamp_beyond_future_skew_returns_422(edge_client: AsyncClient) -> None:
    response = await edge_client.post(
        "/internal/v1/telemetry",
        json={
            **telemetry_payload(),
            "timestamp": (datetime.now(UTC) + timedelta(seconds=301)).isoformat(),
        },
        headers=edge_headers(),
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Telemetry timestamp exceeds the allowed future skew"}
