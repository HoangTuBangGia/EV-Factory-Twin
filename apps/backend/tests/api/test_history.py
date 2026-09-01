from datetime import UTC, datetime, timedelta

import pytest
from ev_twin_api.main import app
from ev_twin_api.schemas.edge_runtime import TaskUpdate
from ev_twin_api.schemas.metrics import FactoryMetrics
from ev_twin_api.schemas.telemetry import RobotTelemetry, TelemetryIngressStatus
from ev_twin_api.services.kpi_snapshot_writer import KpiSnapshot
from httpx2 import AsyncClient


def _metrics(completed_tasks: int = 0) -> FactoryMetrics:
    return FactoryMetrics(
        completed_tasks=completed_tasks,
        throughput_per_hour=0,
        average_cycle_time_seconds=0,
        active_tasks=0,
        queued_tasks=0,
        starvation_events=0,
        fleet_utilization_percent=0,
    )


@pytest.mark.asyncio
async def test_telemetry_history_is_filterable_and_paginated(client: AsyncClient) -> None:
    repository = app.state.runtime_history_repository
    now = datetime.now(UTC)
    for index, robot_id in enumerate(("AMR-01", "AMR-01", "AMR-02")):
        sample = RobotTelemetry.model_validate(
            {
                "timestamp": now + timedelta(seconds=index),
                "robot_id": robot_id,
                "pose": {"x": index, "y": 0, "yaw": 0},
                "velocity": {"linear": 0, "angular": 0},
                "battery": 90,
                "status": "IDLE",
                "task_id": None,
                "payload_id": None,
            }
        )
        await repository.record_telemetry(sample, now, TelemetryIngressStatus.ACCEPTED)

    response = await client.get(
        "/api/v1/history/telemetry",
        params={
            "start": (now - timedelta(seconds=1)).isoformat(),
            "end": (now + timedelta(seconds=5)).isoformat(),
            "robot_id": "AMR-01",
            "limit": 1,
        },
    )

    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
    assert response.json()["items"][0]["telemetry"]["robot_id"] == "AMR-01"
    assert response.json()["next_offset"] == 1


@pytest.mark.asyncio
async def test_task_and_kpi_history_keep_replay_fields(client: AsyncClient) -> None:
    now = datetime.now(UTC)
    await app.state.runtime_history_repository.record_task(
        TaskUpdate(
            task_id="TASK-01",
            payload_id="BP-01",
            pickup_station_id="BATTERY_BUFFER",
            dropoff_station_id="MARRIAGE_STATION",
            assigned_robot_id="AMR-01",
            status="DELIVERING",
            attempt=2,
            max_retries=3,
            message="en route",
            updated_at=datetime(1970, 1, 1, tzinfo=UTC),
        ),
        now,
    )
    await app.state.kpi_history_repository.insert(
        KpiSnapshot(
            recorded_at=now,
            simulated_elapsed_seconds=15,
            metrics=_metrics(completed_tasks=2),
        )
    )
    params = {
        "start": (now - timedelta(seconds=1)).isoformat(),
        "end": (now + timedelta(seconds=1)).isoformat(),
    }

    task_response = await client.get("/api/v1/history/tasks", params=params)
    kpi_response = await client.get("/api/v1/history/metrics", params=params)

    assert task_response.status_code == 200
    update = task_response.json()["items"][0]["update"]
    assert (update["payload_id"], update["attempt"], update["max_retries"]) == ("BP-01", 2, 3)
    assert kpi_response.status_code == 200
    assert kpi_response.json()["items"][0]["metrics"]["completed_tasks"] == 2


@pytest.mark.asyncio
async def test_history_rejects_unbounded_time_range(client: AsyncClient) -> None:
    now = datetime.now(UTC)
    response = await client.get(
        "/api/v1/history/tasks",
        params={
            "start": (now - timedelta(days=8)).isoformat(),
            "end": now.isoformat(),
        },
    )

    assert response.status_code == 422
    assert "7 days" in response.json()["detail"]
