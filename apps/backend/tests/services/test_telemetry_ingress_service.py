import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from ev_twin_api.schemas.factory import MockFactoryConfig
from ev_twin_api.schemas.telemetry import RobotTelemetry, TelemetryIngressStatus
from ev_twin_api.services.factory_state import FactoryState
from ev_twin_api.services.mock_factory import MockFactory
from ev_twin_api.services.runtime_history import InMemoryRuntimeHistoryRepository
from ev_twin_api.services.telemetry_ingress import (
    FutureTimestampError,
    MockSourceActiveError,
    TelemetryIngressService,
    UnknownRobotError,
)
from ev_twin_api.services.telemetry_persistence import TelemetryPersistenceWorker
from ev_twin_api.services.websocket_manager import WebSocketManager


def make_service(
    max_future_skew_seconds: float = 5,
) -> tuple[TelemetryIngressService, FactoryState, WebSocketManager, MockFactory]:
    config = MockFactoryConfig()
    state = FactoryState(config)
    manager = WebSocketManager()
    mock_factory = MockFactory(state, config, manager, enabled=False)
    return (
        TelemetryIngressService(state, manager, mock_factory, max_future_skew_seconds),
        state,
        manager,
        mock_factory,
    )


def make_telemetry(state: FactoryState, **overrides: object) -> RobotTelemetry:
    robot = state.get_robot("AMR-01")
    assert robot is not None
    values: dict[str, object] = {
        "timestamp": robot.last_seen_at + timedelta(seconds=1),
        "robot_id": robot.id,
        "pose": {"x": 8.0, "y": 4.0, "yaw": 1.2},
        "velocity": {"linear": 0.8, "angular": 0.1},
        "battery": 72.5,
        "status": "DELIVERING",
        "task_id": "TASK-0001",
        "payload_id": "BP-0001",
    }
    values.update(overrides)
    return RobotTelemetry.model_validate(values)


@pytest.mark.asyncio
async def test_ingest_updates_state_and_broadcasts_canonical_event() -> None:
    service, state, manager, _ = make_service()
    manager.broadcast = AsyncMock()  # type: ignore[method-assign]
    telemetry = make_telemetry(state)

    result = await service.ingest(telemetry)

    assert result.status == TelemetryIngressStatus.ACCEPTED
    stored = state.get_robot("AMR-01")
    assert stored is not None
    assert stored.name == "AMR-01"
    assert stored.pose == telemetry.pose
    assert stored.velocity == telemetry.velocity
    assert stored.battery == telemetry.battery
    assert stored.status == telemetry.status
    assert stored.last_seen_at == telemetry.timestamp
    manager.broadcast.assert_awaited_once_with(
        {"type": "robot.telemetry", "data": telemetry.model_dump(mode="json")}
    )


@pytest.mark.asyncio
async def test_stale_or_duplicate_sample_is_idempotent_and_not_broadcast() -> None:
    service, state, manager, _ = make_service()
    manager.broadcast = AsyncMock()  # type: ignore[method-assign]
    telemetry = make_telemetry(state)
    await service.ingest(telemetry)
    manager.broadcast.reset_mock()

    result = await service.ingest(telemetry)

    assert result.status == TelemetryIngressStatus.IGNORED_STALE
    manager.broadcast.assert_not_awaited()


@pytest.mark.asyncio
async def test_stale_sample_is_kept_as_late_history_without_overwriting_snapshot() -> None:
    config = MockFactoryConfig()
    state = FactoryState(config)
    manager = WebSocketManager()
    mock_factory = MockFactory(state, config, manager, enabled=False)
    history = InMemoryRuntimeHistoryRepository()
    service = TelemetryIngressService(state, manager, mock_factory, 5, history)
    telemetry = make_telemetry(state)
    late = telemetry.model_copy(update={"timestamp": telemetry.timestamp - timedelta(seconds=1)})

    await service.ingest(telemetry)
    result = await service.ingest(late)

    assert result.status == TelemetryIngressStatus.IGNORED_STALE
    assert len(history.telemetry) == 2
    assert history.telemetry[0][2] == TelemetryIngressStatus.ACCEPTED
    assert history.telemetry[1][2] == TelemetryIngressStatus.IGNORED_STALE


@pytest.mark.asyncio
async def test_future_sample_is_rejected_without_poisoning_state_or_broadcasting() -> None:
    service, state, manager, _ = make_service()
    manager.broadcast = AsyncMock()  # type: ignore[method-assign]
    original = state.get_robot("AMR-01")
    assert original is not None
    telemetry = make_telemetry(state, timestamp=datetime.now(UTC) + timedelta(seconds=6))

    with pytest.raises(FutureTimestampError):
        await service.ingest(telemetry)

    assert state.get_robot("AMR-01") == original
    manager.broadcast.assert_not_awaited()


@pytest.mark.asyncio
async def test_future_skew_limit_is_configurable() -> None:
    service, state, _, _ = make_service(max_future_skew_seconds=10)
    telemetry = make_telemetry(state, timestamp=datetime.now(UTC) + timedelta(seconds=6))

    result = await service.ingest(telemetry)

    assert result.status == TelemetryIngressStatus.ACCEPTED


@pytest.mark.asyncio
async def test_unknown_robot_is_rejected_without_broadcast() -> None:
    service, state, manager, _ = make_service()
    manager.broadcast = AsyncMock()  # type: ignore[method-assign]

    with pytest.raises(UnknownRobotError):
        await service.ingest(make_telemetry(state, robot_id="AMR-99"))

    manager.broadcast.assert_not_awaited()


@pytest.mark.asyncio
async def test_active_mock_source_blocks_edge_ingress() -> None:
    service, state, _, mock_factory = make_service()
    mock_factory.running = True

    with pytest.raises(MockSourceActiveError):
        await service.ingest(make_telemetry(state))


@pytest.mark.asyncio
async def test_concurrent_samples_keep_the_newest_timestamp() -> None:
    service, state, manager, _ = make_service()

    async def delayed_broadcast(_: dict[str, object]) -> None:
        await asyncio.sleep(0)

    manager.broadcast = AsyncMock(side_effect=delayed_broadcast)  # type: ignore[method-assign]
    older = make_telemetry(state, pose={"x": 7.0, "y": 4.0, "yaw": 0.0})
    newer = make_telemetry(
        state,
        timestamp=older.timestamp + timedelta(seconds=1),
        pose={"x": 11.0, "y": 6.0, "yaw": 0.0},
    )

    await asyncio.gather(service.ingest(newer), service.ingest(older))

    stored = state.get_robot("AMR-01")
    assert stored is not None
    assert stored.last_seen_at == newer.timestamp
    assert stored.pose.x == 11.0


@pytest.mark.asyncio
async def test_stale_ordering_is_independent_per_robot() -> None:
    service, state, _, _ = make_service()
    amr_01 = make_telemetry(state)
    amr_02 = make_telemetry(state, robot_id="AMR-02")

    await service.ingest(amr_01)
    stale = await service.ingest(amr_01)
    accepted = await service.ingest(amr_02)

    assert stale.status == TelemetryIngressStatus.IGNORED_STALE
    assert accepted.status == TelemetryIngressStatus.ACCEPTED
    assert state.get_robot("AMR-02").last_seen_at == amr_02.timestamp


@pytest.mark.asyncio
async def test_buffered_ingress_does_not_wait_for_history_persistence() -> None:
    service, state, manager, mock_factory = make_service()
    history = InMemoryRuntimeHistoryRepository()
    history.record_telemetry = AsyncMock()  # type: ignore[method-assign]
    worker = TelemetryPersistenceWorker(history, None, flush_seconds=1)
    service = TelemetryIngressService(
        state,
        manager,
        mock_factory,
        5,
        history,
        persistence_worker=worker,
    )

    result = await service.ingest(make_telemetry(state))

    assert result.status == TelemetryIngressStatus.ACCEPTED
    history.record_telemetry.assert_not_awaited()
    await worker.flush()
    history.record_telemetry.assert_awaited_once()
