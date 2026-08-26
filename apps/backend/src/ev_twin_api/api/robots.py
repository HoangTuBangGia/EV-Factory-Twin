from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from ev_twin_api.api.dependencies import READ_ROLES, require_roles
from ev_twin_api.schemas.history import HistoryQuery, TelemetryHistoryEntry
from ev_twin_api.schemas.robot import Robot
from ev_twin_api.services.factory_state import FactoryStateDep
from ev_twin_api.services.runtime_history import RuntimeHistoryRepositoryDep

router = APIRouter(
    prefix="/api/v1/robots",
    tags=["robots"],
    dependencies=[Depends(require_roles(*READ_ROLES))],
)


@router.get("", response_model=list[Robot])
async def list_robots(factory_state: FactoryStateDep) -> list[Robot]:
    return factory_state.list_robots()


@router.get("/{robot_id}/telemetry-history", response_model=list[TelemetryHistoryEntry])
async def get_robot_telemetry_history(
    robot_id: str,
    query: Annotated[HistoryQuery, Query()],
    repository: RuntimeHistoryRepositoryDep,
) -> list[TelemetryHistoryEntry]:
    return await repository.list_telemetry(
        robot_id=robot_id,
        start=query.start,
        end=query.end,
        before=query.before,
        limit=query.limit,
    )


@router.get("/{robot_id}", response_model=Robot)
async def get_robot(robot_id: str, factory_state: FactoryStateDep) -> Robot:
    robot = factory_state.get_robot(robot_id)
    if robot is None:
        raise HTTPException(status_code=404, detail=f"Robot '{robot_id}' not found")
    return robot
