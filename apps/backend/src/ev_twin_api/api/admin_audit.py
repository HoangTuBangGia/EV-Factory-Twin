from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ev_twin_api.api.dependencies import require_roles
from ev_twin_api.schemas.audit import AuditEvent
from ev_twin_api.schemas.auth import AppRole
from ev_twin_api.services.audit_service import AuditServiceDep

router = APIRouter(
    prefix="/api/v1/admin/audit",
    tags=["admin", "audit"],
    dependencies=[Depends(require_roles(AppRole.ADMIN))],
)


@router.get("", response_model=list[AuditEvent])
async def list_audit_events(
    audit_service: AuditServiceDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    resource_type: Annotated[str | None, Query(min_length=1, max_length=80)] = None,
    resource_id: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
) -> list[AuditEvent]:
    return await audit_service.list(
        limit=limit,
        resource_type=resource_type,
        resource_id=resource_id,
        created_after=created_after,
        created_before=created_before,
    )
