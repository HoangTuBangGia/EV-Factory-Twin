from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ev_twin_api.api.dependencies import require_edge_telemetry_secret
from ev_twin_api.schemas.command import (
    Command,
    CommandAcknowledgementRequest,
    CommandResultRequest,
    EdgeCommand,
)
from ev_twin_api.schemas.edge_runtime import BridgeHealth, EdgeUpdateResponse, TaskUpdate
from ev_twin_api.services.command_service import (
    CommandConflictError,
    CommandNotFoundError,
    CommandServiceDep,
)
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
    return await service.ingest_health(health)


@router.get("/commands/next", response_model=EdgeCommand | None)
async def lease_command(
    bridge_id: Annotated[str, Query(min_length=1, max_length=100)],
    service: CommandServiceDep,
) -> EdgeCommand | None:
    return await service.lease(bridge_id)


@router.post("/commands/ack", response_model=Command)
async def acknowledge_command(
    acknowledgement: CommandAcknowledgementRequest, service: CommandServiceDep
) -> Command:
    try:
        return await service.acknowledge(acknowledgement)
    except (CommandConflictError, CommandNotFoundError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/commands/result", response_model=Command)
async def report_command_result(
    result: CommandResultRequest, service: CommandServiceDep
) -> Command:
    try:
        return await service.result(result)
    except (CommandConflictError, CommandNotFoundError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
