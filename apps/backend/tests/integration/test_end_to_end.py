from unittest.mock import AsyncMock

import pytest
from ev_twin_api.api.metrics import get_metrics
from ev_twin_api.api.tasks import list_tasks
from ev_twin_api.schemas.factory import MockFactoryConfig
from ev_twin_api.schemas.metrics import FactoryMetrics
from ev_twin_api.schemas.task import Task
from ev_twin_api.schemas.telemetry import RobotTelemetry
from ev_twin_api.services.factory_state import FactoryState
from ev_twin_api.services.mock_factory import MockFactory
from ev_twin_api.services.websocket_manager import WebSocketManager


@pytest.mark.asyncio
async def test_mock_engine_end_to_end_task_delivery() -> None:
    """Exercise engine, realtime event contracts, state and REST together."""
    config = MockFactoryConfig(
        task_interval_seconds=1.0,
        simulation_speed=10.0,
        robot_speed_mps=3.0,
    )
    state = FactoryState(config)
    manager = WebSocketManager()
    mock_factory = MockFactory(state, config, manager)
    broadcast = AsyncMock()
    manager.broadcast = broadcast

    for _ in range(300):
        await mock_factory.tick(0.1)
        if state.get_metrics().completed_tasks >= 1:
            break
    # Metrics are evented at 1 Hz; advance once more after completion so the
    # updated aggregate is included in a metrics.updated broadcast.
    await mock_factory.tick(1.0)

    events = [call.args[0] for call in broadcast.await_args_list]
    task_events = [
        Task.model_validate(event["data"]) for event in events if event["type"] == "task.updated"
    ]
    telemetry_events = [
        RobotTelemetry.model_validate(event["data"])
        for event in events
        if event["type"] == "robot.telemetry"
    ]
    metrics_events = [
        FactoryMetrics.model_validate(event["data"])
        for event in events
        if event["type"] == "metrics.updated"
    ]

    queued = [task for task in task_events if task.status == "QUEUED"]
    assigned = [task for task in task_events if task.status == "ASSIGNED"]
    completed = [task for task in task_events if task.status == "COMPLETED"]
    assert queued
    assert assigned
    assert completed

    assigned_robot_id = assigned[0].assigned_robot_id
    positions = [
        (telemetry.pose.x, telemetry.pose.y)
        for telemetry in telemetry_events
        if telemetry.robot_id == assigned_robot_id
    ]
    assert len(positions) >= 2
    assert positions[0] != positions[-1]
    assert any(metrics.completed_tasks >= 1 for metrics in metrics_events)

    tasks_snapshot = await list_tasks(state)
    metrics_snapshot = await get_metrics(state)
    assert any(task.status == "COMPLETED" for task in tasks_snapshot)
    assert metrics_snapshot.completed_tasks >= 1
