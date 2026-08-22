from fastapi import APIRouter, Depends

from ev_twin_api.api.dependencies import READ_ROLES, require_roles
from ev_twin_api.schemas.alert import FactoryAlert
from ev_twin_api.services.runtime_health import RuntimeHealthServiceDep

router = APIRouter(
    prefix="/api/v1/alerts",
    tags=["alerts"],
    dependencies=[Depends(require_roles(*READ_ROLES))],
)


@router.get("", response_model=list[FactoryAlert])
async def list_alerts(service: RuntimeHealthServiceDep) -> list[FactoryAlert]:
    return await service.list_alerts()
