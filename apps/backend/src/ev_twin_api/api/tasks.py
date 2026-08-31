from fastapi import APIRouter, Depends, HTTPException

from ev_twin_api.api.dependencies import READ_ROLES, CurrentUserDep, require_roles
from ev_twin_api.schemas.auth import AppRole
from ev_twin_api.schemas.command import Command
from ev_twin_api.schemas.task import CreateTransportTaskRequest, Task
from ev_twin_api.services.command_service import CommandConflictError, CommandServiceDep
from ev_twin_api.services.factory_state import FactoryStateDep

router = APIRouter(
    prefix="/api/v1/tasks",
    tags=["tasks"],
    dependencies=[Depends(require_roles(*READ_ROLES))],
)


@router.get("", response_model=list[Task])
async def list_tasks(factory_state: FactoryStateDep) -> list[Task]:
    return factory_state.list_tasks()


@router.post(
    "",
    response_model=Command,
    status_code=202,
    dependencies=[Depends(require_roles(AppRole.MONITOR))],
)
async def create_task(
    request: CreateTransportTaskRequest,
    command_service: CommandServiceDep,
    current_user: CurrentUserDep,
) -> Command:
    try:
        return await command_service.create_transport_task(request, current_user)
    except CommandConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/{task_id}", response_model=Task)
async def get_task(task_id: str, factory_state: FactoryStateDep) -> Task:
    task = factory_state.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return task
