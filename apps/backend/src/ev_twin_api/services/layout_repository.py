import asyncio
import json
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy import text
from twin_core.models.layout import LayoutSummary, LayoutVersion, LayoutVersionContent

from ev_twin_api.core.database import Database
from ev_twin_api.schemas.audit import AuditAction
from ev_twin_api.schemas.auth import CurrentUser
from ev_twin_api.services.audit_service import (
    InMemoryAuditRepository,
    PendingAuditEvent,
    insert_audit_event,
)

LAYOUT_SELECT = """
SELECT id, name, latest_version, created_by, created_at, archived_at
FROM public.layouts
"""

VERSION_SELECT = """
SELECT
    versions.layout_id,
    layouts.name,
    versions.version,
    versions.content,
    versions.created_by,
    versions.created_at,
    layouts.archived_at
FROM public.layout_versions AS versions
JOIN public.layouts AS layouts ON layouts.id = versions.layout_id
"""


class LayoutRepositoryNotFoundError(LookupError):
    pass


class LayoutRepositoryConflictError(RuntimeError):
    pass


class LayoutRepository(Protocol):
    async def create(
        self,
        *,
        name: str,
        content: LayoutVersionContent,
        actor: CurrentUser,
        request_id: UUID,
        occurred_at: datetime,
    ) -> LayoutVersion: ...

    async def list(self) -> list[LayoutSummary]: ...

    async def get(self, layout_id: str, version: int | None = None) -> LayoutVersion | None: ...

    async def update_name(
        self,
        *,
        layout_id: str,
        name: str,
        actor: CurrentUser,
        request_id: UUID,
        occurred_at: datetime,
    ) -> LayoutVersion: ...

    async def create_version(
        self,
        *,
        layout_id: str,
        content: LayoutVersionContent,
        actor: CurrentUser,
        request_id: UUID,
        occurred_at: datetime,
    ) -> LayoutVersion: ...

    async def archive(
        self,
        *,
        layout_id: str,
        actor: CurrentUser,
        request_id: UUID,
        occurred_at: datetime,
    ) -> None: ...


def _summary(row: Any) -> LayoutSummary:
    return LayoutSummary.model_validate(dict(row))


def _version(row: Any) -> LayoutVersion:
    content = row["content"]
    if isinstance(content, str):
        content = json.loads(content)
    return LayoutVersion(
        layout_id=str(row["layout_id"]),
        name=str(row["name"]),
        version=int(row["version"]),
        created_by=row["created_by"],
        created_at=row["created_at"],
        archived_at=row["archived_at"],
        **content,
    )


def _audit(
    *,
    actor: CurrentUser,
    action: AuditAction,
    layout_id: str,
    request_id: UUID,
    occurred_at: datetime,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
) -> PendingAuditEvent:
    return PendingAuditEvent(
        actor_id=actor.id,
        actor_role=actor.role,
        action=action,
        resource_type="layout",
        resource_id=layout_id,
        before_data=before,
        after_data=after,
        request_id=request_id,
        created_at=occurred_at,
    )


class InMemoryLayoutRepository:
    def __init__(self, audit_repository: InMemoryAuditRepository | None = None) -> None:
        self.audit_repository = audit_repository or InMemoryAuditRepository()
        self._layouts: dict[str, LayoutSummary] = {}
        self._versions: dict[tuple[str, int], LayoutVersion] = {}
        self._next_id = 1
        self._lock = asyncio.Lock()

    async def create(self, *, name, content, actor, request_id, occurred_at) -> LayoutVersion:
        async with self._lock:
            layout_id = f"LAYOUT-{self._next_id:04d}"
            version = LayoutVersion(
                layout_id=layout_id,
                name=name.strip(),
                version=1,
                created_by=actor.id,
                created_at=occurred_at,
                **content.model_dump(),
            )
            self._layouts[layout_id] = LayoutSummary(
                id=layout_id,
                name=version.name,
                latest_version=1,
                created_by=actor.id,
                created_at=occurred_at,
            )
            self._versions[(layout_id, 1)] = version
            self._next_id += 1
            await self.audit_repository.record(
                _audit(
                    actor=actor,
                    action=AuditAction.LAYOUT_CREATED,
                    layout_id=layout_id,
                    request_id=request_id,
                    occurred_at=occurred_at,
                    before=None,
                    after=version.model_dump(mode="json"),
                )
            )
            return version.model_copy(deep=True)

    async def list(self) -> list[LayoutSummary]:
        async with self._lock:
            return [
                item.model_copy(deep=True)
                for item in sorted(self._layouts.values(), key=lambda value: value.created_at)
                if item.archived_at is None
            ]

    async def get(self, layout_id: str, version: int | None = None) -> LayoutVersion | None:
        async with self._lock:
            summary = self._layouts.get(layout_id)
            if summary is None:
                return None
            selected = version or summary.latest_version
            result = self._versions.get((layout_id, selected))
            if result is None:
                return None
            return result.model_copy(
                update={"name": summary.name, "archived_at": summary.archived_at}
            )

    async def update_name(
        self, *, layout_id, name, actor, request_id, occurred_at
    ) -> LayoutVersion:
        async with self._lock:
            summary = self._require_active(layout_id)
            before = summary.model_dump(mode="json")
            updated = summary.model_copy(update={"name": name.strip()})
            self._layouts[layout_id] = updated
            result = self._versions[(layout_id, updated.latest_version)].model_copy(
                update={"name": updated.name}
            )
            await self.audit_repository.record(
                _audit(
                    actor=actor,
                    action=AuditAction.LAYOUT_METADATA_UPDATED,
                    layout_id=layout_id,
                    request_id=request_id,
                    occurred_at=occurred_at,
                    before=before,
                    after=updated.model_dump(mode="json"),
                )
            )
            return result

    async def create_version(
        self, *, layout_id, content, actor, request_id, occurred_at
    ) -> LayoutVersion:
        async with self._lock:
            summary = self._require_active(layout_id)
            number = summary.latest_version + 1
            version = LayoutVersion(
                layout_id=layout_id,
                name=summary.name,
                version=number,
                created_by=actor.id,
                created_at=occurred_at,
                **content.model_dump(),
            )
            self._versions[(layout_id, number)] = version
            self._layouts[layout_id] = summary.model_copy(update={"latest_version": number})
            await self.audit_repository.record(
                _audit(
                    actor=actor,
                    action=AuditAction.LAYOUT_VERSION_CREATED,
                    layout_id=layout_id,
                    request_id=request_id,
                    occurred_at=occurred_at,
                    before=None,
                    after=version.model_dump(mode="json"),
                )
            )
            return version.model_copy(deep=True)

    async def archive(self, *, layout_id, actor, request_id, occurred_at) -> None:
        async with self._lock:
            summary = self._require_active(layout_id)
            archived = summary.model_copy(update={"archived_at": occurred_at})
            self._layouts[layout_id] = archived
            await self.audit_repository.record(
                _audit(
                    actor=actor,
                    action=AuditAction.LAYOUT_ARCHIVED,
                    layout_id=layout_id,
                    request_id=request_id,
                    occurred_at=occurred_at,
                    before=summary.model_dump(mode="json"),
                    after=archived.model_dump(mode="json"),
                )
            )

    def _require_active(self, layout_id: str) -> LayoutSummary:
        summary = self._layouts.get(layout_id)
        if summary is None:
            raise LayoutRepositoryNotFoundError(f"Layout '{layout_id}' not found")
        if summary.archived_at is not None:
            raise LayoutRepositoryConflictError(f"Layout '{layout_id}' is archived")
        return summary


class SqlAlchemyLayoutRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def create(self, *, name, content, actor, request_id, occurred_at) -> LayoutVersion:
        async with self._database.session() as session, session.begin():
            result = await session.execute(
                text("""
                    INSERT INTO public.layouts (name, created_by, created_at)
                    VALUES (:name, :created_by, :created_at)
                    RETURNING id
                """),
                {"name": name.strip(), "created_by": actor.id, "created_at": occurred_at},
            )
            layout_id = str(result.scalar_one())
            await session.execute(
                text("""
                    INSERT INTO public.layout_versions
                        (layout_id, version, content, created_by, created_at)
                    VALUES (:layout_id, 1, CAST(:content AS jsonb), :created_by, :created_at)
                """),
                {
                    "layout_id": layout_id,
                    "content": content.model_dump_json(),
                    "created_by": actor.id,
                    "created_at": occurred_at,
                },
            )
            version = LayoutVersion(
                layout_id=layout_id,
                name=name.strip(),
                version=1,
                created_by=actor.id,
                created_at=occurred_at,
                **content.model_dump(),
            )
            await insert_audit_event(
                session,
                _audit(
                    actor=actor,
                    action=AuditAction.LAYOUT_CREATED,
                    layout_id=layout_id,
                    request_id=request_id,
                    occurred_at=occurred_at,
                    before=None,
                    after=version.model_dump(mode="json"),
                ),
            )
        return version

    async def list(self) -> list[LayoutSummary]:
        async with self._database.session() as session:
            result = await session.execute(
                text(f"{LAYOUT_SELECT} WHERE archived_at IS NULL ORDER BY created_at, id")
            )
        return [_summary(row) for row in result.mappings().all()]

    async def get(self, layout_id: str, version: int | None = None) -> LayoutVersion | None:
        clause = (
            "versions.version = :version"
            if version is not None
            else ("versions.version = layouts.latest_version")
        )
        async with self._database.session() as session:
            result = await session.execute(
                text(f"{VERSION_SELECT} WHERE versions.layout_id = :layout_id AND {clause}"),
                {"layout_id": layout_id, "version": version},
            )
        row = result.mappings().one_or_none()
        return _version(row) if row is not None else None

    async def update_name(
        self, *, layout_id, name, actor, request_id, occurred_at
    ) -> LayoutVersion:
        async with self._database.session() as session, session.begin():
            before = await self._locked_summary(session, layout_id)
            result = await session.execute(
                text("""
                    UPDATE public.layouts SET name = :name
                    WHERE id = :layout_id AND archived_at IS NULL
                    RETURNING id
                """),
                {"layout_id": layout_id, "name": name.strip()},
            )
            if result.scalar_one_or_none() is None:
                raise LayoutRepositoryConflictError(f"Layout '{layout_id}' is archived")
            after = before.model_copy(update={"name": name.strip()})
            await insert_audit_event(
                session,
                _audit(
                    actor=actor,
                    action=AuditAction.LAYOUT_METADATA_UPDATED,
                    layout_id=layout_id,
                    request_id=request_id,
                    occurred_at=occurred_at,
                    before=before.model_dump(mode="json"),
                    after=after.model_dump(mode="json"),
                ),
            )
        layout = await self.get(layout_id)
        assert layout is not None
        return layout

    async def create_version(
        self, *, layout_id, content, actor, request_id, occurred_at
    ) -> LayoutVersion:
        async with self._database.session() as session, session.begin():
            summary = await self._locked_summary(session, layout_id)
            if summary.archived_at is not None:
                raise LayoutRepositoryConflictError(f"Layout '{layout_id}' is archived")
            number = summary.latest_version + 1
            await session.execute(
                text("""
                    INSERT INTO public.layout_versions
                        (layout_id, version, content, created_by, created_at)
                    VALUES (:layout_id, :version, CAST(:content AS jsonb), :created_by, :created_at)
                """),
                {
                    "layout_id": layout_id,
                    "version": number,
                    "content": content.model_dump_json(),
                    "created_by": actor.id,
                    "created_at": occurred_at,
                },
            )
            await session.execute(
                text("UPDATE public.layouts SET latest_version = :version WHERE id = :layout_id"),
                {"layout_id": layout_id, "version": number},
            )
            version = LayoutVersion(
                layout_id=layout_id,
                name=summary.name,
                version=number,
                created_by=actor.id,
                created_at=occurred_at,
                **content.model_dump(),
            )
            await insert_audit_event(
                session,
                _audit(
                    actor=actor,
                    action=AuditAction.LAYOUT_VERSION_CREATED,
                    layout_id=layout_id,
                    request_id=request_id,
                    occurred_at=occurred_at,
                    before=None,
                    after=version.model_dump(mode="json"),
                ),
            )
        return version

    async def archive(self, *, layout_id, actor, request_id, occurred_at) -> None:
        async with self._database.session() as session, session.begin():
            before = await self._locked_summary(session, layout_id)
            if before.archived_at is not None:
                raise LayoutRepositoryConflictError(f"Layout '{layout_id}' is archived")
            await session.execute(
                text("UPDATE public.layouts SET archived_at = :at WHERE id = :layout_id"),
                {"layout_id": layout_id, "at": occurred_at},
            )
            after = before.model_copy(update={"archived_at": occurred_at})
            await insert_audit_event(
                session,
                _audit(
                    actor=actor,
                    action=AuditAction.LAYOUT_ARCHIVED,
                    layout_id=layout_id,
                    request_id=request_id,
                    occurred_at=occurred_at,
                    before=before.model_dump(mode="json"),
                    after=after.model_dump(mode="json"),
                ),
            )

    @staticmethod
    async def _locked_summary(session, layout_id: str) -> LayoutSummary:
        result = await session.execute(
            text(f"{LAYOUT_SELECT} WHERE id = :layout_id FOR UPDATE"),
            {"layout_id": layout_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise LayoutRepositoryNotFoundError(f"Layout '{layout_id}' not found")
        return _summary(row)
