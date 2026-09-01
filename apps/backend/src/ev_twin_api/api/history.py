from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ev_twin_api.api.dependencies import READ_ROLES, require_roles
from ev_twin_api.schemas.history import (
    HistoryPage,
    KpiHistoryItem,
    TaskHistoryItem,
    TelemetryHistoryItem,
)
from ev_twin_api.services.kpi_snapshot_writer import KpiSnapshotHistoryRepository
from ev_twin_api.services.runtime_history import RuntimeHistoryRepository

HISTORY_DEFAULT_WINDOW = timedelta(hours=1)
HISTORY_MAX_WINDOW = timedelta(days=7)

router = APIRouter(
    prefix="/api/v1/history",
    tags=["history"],
    dependencies=[Depends(require_roles(*READ_ROLES))],
)


@dataclass(frozen=True, slots=True)
class HistoryWindow:
    start: datetime
    end: datetime
    limit: int
    offset: int


def get_history_window(
    start: Annotated[datetime | None, Query()] = None,
    end: Annotated[datetime | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> HistoryWindow:
    resolved_end = end or datetime.now(UTC)
    resolved_start = start or resolved_end - HISTORY_DEFAULT_WINDOW
    if resolved_start.tzinfo is None or resolved_end.tzinfo is None:
        raise HTTPException(status_code=422, detail="history timestamps must include a timezone")
    if resolved_end < resolved_start:
        raise HTTPException(status_code=422, detail="history end must not precede start")
    if resolved_end - resolved_start > HISTORY_MAX_WINDOW:
        raise HTTPException(status_code=422, detail="history window must not exceed 7 days")
    return HistoryWindow(resolved_start, resolved_end, limit, offset)


def get_runtime_history(request: Request) -> RuntimeHistoryRepository:
    return cast(RuntimeHistoryRepository, request.app.state.runtime_history_repository)


def get_kpi_history(request: Request) -> KpiSnapshotHistoryRepository:
    return cast(KpiSnapshotHistoryRepository, request.app.state.kpi_history_repository)


HistoryWindowDep = Annotated[HistoryWindow, Depends(get_history_window)]
RuntimeHistoryDep = Annotated[RuntimeHistoryRepository, Depends(get_runtime_history)]
KpiHistoryDep = Annotated[KpiSnapshotHistoryRepository, Depends(get_kpi_history)]

def _page[ItemT](items: list[ItemT], window: HistoryWindow) -> HistoryPage[ItemT]:
    has_more = len(items) > window.limit
    return HistoryPage(
        items=items[: window.limit],
        next_offset=window.offset + window.limit if has_more else None,
    )


@router.get("/telemetry", response_model=HistoryPage[TelemetryHistoryItem])
async def list_telemetry_history(
    window: HistoryWindowDep,
    repository: RuntimeHistoryDep,
    robot_id: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
) -> HistoryPage[TelemetryHistoryItem]:
    items = await repository.list_telemetry(
        start=window.start,
        end=window.end,
        robot_id=robot_id,
        limit=window.limit + 1,
        offset=window.offset,
    )
    return _page(items, window)


@router.get("/tasks", response_model=HistoryPage[TaskHistoryItem])
async def list_task_history(
    window: HistoryWindowDep,
    repository: RuntimeHistoryDep,
    task_id: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
) -> HistoryPage[TaskHistoryItem]:
    items = await repository.list_tasks(
        start=window.start,
        end=window.end,
        task_id=task_id,
        limit=window.limit + 1,
        offset=window.offset,
    )
    return _page(items, window)


@router.get("/metrics", response_model=HistoryPage[KpiHistoryItem])
async def list_kpi_history(
    window: HistoryWindowDep,
    repository: KpiHistoryDep,
    scenario_id: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
) -> HistoryPage[KpiHistoryItem]:
    items = await repository.list(
        start=window.start,
        end=window.end,
        scenario_id=scenario_id,
        limit=window.limit + 1,
        offset=window.offset,
    )
    return _page(items, window)
