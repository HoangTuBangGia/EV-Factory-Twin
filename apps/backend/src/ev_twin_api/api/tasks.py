from fastapi import APIRouter, HTTPException

from ev_twin_api.schemas.task import Task
from ev_twin_api.services.factory_state import FactoryStateDep

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


@router.get("", response_model=list[Task])
async def list_tasks(factory_state: FactoryStateDep) -> list[Task]:
    return factory_state.list_tasks()


@router.get("/{task_id}", response_model=Task)
async def get_task(task_id: str, factory_state: FactoryStateDep) -> Task:
    task = factory_state.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return task
