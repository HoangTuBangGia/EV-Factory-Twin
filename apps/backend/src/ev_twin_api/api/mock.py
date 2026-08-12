from fastapi import APIRouter

from ev_twin_api.schemas.factory import MockFactoryConfig
from ev_twin_api.schemas.mock import MockControlResponse
from ev_twin_api.services.mock_factory import MockFactory, MockFactoryDep

router = APIRouter(prefix="/api/v1/mock", tags=["mock"])


def _control_response(mock_factory: MockFactory) -> MockControlResponse:
    return MockControlResponse(
        running=mock_factory.running,
        tick_count=mock_factory.tick_count,
        simulated_elapsed_seconds=mock_factory.simulated_elapsed_seconds,
    )


@router.post("/start", response_model=MockControlResponse)
async def start_mock(mock_factory: MockFactoryDep) -> MockControlResponse:
    await mock_factory.start()
    return _control_response(mock_factory)


@router.post("/stop", response_model=MockControlResponse)
async def stop_mock(mock_factory: MockFactoryDep) -> MockControlResponse:
    await mock_factory.stop()
    return _control_response(mock_factory)


@router.post("/reset", response_model=MockControlResponse)
async def reset_mock(mock_factory: MockFactoryDep) -> MockControlResponse:
    await mock_factory.reset()
    return _control_response(mock_factory)


@router.post("/config", response_model=MockFactoryConfig)
async def update_mock_config(
    new_config: MockFactoryConfig, mock_factory: MockFactoryDep
) -> MockFactoryConfig:
    mock_factory.apply_config(new_config)
    return mock_factory.config
