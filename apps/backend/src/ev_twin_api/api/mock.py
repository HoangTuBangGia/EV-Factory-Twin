from uuid import uuid4

from fastapi import APIRouter, Depends

from ev_twin_api.api.dependencies import CurrentUserDep, require_roles
from ev_twin_api.schemas.audit import AuditAction
from ev_twin_api.schemas.auth import AppRole
from ev_twin_api.schemas.factory import MockFactoryConfig
from ev_twin_api.schemas.mock import MockControlResponse
from ev_twin_api.services.audit_service import AuditServiceDep
from ev_twin_api.services.mock_factory import MockFactory, MockFactoryDep

router = APIRouter(
    prefix="/api/v1/mock",
    tags=["mock"],
    dependencies=[Depends(require_roles(AppRole.MONITOR))],
)


def _control_response(mock_factory: MockFactory) -> MockControlResponse:
    return MockControlResponse(
        running=mock_factory.running,
        tick_count=mock_factory.tick_count,
        simulated_elapsed_seconds=mock_factory.simulated_elapsed_seconds,
    )


@router.post("/start", response_model=MockControlResponse)
async def start_mock(mock_factory: MockFactoryDep) -> MockControlResponse:
    async with mock_factory.exclusive_control():
        await mock_factory.start()
        return _control_response(mock_factory)


@router.post("/stop", response_model=MockControlResponse)
async def stop_mock(mock_factory: MockFactoryDep) -> MockControlResponse:
    async with mock_factory.exclusive_control():
        await mock_factory.stop()
        return _control_response(mock_factory)


@router.post("/reset", response_model=MockControlResponse)
async def reset_mock(
    mock_factory: MockFactoryDep,
    audit_service: AuditServiceDep,
    current_user: CurrentUserDep,
) -> MockControlResponse:
    async with mock_factory.exclusive_control():
        request_id = uuid4()
        before = {
            "control": _control_response(mock_factory).model_dump(mode="json"),
            "config": mock_factory.config.model_dump(mode="json"),
        }
        await audit_service.record(
            actor_id=current_user.id,
            actor_role=current_user.role,
            action=AuditAction.FACTORY_RESET_REQUESTED,
            resource_type="factory",
            resource_id="mock-factory",
            before_data=before,
            after_data={"reason": "manual", "requested": True},
            request_id=request_id,
        )
        await mock_factory.reset()
        response = _control_response(mock_factory)
        await audit_service.record(
            actor_id=current_user.id,
            actor_role=current_user.role,
            action=AuditAction.FACTORY_RESET,
            resource_type="factory",
            resource_id="mock-factory",
            before_data=before,
            after_data={
                "reason": "manual",
                "control": response.model_dump(mode="json"),
                "config": mock_factory.config.model_dump(mode="json"),
            },
            request_id=request_id,
        )
        return response


@router.post("/config", response_model=MockFactoryConfig)
async def update_mock_config(
    new_config: MockFactoryConfig,
    mock_factory: MockFactoryDep,
    audit_service: AuditServiceDep,
    current_user: CurrentUserDep,
) -> MockFactoryConfig:
    async with mock_factory.exclusive_control():
        request_id = uuid4()
        before = mock_factory.config.model_dump(mode="json")
        await audit_service.record(
            actor_id=current_user.id,
            actor_role=current_user.role,
            action=AuditAction.FACTORY_CONFIG_CHANGE_REQUESTED,
            resource_type="factory",
            resource_id="mock-factory",
            before_data=before,
            after_data=new_config.model_dump(mode="json"),
            request_id=request_id,
        )
        mock_factory.apply_config(new_config)
        await audit_service.record(
            actor_id=current_user.id,
            actor_role=current_user.role,
            action=AuditAction.FACTORY_CONFIG_CHANGED,
            resource_type="factory",
            resource_id="mock-factory",
            before_data=before,
            after_data=mock_factory.config.model_dump(mode="json"),
            request_id=request_id,
        )
        return mock_factory.config
