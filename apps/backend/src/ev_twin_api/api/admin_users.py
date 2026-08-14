import logging
from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ev_twin_api.api.dependencies import CurrentUserDep, require_roles
from ev_twin_api.schemas.admin import AdminInviteRequest, AdminUser, AdminUserUpdate
from ev_twin_api.schemas.auth import AppRole
from ev_twin_api.services.admin_user_service import (
    AdminUserConflictError,
    AdminUserNotFoundError,
    AdminUserService,
    LastActiveAdminError,
    UserAdministrationUnavailableError,
)

logger = logging.getLogger("ev_twin_api")

router = APIRouter(
    prefix="/api/v1/admin/users",
    tags=["admin", "users"],
    dependencies=[Depends(require_roles(AppRole.ADMIN))],
)


def get_admin_user_service(request: Request) -> AdminUserService:
    return cast(AdminUserService, request.app.state.admin_user_service)


AdminUserServiceDep = Annotated[AdminUserService, Depends(get_admin_user_service)]


def _translate_admin_error(error: Exception) -> HTTPException:
    if isinstance(error, AdminUserNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if isinstance(error, (LastActiveAdminError, AdminUserConflictError)):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    logger.warning("user administration unavailable: %s", type(error).__name__)
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="User administration is unavailable",
    )


@router.get("", response_model=list[AdminUser])
async def list_admin_users(service: AdminUserServiceDep) -> list[AdminUser]:
    try:
        return await service.list()
    except UserAdministrationUnavailableError as error:
        raise _translate_admin_error(error) from error


@router.patch("/{user_id}", response_model=AdminUser)
async def update_admin_user(
    user_id: UUID,
    update: AdminUserUpdate,
    service: AdminUserServiceDep,
    current_user: CurrentUserDep,
) -> AdminUser:
    try:
        return await service.update(user_id, update, actor=current_user)
    except (
        AdminUserNotFoundError,
        LastActiveAdminError,
        UserAdministrationUnavailableError,
    ) as error:
        raise _translate_admin_error(error) from error


@router.post("/invite", response_model=AdminUser, status_code=status.HTTP_201_CREATED)
async def invite_admin_user(
    invite: AdminInviteRequest,
    service: AdminUserServiceDep,
    current_user: CurrentUserDep,
) -> AdminUser:
    try:
        return await service.invite(invite, actor=current_user)
    except (AdminUserConflictError, UserAdministrationUnavailableError) as error:
        raise _translate_admin_error(error) from error
