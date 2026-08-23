import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from ev_twin_api.core.database import Database
from ev_twin_api.schemas.alert import AlertCode, AlertSeverity, FactoryAlert
from ev_twin_api.schemas.edge_runtime import BridgeHealth, TaskUpdate
from ev_twin_api.schemas.telemetry import RobotTelemetry, TelemetryIngressStatus
from ev_twin_api.services.runtime_history import SqlAlchemyRuntimeHistoryRepository
from sqlalchemy import text

DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="TEST_DATABASE_URL is not configured")


@pytest.mark.asyncio
async def test_runtime_history_repository_round_trip() -> None:
    assert DATABASE_URL is not None
    database = Database(DATABASE_URL, ssl_mode="disable")
    repository = SqlAlchemyRuntimeHistoryRepository(database)
    suffix = uuid4().hex
    robot_id = f"TEST-AMR-{suffix}"
    bridge_id = f"test-edge-{suffix}"
    task_id = f"TEST-TASK-{suffix}"
    dedupe_key = f"STALE_TELEMETRY:{robot_id}"
    now = datetime.now(UTC)
    telemetry = RobotTelemetry.model_validate(
        {
            "timestamp": now,
            "robot_id": robot_id,
            "pose": {"x": 1, "y": 2, "yaw": 0},
            "velocity": {"linear": 0.5, "angular": 0},
            "battery": 42,
            "status": "MOVING",
            "task_id": None,
            "payload_id": None,
        }
    )
    alert = FactoryAlert(
        id=uuid4(),
        dedupe_key=dedupe_key,
        severity=AlertSeverity.WARNING,
        code=AlertCode.STALE_TELEMETRY,
        message=f"{robot_id} stale",
        robot_id=robot_id,
        timestamp=now,
    )

    try:
        await repository.record_telemetry(telemetry, now, TelemetryIngressStatus.ACCEPTED)
        await repository.record_telemetry(
            telemetry.model_copy(update={"timestamp": now - timedelta(seconds=1)}),
            now,
            TelemetryIngressStatus.IGNORED_STALE,
        )
        await repository.record_bridge_health(
            BridgeHealth(
                bridge_id=bridge_id,
                status="CONNECTED",
                robot_ids=[robot_id],
                timestamp=now,
                delivered_samples=2,
                failed_deliveries=0,
            ),
            now,
        )
        await repository.record_task(
            TaskUpdate(
                task_id=task_id,
                payload_id=f"TEST-PAYLOAD-{suffix}",
                pickup_station_id="BATTERY_BUFFER",
                dropoff_station_id="MARRIAGE_STATION",
                assigned_robot_id=robot_id,
                status="ASSIGNED",
                attempt=1,
                max_retries=1,
                updated_at=now,
            ),
            now,
        )
        assert await repository.activate_alert(alert)
        assert not await repository.activate_alert(
            alert.model_copy(update={"id": uuid4(), "last_seen_at": now + timedelta(seconds=1)})
        )
        cleared = await repository.clear_alert(dedupe_key, now + timedelta(seconds=2))
        assert cleared is not None
        assert cleared.status == "CLEARED"
        assert await repository.activate_alert(
            alert.model_copy(
                update={
                    "id": uuid4(),
                    "timestamp": now + timedelta(seconds=3),
                    "last_seen_at": now + timedelta(seconds=3),
                }
            )
        )

        async with database.session() as session:
            telemetry_rows = await session.scalar(
                text("select count(*) from public.robot_telemetry_history where robot_id=:id"),
                {"id": robot_id},
            )
            ordering = list(
                (
                    await session.execute(
                        text("""
                            select ordering_status from public.robot_telemetry_history
                            where robot_id=:id order by source_timestamp desc
                        """),
                        {"id": robot_id},
                    )
                ).scalars()
            )
        assert telemetry_rows == 2
        assert ordering == ["ACCEPTED", "LATE"]
        matching_alerts = [
            item.status for item in await repository.list_alerts() if item.robot_id == robot_id
        ]
        assert matching_alerts == [
            "ACTIVE",
            "CLEARED",
        ]
    finally:
        async with database.session() as session, session.begin():
            await session.execute(
                text("delete from public.alerts where dedupe_key=:key"), {"key": dedupe_key}
            )
            await session.execute(
                text("delete from public.task_state_history where task_id=:id"), {"id": task_id}
            )
            await session.execute(
                text("delete from public.bridge_health_history where bridge_id=:id"),
                {"id": bridge_id},
            )
            await session.execute(
                text("delete from public.robot_telemetry_history where robot_id=:id"),
                {"id": robot_id},
            )
        await database.dispose()
