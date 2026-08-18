from fastapi import APIRouter, Depends

from ev_twin_api.api.dependencies import READ_ROLES, require_roles
from ev_twin_api.schemas.factory import FactoryLayout
from ev_twin_api.services.factory_state import FactoryStateDep

router = APIRouter(
    prefix="/api/v1/factory",
    tags=["factory"],
    dependencies=[Depends(require_roles(*READ_ROLES))],
)


@router.get("", response_model=FactoryLayout)
async def get_factory(factory_state: FactoryStateDep) -> FactoryLayout:
    return factory_state.get_layout()
