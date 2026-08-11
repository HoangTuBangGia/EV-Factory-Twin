import asyncio
import contextlib
import logging
import time
from datetime import UTC, datetime

from ev_twin_api.core.routes import ROUTES
from ev_twin_api.schemas.factory import MockFactoryConfig
from ev_twin_api.services.factory_state import FactoryState
from ev_twin_api.services.movement import RouteProgress, advance_along_route
from ev_twin_api.services.task_service import TaskService

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

    def __init__(
        self, state: FactoryState, config: MockFactoryConfig, *, enabled: bool = True
    ) -> None:
        self._state = state
        self.config = config
        self._enabled = enabled
        self.running = False
        self.tick_count = 0
        self.simulated_elapsed_seconds = 0.0
        self._task: asyncio.Task[None] | None = None
        self._consecutive_tick_errors = 0
        self._active_movements: dict[str, RouteProgress] = {}
        self._task_service = TaskService(state)
        self._time_since_last_task = 0.0

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
        self.tick_count = 0
        self.simulated_elapsed_seconds = 0.0
        self._time_since_last_task = 0.0
        logger.info("mock factory reset")
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
        finished_robot_ids: list[str] = []
        for robot in self._state.list_robots():
            updated = robot.model_copy(update={"last_seen_at": now})

            progress = self._active_movements.get(robot.id)
            if progress is not None:
                new_pose, new_velocity, route_finished = advance_along_route(
                    updated.pose, progress, self.config.robot_speed_mps, dt
                )
                updated = updated.model_copy(update={"pose": new_pose, "velocity": new_velocity})
                if route_finished:
                    finished_robot_ids.append(robot.id)

            self._state.update_robot(updated)

        for robot_id in finished_robot_ids:
            self._active_movements.pop(robot_id, None)

        self._time_since_last_task += dt
        while self._time_since_last_task >= self.config.task_interval_seconds:
            self._task_service.generate_task()
            self._time_since_last_task -= self.config.task_interval_seconds

        # BE-006b: task assignment
        # BE-007: battery drain & charging
        # BE-009: metrics recalculation
        # BE-010: alert generation
