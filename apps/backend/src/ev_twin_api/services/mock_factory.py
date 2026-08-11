import asyncio
import contextlib
import logging
import time
from datetime import UTC, datetime

from ev_twin_api.core.routes import CHARGER_ROUTE_KEY, ROUTES
from ev_twin_api.schemas.factory import MockFactoryConfig
from ev_twin_api.schemas.robot import RobotStatus
from ev_twin_api.schemas.telemetry import robot_to_telemetry
from ev_twin_api.schemas.websocket import (
    alert_created_event,
    factory_reset_event,
    metrics_updated_event,
    robot_telemetry_event,
    task_updated_event,
)
from ev_twin_api.services.alert_service import AlertService
from ev_twin_api.services.battery_service import BatteryService, apply_battery_tick
from ev_twin_api.services.factory_state import FactoryState
from ev_twin_api.services.metrics_service import MetricsService
from ev_twin_api.services.movement import RouteProgress, advance_along_route
from ev_twin_api.services.task_service import TaskService
from ev_twin_api.services.websocket_manager import WebSocketManager

logger = logging.getLogger("ev_twin_api")


class MockFactory:
    """Background mock simulation loop, ticking FactoryState at a fixed rate.

    The loop runs at a fixed wall-clock 10 Hz (`TICK_SECONDS`).
    `config.simulation_speed` scales the simulated dt passed into `tick()`,
    not the loop frequency, so simulated time can run faster than real time
    while telemetry stays at a steady 10 Hz. `simulated_elapsed_seconds`
    accumulates dt for later throughput calculations (BE-009).

    Fixed-interval sleep is sufficient for the mock MVP; a production-quality
    loop would measure actual elapsed dt instead.
    """

    TICK_SECONDS = 0.1
    MAX_CONSECUTIVE_TICK_ERRORS = 10
    METRICS_BROADCAST_INTERVAL_SECONDS = 1.0

    def __init__(
        self,
        state: FactoryState,
        config: MockFactoryConfig,
        websocket_manager: WebSocketManager,
        *,
        enabled: bool = True,
    ) -> None:
        self._state = state
        self.config = config
        self._websocket_manager = websocket_manager
        self._enabled = enabled
        self.running = False
        self.tick_count = 0
        self.simulated_elapsed_seconds = 0.0
        self._task: asyncio.Task[None] | None = None
        self._consecutive_tick_errors = 0
        self._active_movements: dict[str, RouteProgress] = {}
        self._task_service = TaskService(state)
        self._battery_service = BatteryService(state)
        self._metrics_service = MetricsService(state)
        self._alert_service = AlertService(state)
        self._time_since_last_task = 0.0
        self._time_since_last_metrics_broadcast = 0.0

    def assign_route(self, robot_id: str, route_key: tuple[str, str]) -> None:
        if route_key not in ROUTES:
            raise ValueError(f"Unknown route: {route_key}")
        self._active_movements[robot_id] = RouteProgress(route_key=route_key)

    def clear_route(self, robot_id: str) -> None:
        self._active_movements.pop(robot_id, None)

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        if not self._enabled:
            logger.info("mock factory disabled, skipping engine start")
            return
        self.running = True
        self._task = asyncio.create_task(self.run())
        logger.info("mock factory started")

    async def stop(self) -> None:
        self.running = False
        task, self._task = self._task, None
        if task is None:
            return
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        logger.info("mock factory stopped")

    async def reset(self) -> None:
        was_running = self._task is not None and not self._task.done()
        await self.stop()
        self._state.reset()
        self._active_movements.clear()
        self._metrics_service.reset()
        self._alert_service.reset()
        self.tick_count = 0
        self.simulated_elapsed_seconds = 0.0
        self._time_since_last_task = 0.0
        self._time_since_last_metrics_broadcast = 0.0
        logger.info("mock factory reset")
        await self._websocket_manager.broadcast(factory_reset_event())
        if was_running:
            await self.start()

    async def run(self) -> None:
        while self.running:
            started = time.monotonic()
            try:
                await self.tick(self.TICK_SECONDS * self.config.simulation_speed)
            except Exception:
                # asyncio.CancelledError is a BaseException, not an Exception,
                # so cancellation from stop() still propagates past this.
                self._consecutive_tick_errors += 1
                logger.exception("mock factory tick failed")
                if self._consecutive_tick_errors >= self.MAX_CONSECUTIVE_TICK_ERRORS:
                    logger.critical(
                        "mock factory stopping after %d consecutive tick failures",
                        self._consecutive_tick_errors,
                    )
                    self.running = False
                    break
            else:
                self._consecutive_tick_errors = 0
            elapsed = time.monotonic() - started
            await asyncio.sleep(max(0.0, self.TICK_SECONDS - elapsed))

    async def tick(self, dt: float) -> None:
        self.tick_count += 1
        self.simulated_elapsed_seconds += dt

        now = datetime.now(UTC)
        for robot in self._state.list_robots():
            updated = robot.model_copy(update={"last_seen_at": now})
            new_battery = apply_battery_tick(robot.status, robot.battery, dt)
            updated = updated.model_copy(update={"battery": new_battery})
            self._state.update_robot(updated)

            if robot.status in (
                RobotStatus.MOVING_TO_PICKUP,
                RobotStatus.DELIVERING,
                RobotStatus.MOVING_TO_CHARGER,
            ):
                progress = self._active_movements.get(robot.id)
                if progress is not None:
                    previous_index = progress.waypoint_index
                    new_pose, new_velocity, route_finished = advance_along_route(
                        updated.pose, progress, self.config.robot_speed_mps, dt
                    )
                    self._state.update_robot(
                        updated.model_copy(update={"pose": new_pose, "velocity": new_velocity})
                    )
                    if (
                        robot.status == RobotStatus.MOVING_TO_PICKUP
                        and progress.waypoint_index > previous_index
                    ):
                        task = self._task_service.arrive_at_pickup(robot.id)
                        await self._websocket_manager.broadcast(task_updated_event(task))
                    elif robot.status == RobotStatus.DELIVERING and route_finished:
                        task = self._task_service.arrive_at_dropoff(robot.id)
                        await self._websocket_manager.broadcast(task_updated_event(task))
                    elif robot.status == RobotStatus.MOVING_TO_CHARGER and route_finished:
                        self._battery_service.arrive_at_charger(robot.id)
            elif robot.status == RobotStatus.PICKING:
                task = self._task_service.finish_pickup(robot.id)
                await self._websocket_manager.broadcast(task_updated_event(task))
            elif robot.status == RobotStatus.DROPPING:
                task = self._task_service.finish_dropoff(robot.id)
                await self._websocket_manager.broadcast(task_updated_event(task))
                self.clear_route(robot.id)
            elif robot.status == RobotStatus.CHARGING:
                if self._battery_service.finish_charging_if_ready(robot.id) is not None:
                    self.clear_route(robot.id)
            elif robot.status == RobotStatus.IDLE:
                charging_robot = self._battery_service.start_charging_if_needed(
                    updated, self.config.low_battery_threshold
                )
                if charging_robot is not None:
                    self.assign_route(charging_robot.id, CHARGER_ROUTE_KEY)

            latest_robot = self._state.get_robot(robot.id)
            if latest_robot is not None:
                await self._websocket_manager.broadcast(
                    robot_telemetry_event(robot_to_telemetry(latest_robot))
                )

        while True:
            assignment = self._task_service.select_assignment(self.config.low_battery_threshold)
            if assignment is None:
                break
            selected_robot, selected_task = assignment
            assigned_task = self._task_service.assign(selected_robot, selected_task)
            self.assign_route(selected_robot.id, (selected_task.pickup, selected_task.dropoff))
            await self._websocket_manager.broadcast(task_updated_event(assigned_task))

        self._time_since_last_task += dt
        while self._time_since_last_task >= self.config.task_interval_seconds:
            new_task = self._task_service.generate_task()
            await self._websocket_manager.broadcast(task_updated_event(new_task))
            self._time_since_last_task -= self.config.task_interval_seconds

        self._state.update_metrics(
            self._metrics_service.recalculate(self.simulated_elapsed_seconds)
        )

        self._time_since_last_metrics_broadcast += dt
        while self._time_since_last_metrics_broadcast >= self.METRICS_BROADCAST_INTERVAL_SECONDS:
            await self._websocket_manager.broadcast(
                metrics_updated_event(self._state.get_metrics())
            )
            self._time_since_last_metrics_broadcast -= self.METRICS_BROADCAST_INTERVAL_SECONDS

        new_alerts = self._alert_service.check(
            low_battery_threshold=self.config.low_battery_threshold,
            task_interval_seconds=self.config.task_interval_seconds,
        )
        for alert in new_alerts:
            await self._websocket_manager.broadcast(alert_created_event(alert))
