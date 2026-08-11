import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ev_twin_api import __version__
from ev_twin_api.api.health import router as health_router
from ev_twin_api.core.config import get_settings
from ev_twin_api.core.logging_config import configure_logging
from ev_twin_api.schemas.factory import MockFactoryConfig
from ev_twin_api.services.factory_state import FactoryState
from ev_twin_api.services.mock_factory import MockFactory

configure_logging()
logger = logging.getLogger("ev_twin_api")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.started_at_monotonic = time.monotonic()

    mock_config = MockFactoryConfig(
        robot_count=settings.mock_robot_count,
        task_interval_seconds=settings.mock_task_interval_seconds,
        robot_speed_mps=settings.mock_robot_speed_mps,
        simulation_speed=settings.mock_simulation_speed,
    )
    factory_state = FactoryState(config=mock_config)
    mock_factory = MockFactory(
        state=factory_state, config=mock_config, enabled=settings.mock_factory_enabled
    )
    app.state.factory_state = factory_state
    app.state.mock_factory = mock_factory

    await mock_factory.start()
    logger.info("backend started")
    yield
    await mock_factory.stop()
    logger.info("backend stopped")


app = FastAPI(
    title="EV Factory Digital Twin API",
    version=__version__,
    description="Mock-data backend mô phỏng đội AMR chở pin trong nhà máy, đẩy telemetry realtime.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
