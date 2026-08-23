import asyncio
import contextlib
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated, cast
from uuid import UUID, uuid4

from fastapi import Depends, Request
from twin_core.models.layout import LayoutVersion, Point, point_in_polygon

from ev_twin_api.schemas.alert import AlertCode, AlertSeverity, FactoryAlert
from ev_twin_api.schemas.edge_runtime import BridgeHealth, BridgeStatus
from ev_twin_api.schemas.robot import RobotStatus
from ev_twin_api.schemas.telemetry import RobotTelemetry
from ev_twin_api.schemas.websocket import alert_created_event, alert_updated_event
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


class RuntimeHealthService:
    def __init__(
        self,
        state: FactoryState,
        repository: RuntimeHistoryRepository,
        websockets: WebSocketManager,
        *,
        stale_telemetry_seconds: float,
        bridge_disconnect_seconds: float,
        low_battery_percent: float,
        sweep_seconds: float,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._state = state
        self._repository = repository
        self._websockets = websockets
        self._stale_after = timedelta(seconds=stale_telemetry_seconds)
        self._bridge_stale_after = timedelta(seconds=bridge_disconnect_seconds)
        self._low_battery = low_battery_percent
        self._sweep_seconds = sweep_seconds
        self._clock = clock or (lambda: datetime.now(UTC))
        self._telemetry_seen: dict[str, datetime] = {}
        self._bridge_seen: dict[str, tuple[BridgeHealth, datetime]] = {}
        self._applied_layout: LayoutVersion | None = None
        self._congestion_keys: set[str] = set()
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

    def set_applied_layout(self, layout: LayoutVersion | None) -> None:
        self._applied_layout = layout.model_copy(deep=True) if layout is not None else None
        self._telemetry_seen.clear()

    async def record_existing(self, alert: FactoryAlert) -> None:
        await self._repository.activate_alert(alert)

    async def clear_existing(self, dedupe_key: str) -> None:
        await self._clear(dedupe_key, self._clock())

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
        await self._check_congestion()

    async def list_alerts(self) -> list[FactoryAlert]:
        return await self._repository.list_alerts()

    async def _check_congestion(self) -> None:
        robots = [
            robot
            for robot_id in self._telemetry_seen
            if (robot := self._state.get_robot(robot_id)) is not None
            and robot.status != RobotStatus.OFFLINE
        ]
        current_keys: set[str] = set()
        layout = self._applied_layout
        if layout is not None:
            for zone in layout.congestion_zones:
                occupants = [
                    robot.id
                    for robot in robots
                    if point_in_polygon(Point(x=robot.pose.x, y=robot.pose.y), zone.points)
                ]
                key = f"CONGESTION:{layout.layout_id}:{layout.version}:{zone.id}"
                if len(occupants) >= 2:
                    current_keys.add(key)
                    await self._condition(
                        key,
                        True,
                        AlertCode.CONGESTION,
                        f"{zone.id} occupied by {len(occupants)} robots: {', '.join(occupants)}",
                    )
        for key in self._congestion_keys - current_keys:
            await self._condition(key, False, AlertCode.CONGESTION, "Congestion cleared")
        self._congestion_keys = current_keys

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
            await self._clear(dedupe_key, now)
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

    async def _clear(self, dedupe_key: str, cleared_at: datetime) -> None:
        cleared = await self._repository.clear_alert(dedupe_key, cleared_at)
        if cleared is not None:
            await self._websockets.broadcast(alert_updated_event(cleared))

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self._sweep_seconds)
            await self.sweep()


def get_runtime_health_service(request: Request) -> RuntimeHealthService:
    return cast(RuntimeHealthService, request.app.state.runtime_health_service)


RuntimeHealthServiceDep = Annotated[RuntimeHealthService, Depends(get_runtime_health_service)]
