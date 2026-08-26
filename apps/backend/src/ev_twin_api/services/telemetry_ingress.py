from datetime import UTC, datetime, timedelta

from ev_twin_api.schemas.robot import Robot
from ev_twin_api.schemas.telemetry import (
    RobotTelemetry,
    TelemetryIngressResponse,
    TelemetryIngressStatus,
)
from ev_twin_api.schemas.websocket import robot_telemetry_event
from ev_twin_api.services.factory_state import FactoryState
from ev_twin_api.services.mock_factory import MockFactory
from ev_twin_api.services.runtime_health import RuntimeHealthService
from ev_twin_api.services.runtime_history import (
    InMemoryRuntimeHistoryRepository,
    RuntimeHistoryRepository,
)
from ev_twin_api.services.telemetry_evidence import TelemetryEvidence
from ev_twin_api.services.telemetry_persistence import TelemetryPersistenceWorker
from ev_twin_api.services.websocket_manager import WebSocketManager


class UnknownRobotError(LookupError):
    pass


class MockSourceActiveError(RuntimeError):
    pass


class FutureTimestampError(ValueError):
    pass


class TelemetryIngressService:
    def __init__(
        self,
        factory_state: FactoryState,
        websocket_manager: WebSocketManager,
        mock_factory: MockFactory,
        max_future_skew_seconds: float,
        history_repository: RuntimeHistoryRepository | None = None,
        runtime_health: RuntimeHealthService | None = None,
        persistence_worker: TelemetryPersistenceWorker | None = None,
        evidence: TelemetryEvidence | None = None,
    ) -> None:
        self._factory_state = factory_state
        self._websocket_manager = websocket_manager
        self._mock_factory = mock_factory
        self._max_future_skew = timedelta(seconds=max_future_skew_seconds)
        self._history = history_repository or InMemoryRuntimeHistoryRepository()
        self._runtime_health = runtime_health
        self._persistence_worker = persistence_worker
        self._evidence = evidence or TelemetryEvidence()

    async def ingest(self, telemetry: RobotTelemetry) -> TelemetryIngressResponse:
        self._evidence.record_received()
        async with self._mock_factory.exclusive_control():
            if self._mock_factory.running:
                self._evidence.record_rejected_mock_active()
                raise MockSourceActiveError

            current = self._factory_state.get_robot(telemetry.robot_id)
            if current is None:
                self._evidence.record_rejected_unknown_robot()
                raise UnknownRobotError(telemetry.robot_id)

            ingested_at = datetime.now(UTC)
            if telemetry.timestamp > ingested_at + self._max_future_skew:
                self._evidence.record_rejected_future_timestamp()
                raise FutureTimestampError
            ordering_status = (
                TelemetryIngressStatus.IGNORED_STALE
                if telemetry.timestamp <= current.last_seen_at
                else TelemetryIngressStatus.ACCEPTED
            )
            if ordering_status == TelemetryIngressStatus.ACCEPTED:
                self._evidence.record_accepted(telemetry.timestamp, ingested_at)
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

            else:
                self._evidence.record_ignored_stale()

        if ordering_status == TelemetryIngressStatus.ACCEPTED:
            await self._websocket_manager.broadcast(
                robot_telemetry_event(
                    telemetry,
                    ingested_at=ingested_at,
                    broadcast_at=datetime.now(UTC),
                )
            )

        if self._persistence_worker is not None:
            self._persistence_worker.submit(telemetry, ingested_at, ordering_status)
        else:
            await self._history.record_telemetry(telemetry, ingested_at, ordering_status)
            if (
                ordering_status == TelemetryIngressStatus.ACCEPTED
                and self._runtime_health is not None
            ):
                await self._runtime_health.note_telemetry(telemetry, ingested_at)
        return TelemetryIngressResponse(
            status=ordering_status,
            robot_id=telemetry.robot_id,
            source_timestamp=telemetry.timestamp,
            ingested_at=ingested_at,
        )
