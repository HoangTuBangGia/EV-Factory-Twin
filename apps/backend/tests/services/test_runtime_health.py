from datetime import UTC, datetime, timedelta

import pytest
from ev_twin_api.schemas.edge_runtime import BridgeHealth
from ev_twin_api.schemas.factory import MockFactoryConfig
from ev_twin_api.schemas.telemetry import robot_to_telemetry
from ev_twin_api.services.factory_state import FactoryState
from ev_twin_api.services.runtime_health import RuntimeHealthService
from ev_twin_api.services.runtime_history import InMemoryRuntimeHistoryRepository
from ev_twin_api.services.websocket_manager import WebSocketManager


def setup(now: datetime):
    state = FactoryState(MockFactoryConfig())
    repository = InMemoryRuntimeHistoryRepository()
    service = RuntimeHealthService(
        state,
        repository,
        WebSocketManager(),
        stale_telemetry_seconds=5,
        bridge_disconnect_seconds=5,
        congestion_distance_meters=1.5,
        low_battery_percent=20,
        sweep_seconds=1,
        clock=lambda: now,
    )
    return service, state, repository


@pytest.mark.asyncio
async def test_stale_telemetry_deduplicates_clears_and_retriggers() -> None:
    now = datetime.now(UTC)
    service, state, repository = setup(now)
    telemetry = robot_to_telemetry(state.get_robot("AMR-01"))
    await service.note_telemetry(telemetry, now - timedelta(seconds=6))

    await service.sweep()
    await service.sweep()
    assert [alert.code for alert in await repository.list_alerts()] == ["STALE_TELEMETRY"]

    await service.note_telemetry(telemetry, now)
    assert (await repository.list_alerts())[0].status == "CLEARED"
    await service.note_telemetry(telemetry, now - timedelta(seconds=6))
    await service.sweep()
    assert [alert.status for alert in await repository.list_alerts()] == [
        "ACTIVE",
        "CLEARED",
    ]


@pytest.mark.asyncio
async def test_bridge_degraded_and_disconnect_share_one_condition() -> None:
    now = datetime.now(UTC)
    service, _, repository = setup(now)
    degraded = BridgeHealth(
        bridge_id="edge-main",
        status="DEGRADED",
        robot_ids=["AMR-01"],
        timestamp=now,
        delivered_samples=1,
        failed_deliveries=1,
        last_error="backend unreachable",
    )
    await service.note_bridge_health(degraded)
    await service.sweep()
    assert len(await repository.list_alerts()) == 1

    await service.note_bridge_health(degraded.model_copy(update={"status": "CONNECTED"}))
    assert (await repository.list_alerts())[0].status == "CLEARED"

    await service.note_bridge_health(
        degraded.model_copy(update={"status": "CONNECTED"}),
        now - timedelta(seconds=6),
    )
    await service.sweep()
    assert [alert.status for alert in await repository.list_alerts()] == [
        "ACTIVE",
        "CLEARED",
    ]


@pytest.mark.asyncio
async def test_congestion_clears_when_robots_separate() -> None:
    now = datetime.now(UTC)
    service, state, repository = setup(now)
    first = state.get_robot("AMR-01")
    second = state.get_robot("AMR-02")
    first.status = second.status = "MOVING"
    first.pose.x = second.pose.x = 1
    first.pose.y = second.pose.y = 1
    state.update_robot(first)
    state.update_robot(second)

    await service.note_telemetry(robot_to_telemetry(first), now)
    await service.note_telemetry(robot_to_telemetry(second), now)
    assert (await repository.list_alerts())[0].code == "CONGESTION"

    second.pose.x = 10
    state.update_robot(second)
    await service.note_telemetry(robot_to_telemetry(second), now)
    assert (await repository.list_alerts())[0].status == "CLEARED"
