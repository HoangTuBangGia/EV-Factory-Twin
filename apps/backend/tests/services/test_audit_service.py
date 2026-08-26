from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from ev_twin_api.schemas.audit import AuditAction
from ev_twin_api.schemas.auth import AppRole
from ev_twin_api.services.audit_service import InMemoryAuditRepository, PendingAuditEvent

ACTOR_ID = UUID("00000000-0000-0000-0000-000000000002")
REQUEST_ID = UUID("10000000-0000-0000-0000-000000000001")


def event(created_at: datetime, resource_id: str) -> PendingAuditEvent:
    return PendingAuditEvent(
        actor_id=ACTOR_ID,
        actor_role=AppRole.MONITOR,
        action=AuditAction.COMMAND_COMPLETED,
        resource_type="command",
        resource_id=resource_id,
        before_data=None,
        after_data={"status": "COMPLETED"},
        request_id=REQUEST_ID,
        created_at=created_at,
    )


@pytest.mark.asyncio
async def test_audit_history_filters_orders_and_uses_exclusive_cursor() -> None:
    repository = InMemoryAuditRepository()
    now = datetime.now(UTC)
    await repository.record(event(now + timedelta(seconds=1), "OP-01"))
    await repository.record(event(now + timedelta(seconds=3), "OP-03"))
    await repository.record(event(now + timedelta(seconds=2), "OP-02"))

    first_page = await repository.list(
        limit=2,
        resource_type="command",
        created_after=now,
        created_before=now + timedelta(seconds=4),
    )
    second_page = await repository.list(
        limit=2,
        resource_type="command",
        created_after=now,
        created_before=now + timedelta(seconds=4),
        cursor_before=first_page[-1].created_at,
        cursor_before_id=first_page[-1].id,
    )

    assert [item.resource_id for item in first_page] == ["OP-03", "OP-02"]
    assert [item.resource_id for item in second_page] == ["OP-01"]


@pytest.mark.asyncio
async def test_audit_cursor_does_not_skip_events_with_the_same_timestamp() -> None:
    repository = InMemoryAuditRepository()
    now = datetime.now(UTC)
    await repository.record(event(now, "OP-01"))
    await repository.record(event(now, "OP-02"))

    first_page = await repository.list(limit=1)
    second_page = await repository.list(
        limit=1,
        cursor_before=first_page[0].created_at,
        cursor_before_id=first_page[0].id,
    )

    assert [item.resource_id for item in first_page] == ["OP-02"]
    assert [item.resource_id for item in second_page] == ["OP-01"]
