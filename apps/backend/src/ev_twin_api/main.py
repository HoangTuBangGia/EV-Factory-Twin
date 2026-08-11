import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ev_twin_api import __version__
from ev_twin_api.api.health import router as health_router
from ev_twin_api.core.config import get_settings
from ev_twin_api.core.logging_config import configure_logging

configure_logging()
logger = logging.getLogger("ev_twin_api")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Mock engine startup/shutdown hooks in vào đây (BE-005).
    logger.info("backend started")
    yield
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
