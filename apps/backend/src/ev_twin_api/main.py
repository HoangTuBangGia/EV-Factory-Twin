import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ev_twin_api import __version__
from ev_twin_api.api.admin_audit import router as admin_audit_router
from ev_twin_api.api.admin_users import router as admin_users_router
from ev_twin_api.api.alerts import router as alerts_router
from ev_twin_api.api.auth import router as auth_router
from ev_twin_api.api.factory import router as factory_router
from ev_twin_api.api.health import router as health_router
from ev_twin_api.api.metrics import router as metrics_router
from ev_twin_api.api.mock import router as mock_router
from ev_twin_api.api.robots import router as robots_router
from ev_twin_api.api.scenarios import router as scenarios_router
from ev_twin_api.api.tasks import router as tasks_router
from ev_twin_api.api.telemetry import router as telemetry_router
from ev_twin_api.api.websocket import router as websocket_router
from ev_twin_api.core.config import get_settings
from ev_twin_api.core.database import Database
from ev_twin_api.core.logging_config import configure_logging
from ev_twin_api.core.security import JwtVerifier
from ev_twin_api.schemas.factory import MockFactoryConfig
from ev_twin_api.services.admin_user_service import (
    AdminUserService,
    SqlAlchemyAdminUserRepository,
    SupabaseUserInvitationGateway,
)
from ev_twin_api.services.audit_service import (
    AuditRepository,
    AuditService,
    InMemoryAuditRepository,
    SqlAlchemyAuditRepository,
)
from ev_twin_api.services.auth_service import AuthService, SqlAlchemyProfileRepository
from ev_twin_api.services.factory_state import FactoryState
from ev_twin_api.services.kpi_snapshot_writer import build_kpi_snapshot_writer
from ev_twin_api.services.mock_factory import MockFactory
from ev_twin_api.services.scenario_repository import (
    InMemoryScenarioRepository,
    ScenarioRepository,
    SqlAlchemyScenarioRepository,
)
from ev_twin_api.services.scenario_service import ScenarioService
from ev_twin_api.services.telemetry_ingress import TelemetryIngressService
from ev_twin_api.services.websocket_manager import WebSocketManager

configure_logging()
logger = logging.getLogger("ev_twin_api")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    app.state.started_at_monotonic = time.monotonic()

    database_url = settings.database_url.get_secret_value() if settings.database_url else None
    database = Database(database_url, ssl_mode=settings.database_ssl_mode)
    issuer = settings.effective_supabase_jwt_issuer
    jwks_url = settings.effective_supabase_jwks_url
    jwt_verifier = (
        JwtVerifier(
            issuer=issuer,
            audience=settings.supabase_jwt_audience,
            jwks_url=jwks_url,
            jwks_cache_ttl_seconds=settings.supabase_jwks_cache_ttl_seconds,
            jwks_request_timeout_seconds=settings.supabase_jwks_request_timeout_seconds,
            unknown_kid_refresh_cooldown_seconds=(
                settings.supabase_jwks_unknown_kid_cooldown_seconds
            ),
            leeway_seconds=settings.supabase_jwt_leeway_seconds,
            verification_max_workers=settings.supabase_jwt_verification_max_workers,
            verification_max_in_flight=(settings.supabase_jwt_verification_max_in_flight),
        )
        if issuer and jwks_url
        else None
    )
    app.state.database = database
    app.state.auth_service = AuthService(
        verifier=jwt_verifier,
        profiles=SqlAlchemyProfileRepository(database),
    )
    if jwt_verifier is None:
        logger.warning("authentication enabled but Supabase issuer/JWKS are not configured")

    mock_config = MockFactoryConfig(
        robot_count=settings.mock_robot_count,
        task_interval_seconds=settings.mock_task_interval_seconds,
        robot_speed_mps=settings.mock_robot_speed_mps,
        simulation_speed=settings.mock_simulation_speed,
    )
    websocket_manager = WebSocketManager()
    factory_state = FactoryState(config=mock_config)
    mock_factory = MockFactory(
        state=factory_state,
        config=mock_config,
        websocket_manager=websocket_manager,
        enabled=settings.mock_factory_enabled,
    )
    app.state.factory_state = factory_state
    app.state.mock_factory = mock_factory
    app.state.telemetry_ingress_service = TelemetryIngressService(
        factory_state=factory_state,
        websocket_manager=websocket_manager,
        mock_factory=mock_factory,
    )
    audit_repository: AuditRepository
    scenario_repository: ScenarioRepository
    if database.configured:
        audit_repository = SqlAlchemyAuditRepository(database)
        scenario_repository = SqlAlchemyScenarioRepository(database)
    else:
        in_memory_audit_repository = InMemoryAuditRepository()
        audit_repository = in_memory_audit_repository
        scenario_repository = InMemoryScenarioRepository(in_memory_audit_repository)
        logger.warning(
            "DATABASE_URL is not configured; scenarios and audit events are in-memory only"
        )
    app.state.audit_service = AuditService(audit_repository)
    app.state.scenario_service = ScenarioService(mock_factory, scenario_repository)
    app.state.websocket_manager = websocket_manager
    invitation_gateway = (
        SupabaseUserInvitationGateway(
            supabase_url=settings.supabase_url,
            service_role_key=settings.supabase_service_role_key,
        )
        if settings.supabase_url is not None and settings.supabase_service_role_key is not None
        else None
    )
    app.state.admin_user_service = AdminUserService(
        repository=SqlAlchemyAdminUserRepository(database),
        invitations=invitation_gateway,
        websocket_manager=websocket_manager,
    )
    kpi_snapshot_writer = build_kpi_snapshot_writer(
        database=database,
        factory_state=factory_state,
        simulated_elapsed_seconds=lambda: mock_factory.simulated_elapsed_seconds,
    )
    app.state.kpi_snapshot_writer = kpi_snapshot_writer

    await mock_factory.start()
    if kpi_snapshot_writer is not None:
        await kpi_snapshot_writer.start()
    logger.info("backend started")
    try:
        yield
    finally:
        if kpi_snapshot_writer is not None:
            await kpi_snapshot_writer.stop()
        await mock_factory.stop()
        if jwt_verifier is not None:
            jwt_verifier.close()
        await database.dispose()
        logger.info("backend stopped")


app = FastAPI(
    title="EV Factory Digital Twin API",
    version=__version__,
    description="Application API for AMR battery intralogistics telemetry and scenarios.",
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
app.include_router(auth_router)
app.include_router(admin_audit_router)
app.include_router(admin_users_router)
app.include_router(factory_router)
app.include_router(robots_router)
app.include_router(tasks_router)
app.include_router(metrics_router)
app.include_router(alerts_router)
app.include_router(mock_router)
app.include_router(scenarios_router)
app.include_router(telemetry_router)
app.include_router(websocket_router)
