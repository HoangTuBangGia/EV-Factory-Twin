from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ev_twin_api.api.dependencies import require_roles
from ev_twin_api.schemas.audit import AuditEvent
from ev_twin_api.schemas.auth import AppRole
from ev_twin_api.schemas.history import AuditHistoryQuery
from ev_twin_api.services.audit_service import AuditServiceDep

router = APIRouter(
    prefix="/api/v1/audit-events",
    tags=["audit"],
    dependencies=[Depends(require_roles(AppRole.MONITOR))],
)


@router.get("", response_model=list[AuditEvent])
async def list_audit_events(
    query: Annotated[AuditHistoryQuery, Query()],
    audit: AuditServiceDep,
) -> list[AuditEvent]:
    return await audit.list(
        limit=query.limit,
        resource_type=query.resource_type,
        resource_id=query.resource_id,
        created_after=query.start,
        created_before=query.end,
        cursor_before=query.before,
        cursor_before_id=query.before_id,
    )
