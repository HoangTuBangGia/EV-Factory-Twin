from fastapi import APIRouter, Depends

from ev_twin_api.api.dependencies import READ_ROLES, require_roles
from ev_twin_api.schemas.metrics import FactoryMetrics
from ev_twin_api.services.factory_state import FactoryStateDep

router = APIRouter(
    prefix="/api/v1/metrics",
    tags=["metrics"],
    dependencies=[Depends(require_roles(*READ_ROLES))],
)


@router.get("", response_model=FactoryMetrics)
async def get_metrics(factory_state: FactoryStateDep) -> FactoryMetrics:
    return factory_state.get_metrics()
