from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from ev_twin_api.api.dependencies import READ_ROLES, require_roles
from ev_twin_api.schemas.auth import AppRole
from ev_twin_api.schemas.command import Command
from ev_twin_api.services.command_service import (
    CommandConflictError,
    CommandNotFoundError,
    CommandServiceDep,
)

router = APIRouter(prefix="/api/v1/commands", tags=["commands"])


def _translate(error: Exception) -> HTTPException:
    if isinstance(error, CommandNotFoundError):
        return HTTPException(status_code=404, detail=str(error))
    return HTTPException(status_code=409, detail=str(error))


@router.get("", response_model=list[Command], dependencies=[Depends(require_roles(*READ_ROLES))])
async def list_commands(service: CommandServiceDep) -> list[Command]:
    return await service.list()


@router.get(
    "/{operation_id}", response_model=Command, dependencies=[Depends(require_roles(*READ_ROLES))]
)
async def get_command(operation_id: UUID, service: CommandServiceDep) -> Command:
    try:
        return await service.get(operation_id)
    except CommandNotFoundError as error:
        raise _translate(error) from error


@router.post(
    "/{operation_id}/retry",
    response_model=Command,
    dependencies=[Depends(require_roles(AppRole.MONITOR))],
)
async def retry_command(operation_id: UUID, service: CommandServiceDep) -> Command:
    try:
        return await service.retry(operation_id)
    except (CommandNotFoundError, CommandConflictError) as error:
        raise _translate(error) from error
