from datetime import UTC, datetime

from ev_twin_api.schemas.robot import Robot
from ev_twin_api.schemas.telemetry import (
    RobotTelemetry,
    TelemetryIngressResponse,
    TelemetryIngressStatus,
)
from ev_twin_api.schemas.websocket import robot_telemetry_event
from ev_twin_api.services.factory_state import FactoryState
from ev_twin_api.services.mock_factory import MockFactory
from ev_twin_api.services.websocket_manager import WebSocketManager


class UnknownRobotError(LookupError):
    pass


class MockSourceActiveError(RuntimeError):
    pass


class TelemetryIngressService:
    def __init__(
        self,
        factory_state: FactoryState,
        websocket_manager: WebSocketManager,
        mock_factory: MockFactory,
    ) -> None:
        self._factory_state = factory_state
        self._websocket_manager = websocket_manager
        self._mock_factory = mock_factory

    async def ingest(self, telemetry: RobotTelemetry) -> TelemetryIngressResponse:
        async with self._mock_factory.exclusive_control():
            if self._mock_factory.running:
                raise MockSourceActiveError

            current = self._factory_state.get_robot(telemetry.robot_id)
            if current is None:
                raise UnknownRobotError(telemetry.robot_id)

            ingested_at = datetime.now(UTC)
            if telemetry.timestamp <= current.last_seen_at:
                return TelemetryIngressResponse(
                    status=TelemetryIngressStatus.IGNORED_STALE,
                    robot_id=telemetry.robot_id,
                    source_timestamp=telemetry.timestamp,
                    ingested_at=ingested_at,
                )

            self._factory_state.update_robot(
                Robot(
                    id=current.id,
                    name=current.name,
                    status=telemetry.status,
                    pose=telemetry.pose,
                    velocity=telemetry.velocity,
                    battery=telemetry.battery,
                    task_id=telemetry.task_id,
                    payload_id=telemetry.payload_id,
                    last_seen_at=telemetry.timestamp,
                )
            )
            await self._websocket_manager.broadcast(robot_telemetry_event(telemetry))
            return TelemetryIngressResponse(
                status=TelemetryIngressStatus.ACCEPTED,
                robot_id=telemetry.robot_id,
                source_timestamp=telemetry.timestamp,
                ingested_at=ingested_at,
            )
