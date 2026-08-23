import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from ev_twin_api.core.database import Database
from ev_twin_api.schemas.command import Command, CommandAttempt, CommandStatus
from ev_twin_api.schemas.scenario import ScenarioConfig
from ev_twin_api.services.command_service import SqlAlchemyCommandRepository
from sqlalchemy import text

DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="TEST_DATABASE_URL is not configured")


@pytest.mark.asyncio
async def test_unleased_command_timeout_and_retry_deadline_round_trip() -> None:
    assert DATABASE_URL is not None
    database = Database(DATABASE_URL, ssl_mode="disable")
    repository = SqlAlchemyCommandRepository(database)
    operation_id = uuid4()
    scenario_id = f"TEST-SCN-{uuid4().hex}"
    started_at = datetime.now(UTC) - timedelta(seconds=2)

    try:
        async with database.session() as session, session.begin():
            actor_id = await session.scalar(text("select id from public.profiles limit 1"))
            layout = (
                (
                    await session.execute(
                        text("""
                        select layout_id, version,
                               content->'routes'->0->>'id' as route_id
                        from public.layout_versions
                        order by created_at limit 1
                    """)
                    )
                )
                .mappings()
                .one()
            )
            assert actor_id is not None
            await session.execute(
                text("""
                    insert into public.scenarios (
                        id, name, num_robots, num_tasks, task_arrival_interval,
                        travel_time, loading_time, simulation_time, completed_tasks,
                        unfinished_tasks, completion_rate, throughput_per_hour,
                        average_cycle_time, average_waiting_time, duration_ms,
                        created_by, created_at, layout_id, layout_version, route_id,
                        robot_speed_mps, charger_count, route_distance_m,
                        congestion_multiplier, fleet_utilization_percent,
                        starvation_events, congestion_percent, travel_distance,
                        average_delivery_delay
                    ) values (
                        :id, 'command repository smoke', 2, 1, 5, 10, 2, 60,
                        0, 1, 0, 0, 0, 0, 1, :actor, :created_at,
                        :layout_id, :layout_version, :route_id, 1, 1, 10, 1,
                        0, 0, 0, 0, 0
                    )
                """),
                {
                    "id": scenario_id,
                    "actor": actor_id,
                    "created_at": started_at,
                    "layout_id": layout["layout_id"],
                    "layout_version": layout["version"],
                    "route_id": layout["route_id"],
                },
            )

        config = ScenarioConfig(
            num_robots=2,
            num_tasks=1,
            task_arrival_interval=5,
            travel_time=10,
            loading_time=2,
            simulation_time=60,
            layout_id=layout["layout_id"],
            layout_version=layout["version"],
            route_id=layout["route_id"],
            robot_speed_mps=1,
            charger_count=1,
            route_distance_m=10,
            congestion_multiplier=1,
        )
        await repository.create(
            Command(
                operation_id=operation_id,
                scenario_id=scenario_id,
                status=CommandStatus.PENDING,
                payload=config,
                timeout_seconds=1,
                max_retries=1,
                attempts=[CommandAttempt(attempt_number=1, status=CommandStatus.PENDING)],
                requested_by=actor_id,
                created_at=started_at,
                updated_at=started_at,
            )
        )

        expired = await repository.expire(datetime.now(UTC))
        assert expired[0].status == CommandStatus.TIMED_OUT

        retried_at = datetime.now(UTC)
        retried = await repository.retry(operation_id, retried_at)
        assert retried.status == CommandStatus.PENDING
        assert retried.updated_at >= retried_at
        assert not await repository.expire(retried_at + timedelta(milliseconds=500))
        assert (await repository.expire(retried_at + timedelta(seconds=2)))[0].status == (
            CommandStatus.TIMED_OUT
        )
    finally:
        async with database.session() as session, session.begin():
            await session.execute(
                text("delete from public.command_acknowledgements where operation_id=:id"),
                {"id": operation_id},
            )
            await session.execute(
                text("delete from public.command_attempts where operation_id=:id"),
                {"id": operation_id},
            )
            await session.execute(
                text("delete from public.commands where operation_id=:id"),
                {"id": operation_id},
            )
            await session.execute(
                text("delete from public.scenarios where id=:id"),
                {"id": scenario_id},
            )
        await database.dispose()
