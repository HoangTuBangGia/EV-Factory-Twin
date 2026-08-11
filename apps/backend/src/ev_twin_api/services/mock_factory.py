import asyncio
import contextlib
import logging
import time
from datetime import UTC, datetime

from ev_twin_api.schemas.factory import MockFactoryConfig
from ev_twin_api.services.factory_state import FactoryState

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
        self.tick_count = 0
        self.simulated_elapsed_seconds = 0.0
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
        for robot in self._state.list_robots():
            self._state.update_robot(robot.model_copy(update={"last_seen_at": now}))

        # BE-005b: waypoint movement
        # BE-006: task generation & assignment
        # BE-007: battery drain & charging
        # BE-009: metrics recalculation
        # BE-010: alert generation
