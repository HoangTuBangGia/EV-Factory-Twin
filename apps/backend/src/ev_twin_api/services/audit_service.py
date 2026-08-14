import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Any, Protocol, cast
from uuid import UUID, uuid4

from fastapi import Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ev_twin_api.core.database import Database
from ev_twin_api.schemas.audit import AuditAction, AuditEvent
from ev_twin_api.schemas.auth import AppRole

AUDIT_INSERT_SQL = """
INSERT INTO public.audit_events (
    actor_id,
    actor_role,
    action,
    resource_type,
    resource_id,
    before_data,
    after_data,
    request_id,
    created_at
)
VALUES (
    :actor_id,
    CAST(:actor_role AS public.app_role),
    :action,
    :resource_type,
    :resource_id,
    CAST(:before_data AS jsonb),
    CAST(:after_data AS jsonb),
    :request_id,
    :created_at
)
"""

AUDIT_SELECT_SQL = """
SELECT
    id,
    actor_id,
    actor_role::text AS actor_role,
    action,
    resource_type,
    resource_id,
    before_data,
    after_data,
    request_id,
    created_at
FROM public.audit_events
"""


@dataclass(frozen=True)
class PendingAuditEvent:
    actor_id: UUID
    actor_role: AppRole
    action: AuditAction
    resource_type: str
    resource_id: str
    before_data: dict[str, Any] | None
    after_data: dict[str, Any] | None
    request_id: UUID
    created_at: datetime


class AuditRepository(Protocol):
    async def record(self, event: PendingAuditEvent) -> AuditEvent | None: ...

    async def list(
        self,
        *,
        limit: int,
        resource_type: str | None = None,
        resource_id: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
    ) -> list[AuditEvent]: ...


def _event_from_mapping(row: Any) -> AuditEvent:
    return AuditEvent.model_validate(dict(row))


async def insert_audit_event(session: AsyncSession, event: PendingAuditEvent) -> None:
    """Insert an event using an existing transaction owned by the caller."""

    await session.execute(
        text(AUDIT_INSERT_SQL),
        {
            "actor_id": event.actor_id,
            "actor_role": event.actor_role.value,
            "action": event.action.value,
            "resource_type": event.resource_type,
            "resource_id": event.resource_id,
            "before_data": json.dumps(event.before_data) if event.before_data is not None else None,
            "after_data": json.dumps(event.after_data) if event.after_data is not None else None,
            "request_id": event.request_id,
            "created_at": event.created_at,
        },
    )


class InMemoryAuditRepository:
    """Local/test audit store. Production uses PostgreSQL when DATABASE_URL exists."""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []
        self._next_id = 1
        self._lock = asyncio.Lock()

    async def record(self, event: PendingAuditEvent) -> AuditEvent:
        async with self._lock:
            stored = AuditEvent(id=self._next_id, **event.__dict__)
            self._next_id += 1
            self._events.append(stored)
            return stored.model_copy(deep=True)

    async def list(
        self,
        *,
        limit: int,
        resource_type: str | None = None,
        resource_id: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
    ) -> list[AuditEvent]:
        async with self._lock:
            events = (
                event
                for event in reversed(self._events)
                if (resource_type is None or event.resource_type == resource_type)
                and (resource_id is None or event.resource_id == resource_id)
                and (created_after is None or event.created_at >= created_after)
                and (created_before is None or event.created_at <= created_before)
            )
            return [event.model_copy(deep=True) for event in list(events)[:limit]]


class SqlAlchemyAuditRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def record(self, event: PendingAuditEvent) -> None:
        async with self._database.session() as session, session.begin():
            await insert_audit_event(session, event)

    async def list(
        self,
        *,
        limit: int,
        resource_type: str | None = None,
        resource_id: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
    ) -> list[AuditEvent]:
        clauses: list[str] = []
        params: dict[str, object] = {"limit": limit}
        if resource_type is not None:
            clauses.append("resource_type = :resource_type")
            params["resource_type"] = resource_type
        if resource_id is not None:
            clauses.append("resource_id = :resource_id")
            params["resource_id"] = resource_id
        if created_after is not None:
            clauses.append("created_at >= :created_after")
            params["created_after"] = created_after
        if created_before is not None:
            clauses.append("created_at <= :created_before")
            params["created_before"] = created_before

        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        statement = text(f"{AUDIT_SELECT_SQL}{where} ORDER BY created_at DESC LIMIT :limit")
        async with self._database.session() as session:
            result = await session.execute(statement, params)
        return [_event_from_mapping(row) for row in result.mappings().all()]


class AuditService:
    def __init__(self, repository: AuditRepository) -> None:
        self._repository = repository

    async def record(
        self,
        *,
        actor_id: UUID,
        actor_role: AppRole,
        action: AuditAction,
        resource_type: str,
        resource_id: str,
        before_data: dict[str, Any] | None = None,
        after_data: dict[str, Any] | None = None,
        request_id: UUID | None = None,
    ) -> None:
        await self._repository.record(
            PendingAuditEvent(
                actor_id=actor_id,
                actor_role=actor_role,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                before_data=before_data,
                after_data=after_data,
                request_id=request_id or uuid4(),
                created_at=datetime.now(UTC),
            )
        )

    async def list(
        self,
        *,
        limit: int,
        resource_type: str | None = None,
        resource_id: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
    ) -> list[AuditEvent]:
        return await self._repository.list(
            limit=limit,
            resource_type=resource_type,
            resource_id=resource_id,
            created_after=created_after,
            created_before=created_before,
        )


def get_audit_service(request: Request) -> AuditService:
    return cast(AuditService, request.app.state.audit_service)


AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]
