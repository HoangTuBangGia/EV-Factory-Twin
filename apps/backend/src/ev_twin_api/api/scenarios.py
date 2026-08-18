from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Depends, HTTPException

from ev_twin_api.api.dependencies import READ_ROLES, CurrentUserDep, require_roles
from ev_twin_api.schemas.auth import AppRole
from ev_twin_api.schemas.scenario import Scenario, ScenarioRunRequest
from ev_twin_api.services.scenario_service import (
    InvalidScenarioTransitionError,
    ScenarioNotFoundError,
    ScenarioServiceDep,
)

router = APIRouter(prefix="/api/v1/scenarios", tags=["scenarios"])


async def _scenario_action(action: Callable[[], Awaitable[Scenario]]) -> Scenario:
    try:
        return await action()
    except ScenarioNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except InvalidScenarioTransitionError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post(
    "/run",
    response_model=Scenario,
    dependencies=[Depends(require_roles(AppRole.DESIGNER))],
)
async def run_scenario(
    request: ScenarioRunRequest,
    scenario_service: ScenarioServiceDep,
    current_user: CurrentUserDep,
) -> Scenario:
    return await scenario_service.run(request, current_user)


@router.get(
    "/baseline",
    response_model=Scenario,
    dependencies=[Depends(require_roles(*READ_ROLES))],
)
async def get_baseline(scenario_service: ScenarioServiceDep) -> Scenario:
    return await scenario_service.get_baseline()


@router.get(
    "",
    response_model=list[Scenario],
    dependencies=[Depends(require_roles(*READ_ROLES))],
)
async def list_scenarios(scenario_service: ScenarioServiceDep) -> list[Scenario]:
    return await scenario_service.list()


@router.get(
    "/{scenario_id}",
    response_model=Scenario,
    dependencies=[Depends(require_roles(*READ_ROLES))],
)
async def get_scenario(scenario_id: str, scenario_service: ScenarioServiceDep) -> Scenario:
    return await _scenario_action(lambda: scenario_service.get(scenario_id))


@router.post(
    "/{scenario_id}/approve",
    response_model=Scenario,
    dependencies=[Depends(require_roles(AppRole.MONITOR))],
)
async def approve_scenario(
    scenario_id: str,
    scenario_service: ScenarioServiceDep,
    current_user: CurrentUserDep,
) -> Scenario:
    return await _scenario_action(lambda: scenario_service.approve(scenario_id, current_user))


@router.post(
    "/{scenario_id}/reject",
    response_model=Scenario,
    dependencies=[Depends(require_roles(AppRole.MONITOR))],
)
async def reject_scenario(
    scenario_id: str,
    scenario_service: ScenarioServiceDep,
    current_user: CurrentUserDep,
) -> Scenario:
    return await _scenario_action(lambda: scenario_service.reject(scenario_id, current_user))


@router.post(
    "/{scenario_id}/apply",
    response_model=Scenario,
    dependencies=[Depends(require_roles(AppRole.MONITOR))],
)
async def apply_scenario(
    scenario_id: str,
    scenario_service: ScenarioServiceDep,
    current_user: CurrentUserDep,
) -> Scenario:
    return await _scenario_action(lambda: scenario_service.apply(scenario_id, current_user))
