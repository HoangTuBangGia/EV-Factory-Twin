from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Request

from ev_twin_api.api.dependencies import CurrentUserDep, require_roles
from ev_twin_api.schemas.auth import AppRole
from ev_twin_api.schemas.optimization import OptimizationRequest, OptimizationResult
from ev_twin_api.services.optimization_service import OptimizationService
from ev_twin_api.services.scenario_service import InvalidScenarioConfigurationError

router = APIRouter(prefix="/api/v1/optimizations", tags=["optimizations"])


def get_optimization_service(request: Request) -> OptimizationService:
    return cast(OptimizationService, request.app.state.optimization_service)


OptimizationServiceDep = Annotated[OptimizationService, Depends(get_optimization_service)]


@router.post(
    "/run",
    response_model=OptimizationResult,
    dependencies=[Depends(require_roles(AppRole.DESIGNER))],
)
async def run_optimization(
    request: OptimizationRequest,
    service: OptimizationServiceDep,
    current_user: CurrentUserDep,
) -> OptimizationResult:
    try:
        return await service.run(request, current_user)
    except InvalidScenarioConfigurationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
