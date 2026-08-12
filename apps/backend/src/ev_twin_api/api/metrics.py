from fastapi import APIRouter

from ev_twin_api.schemas.metrics import FactoryMetrics
from ev_twin_api.services.factory_state import FactoryStateDep

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


@router.get("", response_model=FactoryMetrics)
async def get_metrics(factory_state: FactoryStateDep) -> FactoryMetrics:
    return factory_state.get_metrics()
