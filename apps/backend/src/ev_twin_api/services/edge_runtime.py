from datetime import UTC, datetime

from ev_twin_api.schemas.edge_runtime import BridgeHealth, EdgeUpdateResponse, TaskUpdate
from ev_twin_api.schemas.task import Task, TaskStatus
from ev_twin_api.schemas.websocket import task_updated_event
from ev_twin_api.services.factory_state import FactoryState
from ev_twin_api.services.runtime_health import RuntimeHealthService
from ev_twin_api.services.runtime_history import (
    InMemoryRuntimeHistoryRepository,
    RuntimeHistoryRepository,
)
from ev_twin_api.services.websocket_manager import WebSocketManager


class EdgeRuntimeService:
    def __init__(
        self,
        state: FactoryState,
        websocket_manager: WebSocketManager,
        history_repository: RuntimeHistoryRepository | None = None,
        runtime_health: RuntimeHealthService | None = None,
    ) -> None:
        self._state = state
        self._websocket_manager = websocket_manager
        self._task_timestamps: dict[str, datetime] = {}
        self._bridge_health: dict[str, BridgeHealth] = {}
        self._history = history_repository or InMemoryRuntimeHistoryRepository()
        self._runtime_health = runtime_health

    async def ingest_task(self, update: TaskUpdate) -> EdgeUpdateResponse:
        ingested_at = datetime.now(UTC)
        await self._history.record_task(update, ingested_at)
        latest = self._task_timestamps.get(update.task_id)
        if latest is not None and update.updated_at <= latest:
            return EdgeUpdateResponse(accepted=False, identifier=update.task_id)

        current = self._state.get_task(update.task_id)
        created_at = current.created_at if current else update.updated_at
        started_at = current.started_at if current else None
        if started_at is None and update.status != TaskStatus.QUEUED:
            started_at = update.updated_at
        completed_at = (
            update.updated_at
            if update.status == TaskStatus.COMPLETED
            else (current.completed_at if current else None)
        )
        task = Task(
            task_id=update.task_id,
            payload_id=update.payload_id,
            pickup=update.pickup_station_id,
            dropoff=update.dropoff_station_id,
            assigned_robot_id=update.assigned_robot_id,
            status=update.status,
            created_at=created_at,
            started_at=started_at,
            completed_at=completed_at,
        )
        if current is None:
            self._state.add_task(task)
        else:
            self._state.update_task(task)
        self._task_timestamps[update.task_id] = update.updated_at
        await self._websocket_manager.broadcast(task_updated_event(task))
        return EdgeUpdateResponse(accepted=True, identifier=update.task_id)

    async def ingest_health(self, health: BridgeHealth) -> EdgeUpdateResponse:
        ingested_at = datetime.now(UTC)
        await self._history.record_bridge_health(health, ingested_at)
        current = self._bridge_health.get(health.bridge_id)
        if current is not None and health.timestamp <= current.timestamp:
            return EdgeUpdateResponse(accepted=False, identifier=health.bridge_id)
        self._bridge_health[health.bridge_id] = health
        if self._runtime_health is not None:
            await self._runtime_health.note_bridge_health(health, ingested_at)
        return EdgeUpdateResponse(accepted=True, identifier=health.bridge_id)

    def get_health(self, bridge_id: str) -> BridgeHealth | None:
        health = self._bridge_health.get(bridge_id)
        return health.model_copy(deep=True) if health else None
