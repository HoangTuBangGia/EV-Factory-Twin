import asyncio
import contextlib
import math
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated, cast
from uuid import UUID, uuid4

from fastapi import Depends, Request

from ev_twin_api.schemas.alert import AlertCode, AlertSeverity, FactoryAlert
from ev_twin_api.schemas.edge_runtime import BridgeHealth, BridgeStatus
from ev_twin_api.schemas.robot import RobotStatus
from ev_twin_api.schemas.telemetry import RobotTelemetry
from ev_twin_api.schemas.websocket import alert_created_event
from ev_twin_api.services.factory_state import FactoryState
from ev_twin_api.services.runtime_history import RuntimeHistoryRepository
from ev_twin_api.services.websocket_manager import WebSocketManager

SEVERITY_BY_CODE = {
    AlertCode.LOW_BATTERY: AlertSeverity.WARNING,
    AlertCode.ROBOT_ERROR: AlertSeverity.CRITICAL,
    AlertCode.STALE_TELEMETRY: AlertSeverity.WARNING,
    AlertCode.BRIDGE_DISCONNECTED: AlertSeverity.CRITICAL,
    AlertCode.COMMAND_TIMEOUT: AlertSeverity.CRITICAL,
    AlertCode.CONGESTION: AlertSeverity.WARNING,
}
MOVING_STATUSES = {
    RobotStatus.MOVING,
    RobotStatus.PICKING,
    RobotStatus.DELIVERING,
}


class RuntimeHealthService:
    def __init__(
        self,
        state: FactoryState,
        repository: RuntimeHistoryRepository,
        websockets: WebSocketManager,
        *,
        stale_telemetry_seconds: float,
        bridge_disconnect_seconds: float,
        congestion_distance_meters: float,
        low_battery_percent: float,
        sweep_seconds: float,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._state = state
        self._repository = repository
        self._websockets = websockets
        self._stale_after = timedelta(seconds=stale_telemetry_seconds)
        self._bridge_stale_after = timedelta(seconds=bridge_disconnect_seconds)
        self._congestion_distance = congestion_distance_meters
        self._low_battery = low_battery_percent
        self._sweep_seconds = sweep_seconds
        self._clock = clock or (lambda: datetime.now(UTC))
        self._telemetry_seen: dict[str, datetime] = {}
        self._bridge_seen: dict[str, tuple[BridgeHealth, datetime]] = {}
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run(), name="runtime-health-sweep")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def note_telemetry(self, telemetry: RobotTelemetry, ingested_at: datetime) -> None:
        self._telemetry_seen[telemetry.robot_id] = ingested_at
        await self._condition(
            f"LOW_BATTERY:{telemetry.robot_id}",
            telemetry.battery <= self._low_battery,
            AlertCode.LOW_BATTERY,
            f"{telemetry.robot_id} battery low ({telemetry.battery:.1f}%)",
            robot_id=telemetry.robot_id,
        )
        await self._condition(
            f"ROBOT_ERROR:{telemetry.robot_id}",
            telemetry.status == RobotStatus.ERROR,
            AlertCode.ROBOT_ERROR,
            f"{telemetry.robot_id} entered ERROR state",
            robot_id=telemetry.robot_id,
        )
        await self._condition(
            f"STALE_TELEMETRY:{telemetry.robot_id}",
            False,
            AlertCode.STALE_TELEMETRY,
            f"{telemetry.robot_id} telemetry recovered",
            robot_id=telemetry.robot_id,
        )
        await self._check_congestion()

    async def note_bridge_health(
        self, health: BridgeHealth, received_at: datetime | None = None
    ) -> None:
        self._bridge_seen[health.bridge_id] = (health, received_at or self._clock())
        await self._condition(
            f"BRIDGE_DISCONNECTED:{health.bridge_id}",
            health.status == BridgeStatus.DEGRADED,
            AlertCode.BRIDGE_DISCONNECTED,
            health.last_error or f"{health.bridge_id} reported DEGRADED",
        )

    async def note_command_timeout(self, operation_id: UUID, active: bool) -> None:
        await self._condition(
            f"COMMAND_TIMEOUT:{operation_id}",
            active,
            AlertCode.COMMAND_TIMEOUT,
            f"Command {operation_id} timed out",
            operation_id=operation_id,
        )

    async def record_existing(self, alert: FactoryAlert) -> None:
        await self._repository.activate_alert(alert)

    async def clear_existing(self, dedupe_key: str) -> None:
        await self._repository.clear_alert(dedupe_key, self._clock())

    async def sweep(self) -> None:
        now = self._clock()
        for robot_id, received_at in self._telemetry_seen.items():
            await self._condition(
                f"STALE_TELEMETRY:{robot_id}",
                now - received_at > self._stale_after,
                AlertCode.STALE_TELEMETRY,
                f"{robot_id} telemetry stale for {(now - received_at).total_seconds():.0f}s",
                robot_id=robot_id,
            )
        for bridge_id, (health, received_at) in self._bridge_seen.items():
            disconnected = now - received_at > self._bridge_stale_after
            await self._condition(
                f"BRIDGE_DISCONNECTED:{bridge_id}",
                disconnected or health.status == BridgeStatus.DEGRADED,
                AlertCode.BRIDGE_DISCONNECTED,
                health.last_error
                or f"{bridge_id} health stale for {(now - received_at).total_seconds():.0f}s",
            )

    async def list_alerts(self) -> list[FactoryAlert]:
        return await self._repository.list_alerts()

    async def _check_congestion(self) -> None:
        moving = [
            robot
            for robot_id in self._telemetry_seen
            if (robot := self._state.get_robot(robot_id)) is not None
            and robot.status in MOVING_STATUSES
        ]
        closest: tuple[str, str, float] | None = None
        for index, first in enumerate(moving):
            for second in moving[index + 1 :]:
                distance = math.hypot(first.pose.x - second.pose.x, first.pose.y - second.pose.y)
                if distance <= self._congestion_distance and (
                    closest is None or distance < closest[2]
                ):
                    closest = (first.id, second.id, distance)
        # ponytail: proximity is the MVP ceiling; replace with active-layout zone
        # occupancy when runtime layout binding is introduced.
        await self._condition(
            "CONGESTION:FLEET",
            closest is not None,
            AlertCode.CONGESTION,
            (
                f"{closest[0]} and {closest[1]} are {closest[2]:.2f}m apart while moving"
                if closest
                else "Fleet congestion cleared"
            ),
        )

    async def _condition(
        self,
        dedupe_key: str,
        active: bool,
        code: AlertCode,
        message: str,
        *,
        robot_id: str | None = None,
        task_id: str | None = None,
        operation_id: UUID | None = None,
    ) -> None:
        now = self._clock()
        if not active:
            await self._repository.clear_alert(dedupe_key, now)
            return
        alert = FactoryAlert(
            id=uuid4(),
            dedupe_key=dedupe_key,
            severity=SEVERITY_BY_CODE[code],
            code=code,
            message=message,
            robot_id=robot_id,
            task_id=task_id,
            operation_id=operation_id,
            timestamp=now,
            last_seen_at=now,
        )
        if await self._repository.activate_alert(alert):
            self._state.add_alert(alert)
            await self._websockets.broadcast(alert_created_event(alert))

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self._sweep_seconds)
            await self.sweep()


def get_runtime_health_service(request: Request) -> RuntimeHealthService:
    return cast(RuntimeHealthService, request.app.state.runtime_health_service)


RuntimeHealthServiceDep = Annotated[RuntimeHealthService, Depends(get_runtime_health_service)]
