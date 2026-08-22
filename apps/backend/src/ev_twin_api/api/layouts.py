from collections.abc import Awaitable

from fastapi import APIRouter, Depends, HTTPException, Response, status

from ev_twin_api.api.dependencies import READ_ROLES, CurrentUserDep, require_roles
from ev_twin_api.schemas.auth import AppRole
from ev_twin_api.schemas.layout import (
    CreateLayoutRequest,
    CreateLayoutVersionRequest,
    LayoutSummary,
    LayoutVersion,
    UpdateLayoutRequest,
)
from ev_twin_api.services.layout_service import (
    LayoutConflictError,
    LayoutNotFoundError,
    LayoutServiceDep,
)

router = APIRouter(prefix="/api/v1/layouts", tags=["layouts"])


async def _layout_action[ResultT](action: Awaitable[ResultT]) -> ResultT:
    try:
        return await action
    except LayoutNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except LayoutConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get(
    "",
    response_model=list[LayoutSummary],
    dependencies=[Depends(require_roles(*READ_ROLES))],
)
async def list_layouts(service: LayoutServiceDep) -> list[LayoutSummary]:
    return await service.list()


@router.post(
    "",
    response_model=LayoutVersion,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(AppRole.DESIGNER))],
)
async def create_layout(
    request: CreateLayoutRequest, service: LayoutServiceDep, actor: CurrentUserDep
) -> LayoutVersion:
    return await service.create(request, actor)


@router.get(
    "/{layout_id}",
    response_model=LayoutVersion,
    dependencies=[Depends(require_roles(*READ_ROLES))],
)
async def get_layout(layout_id: str, service: LayoutServiceDep) -> LayoutVersion:
    return await _layout_action(service.get(layout_id))


@router.patch(
    "/{layout_id}",
    response_model=LayoutVersion,
    dependencies=[Depends(require_roles(AppRole.DESIGNER))],
)
async def update_layout(
    layout_id: str,
    request: UpdateLayoutRequest,
    service: LayoutServiceDep,
    actor: CurrentUserDep,
) -> LayoutVersion:
    return await _layout_action(service.update(layout_id, request, actor))


@router.delete(
    "/{layout_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(AppRole.DESIGNER))],
)
async def archive_layout(
    layout_id: str, service: LayoutServiceDep, actor: CurrentUserDep
) -> Response:
    await _layout_action(service.archive(layout_id, actor))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{layout_id}/versions",
    response_model=LayoutVersion,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(AppRole.DESIGNER))],
)
async def create_layout_version(
    layout_id: str,
    request: CreateLayoutVersionRequest,
    service: LayoutServiceDep,
    actor: CurrentUserDep,
) -> LayoutVersion:
    return await _layout_action(service.create_version(layout_id, request, actor))


@router.get(
    "/{layout_id}/versions/{version}",
    response_model=LayoutVersion,
    dependencies=[Depends(require_roles(*READ_ROLES))],
)
async def get_layout_version(
    layout_id: str, version: int, service: LayoutServiceDep
) -> LayoutVersion:
    return await _layout_action(service.get(layout_id, version))
