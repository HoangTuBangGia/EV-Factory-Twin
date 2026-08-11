from fastapi import APIRouter, HTTPException

from ev_twin_api.schemas.robot import Robot
from ev_twin_api.services.factory_state import FactoryStateDep

router = APIRouter(prefix="/api/v1/robots", tags=["robots"])


@router.get("", response_model=list[Robot])
async def list_robots(factory_state: FactoryStateDep) -> list[Robot]:
    return factory_state.list_robots()


@router.get("/{robot_id}", response_model=Robot)
async def get_robot(robot_id: str, factory_state: FactoryStateDep) -> Robot:
    robot = factory_state.get_robot(robot_id)
    if robot is None:
        raise HTTPException(status_code=404, detail=f"Robot '{robot_id}' not found")
    return robot
