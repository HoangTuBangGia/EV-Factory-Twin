from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request

from ev_twin_api.api.dependencies import require_edge_telemetry_secret
from ev_twin_api.schemas.edge_runtime import BridgeHealth, EdgeUpdateResponse, TaskUpdate
from ev_twin_api.services.edge_runtime import EdgeRuntimeService

router = APIRouter(
    prefix="/internal/v1",
    tags=["edge"],
    dependencies=[Depends(require_edge_telemetry_secret)],
)


def get_edge_runtime_service(request: Request) -> EdgeRuntimeService:
    return cast(EdgeRuntimeService, request.app.state.edge_runtime_service)


EdgeRuntimeServiceDep = Annotated[EdgeRuntimeService, Depends(get_edge_runtime_service)]


@router.post("/task-updates", response_model=EdgeUpdateResponse)
async def ingest_task_update(
    update: TaskUpdate, service: EdgeRuntimeServiceDep
) -> EdgeUpdateResponse:
    return await service.ingest_task(update)


@router.post("/bridge-health", response_model=EdgeUpdateResponse)
async def ingest_bridge_health(
    health: BridgeHealth, service: EdgeRuntimeServiceDep
) -> EdgeUpdateResponse:
    return service.ingest_health(health)
