from datetime import UTC, datetime, timedelta

import pytest
from ev_twin_api.main import app
from ev_twin_api.schemas.telemetry import TelemetryIngressStatus, robot_to_telemetry
from httpx2 import AsyncClient


@pytest.mark.asyncio
async def test_robot_history_requires_bounded_utc_range_and_returns_latest_first(
    client: AsyncClient,
) -> None:
    repository = app.state.runtime_history_repository
    robot = app.state.factory_state.get_robot("AMR-01")
    assert robot is not None
    now = datetime.now(UTC).replace(microsecond=123_000)
    first = robot_to_telemetry(robot).model_copy(update={"timestamp": now})
    second = first.model_copy(update={"timestamp": now + timedelta(seconds=1)})
    await repository.record_telemetry(first, now, TelemetryIngressStatus.ACCEPTED)
    await repository.record_telemetry(
        second, now + timedelta(seconds=1), TelemetryIngressStatus.ACCEPTED
    )

    response = await client.get(
        "/api/v1/robots/AMR-01/telemetry-history",
        params={
            "start": (now - timedelta(seconds=1)).isoformat(),
            "end": (now + timedelta(seconds=2)).isoformat(),
            "limit": 1,
        },
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert datetime.fromisoformat(response.json()[0]["telemetry"]["timestamp"]) == second.timestamp


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "params",
    [
        {"start": "2026-08-26T00:00:00", "end": "2026-08-26T01:00:00Z"},
        {"start": "2026-08-26T02:00:00Z", "end": "2026-08-26T01:00:00Z"},
        {"start": "2026-08-26T00:00:00Z", "end": "2026-08-26T01:00:00Z", "limit": 501},
    ],
)
async def test_robot_history_rejects_invalid_range(
    params: dict[str, object], client: AsyncClient
) -> None:
    response = await client.get(
        "/api/v1/robots/AMR-01/telemetry-history",
        params=params,
    )

    assert response.status_code == 422
