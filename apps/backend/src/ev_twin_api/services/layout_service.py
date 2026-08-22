from collections.abc import Awaitable
from datetime import UTC, datetime
from typing import Annotated, cast
from uuid import uuid4

from fastapi import Depends, Request
from twin_core.models.layout import LayoutSummary, LayoutVersion

from ev_twin_api.schemas.auth import CurrentUser
from ev_twin_api.schemas.layout import (
    CreateLayoutRequest,
    CreateLayoutVersionRequest,
    UpdateLayoutRequest,
)
from ev_twin_api.services.layout_repository import (
    LayoutRepository,
    LayoutRepositoryConflictError,
    LayoutRepositoryNotFoundError,
)


class LayoutNotFoundError(LookupError):
    pass


class LayoutConflictError(RuntimeError):
    pass


class LayoutService:
    def __init__(self, repository: LayoutRepository) -> None:
        self._repository = repository

    async def create(self, request: CreateLayoutRequest, actor: CurrentUser) -> LayoutVersion:
        return await self._repository.create(
            name=request.name,
            content=request.content,
            actor=actor,
            request_id=uuid4(),
            occurred_at=datetime.now(UTC),
        )

    async def list(self) -> list[LayoutSummary]:
        return await self._repository.list()

    async def get(self, layout_id: str, version: int | None = None) -> LayoutVersion:
        layout = await self._repository.get(layout_id, version)
        if layout is None:
            suffix = f" version {version}" if version is not None else ""
            raise LayoutNotFoundError(f"Layout '{layout_id}'{suffix} not found")
        return layout

    async def update(
        self, layout_id: str, request: UpdateLayoutRequest, actor: CurrentUser
    ) -> LayoutVersion:
        return await self._translate(
            self._repository.update_name(
                layout_id=layout_id,
                name=request.name,
                actor=actor,
                request_id=uuid4(),
                occurred_at=datetime.now(UTC),
            )
        )

    async def create_version(
        self,
        layout_id: str,
        request: CreateLayoutVersionRequest,
        actor: CurrentUser,
    ) -> LayoutVersion:
        return await self._translate(
            self._repository.create_version(
                layout_id=layout_id,
                content=request.content,
                actor=actor,
                request_id=uuid4(),
                occurred_at=datetime.now(UTC),
            )
        )

    async def archive(self, layout_id: str, actor: CurrentUser) -> None:
        await self._translate(
            self._repository.archive(
                layout_id=layout_id,
                actor=actor,
                request_id=uuid4(),
                occurred_at=datetime.now(UTC),
            )
        )

    @staticmethod
    async def _translate[ResultT](operation: Awaitable[ResultT]) -> ResultT:
        try:
            return await operation
        except LayoutRepositoryNotFoundError as error:
            raise LayoutNotFoundError(str(error)) from error
        except LayoutRepositoryConflictError as error:
            raise LayoutConflictError(str(error)) from error


def get_layout_service(request: Request) -> LayoutService:
    return cast(LayoutService, request.app.state.layout_service)


LayoutServiceDep = Annotated[LayoutService, Depends(get_layout_service)]
