from fastapi import APIRouter

from ev_twin_api.schemas.alert import FactoryAlert
from ev_twin_api.services.factory_state import FactoryStateDep

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


@router.get("", response_model=list[FactoryAlert])
async def list_alerts(factory_state: FactoryStateDep) -> list[FactoryAlert]:
    return factory_state.list_alerts()
