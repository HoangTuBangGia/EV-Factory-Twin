from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from ev_twin_api.schemas.edge_runtime import BridgeHealth
from ev_twin_api.schemas.factory import MockFactoryConfig
from ev_twin_api.schemas.telemetry import robot_to_telemetry
from ev_twin_api.services.factory_state import FactoryState
from ev_twin_api.services.layout_repository import InMemoryLayoutRepository
from ev_twin_api.services.layout_service import LayoutService
from ev_twin_api.services.runtime_health import RuntimeHealthService
from ev_twin_api.services.runtime_history import InMemoryRuntimeHistoryRepository
from ev_twin_api.services.websocket_manager import WebSocketManager


async def setup(now: datetime):
    state = FactoryState(MockFactoryConfig())
    repository = InMemoryRuntimeHistoryRepository()
    websockets = WebSocketManager()
    websockets.broadcast = AsyncMock()
    service = RuntimeHealthService(
        state,
        repository,
        websockets,
        stale_telemetry_seconds=5,
        bridge_disconnect_seconds=5,
        low_battery_percent=20,
        sweep_seconds=1,
        clock=lambda: now,
    )
    service.set_applied_layout(
        await LayoutService(InMemoryLayoutRepository(include_default=True)).get("LAYOUT-DEFAULT", 1)
    )
    return service, state, repository, websockets


@pytest.mark.asyncio
async def test_stale_telemetry_deduplicates_clears_and_retriggers() -> None:
    now = datetime.now(UTC)
    service, state, repository, websockets = await setup(now)
    telemetry = robot_to_telemetry(state.get_robot("AMR-01"))
    await service.note_telemetry(telemetry, now - timedelta(seconds=6))

    await service.sweep()
    await service.sweep()
    assert [alert.code for alert in await repository.list_alerts()] == ["STALE_TELEMETRY"]

    await service.note_telemetry(telemetry, now)
    assert (await repository.list_alerts())[0].status == "CLEARED"
    assert any(
        call.args[0]["type"] == "alert.updated" and call.args[0]["data"]["status"] == "CLEARED"
        for call in websockets.broadcast.await_args_list
    )
    await service.note_telemetry(telemetry, now - timedelta(seconds=6))
    await service.sweep()
    assert [alert.status for alert in await repository.list_alerts()] == [
        "ACTIVE",
        "CLEARED",
    ]


@pytest.mark.asyncio
async def test_bridge_degraded_and_disconnect_share_one_condition() -> None:
    now = datetime.now(UTC)
    service, _, repository, _ = await setup(now)
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
async def test_congestion_uses_applied_layout_zone_and_clears_on_exit() -> None:
    now = datetime.now(UTC)
    service, state, repository, _ = await setup(now)
    first = state.get_robot("AMR-01")
    second = state.get_robot("AMR-02")
    first.status = second.status = "MOVING"
    first.pose.x = second.pose.x = 1
    first.pose.y = second.pose.y = 1
    state.update_robot(first)
    state.update_robot(second)

    await service.note_telemetry(robot_to_telemetry(first), now)
    await service.note_telemetry(robot_to_telemetry(second), now)
    assert await repository.list_alerts() == []

    first.pose.x = second.pose.x = 11
    first.pose.y = second.pose.y = 7
    state.update_robot(first)
    state.update_robot(second)
    await service.note_telemetry(robot_to_telemetry(first), now)
    await service.note_telemetry(robot_to_telemetry(second), now)
    assert (await repository.list_alerts())[0].code == "CONGESTION"
    assert (await repository.list_alerts())[0].dedupe_key == (
        "CONGESTION:LAYOUT-DEFAULT:1:CONGESTION_01"
    )

    second.pose.x = 1
    second.pose.y = 1
    state.update_robot(second)
    await service.note_telemetry(robot_to_telemetry(second), now)
    assert (await repository.list_alerts())[0].status == "CLEARED"
