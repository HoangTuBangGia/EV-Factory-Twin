from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from ev_twin_api.api.dependencies import READ_ROLES, CurrentUserDep, require_roles
from ev_twin_api.schemas.alert import FactoryAlert
from ev_twin_api.schemas.auth import AppRole
from ev_twin_api.services.runtime_health import AlertNotFoundError, RuntimeHealthServiceDep

router = APIRouter(
    prefix="/api/v1/alerts",
    tags=["alerts"],
    dependencies=[Depends(require_roles(*READ_ROLES))],
)


@router.get("", response_model=list[FactoryAlert])
async def list_alerts(service: RuntimeHealthServiceDep) -> list[FactoryAlert]:
    return await service.list_alerts()


@router.post(
    "/{alert_id}/acknowledge",
    response_model=FactoryAlert,
    dependencies=[Depends(require_roles(AppRole.MONITOR))],
)
async def acknowledge_alert(
    alert_id: UUID,
    service: RuntimeHealthServiceDep,
    current_user: CurrentUserDep,
) -> FactoryAlert:
    try:
        return await service.acknowledge_alert(alert_id, current_user.id)
    except AlertNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
