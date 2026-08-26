from datetime import UTC, datetime, timedelta

import pytest
from conftest import make_test_user
from ev_twin_api.api.dependencies import get_current_user
from ev_twin_api.main import app
from ev_twin_api.schemas.audit import AuditAction
from ev_twin_api.schemas.auth import AppRole
from httpx2 import AsyncClient


def params(now: datetime) -> dict[str, str]:
    return {
        "start": (now - timedelta(seconds=1)).isoformat(),
        "end": (now + timedelta(seconds=1)).isoformat(),
    }


@pytest.mark.asyncio
async def test_monitor_can_filter_audit_history_without_secret_fields(client: AsyncClient) -> None:
    now = datetime.now(UTC)
    await app.state.audit_service.record(
        actor_id=make_test_user(AppRole.MONITOR).id,
        actor_role=AppRole.MONITOR,
        action=AuditAction.COMMAND_COMPLETED,
        resource_type="command",
        resource_id="OP-01",
        after_data={"status": "COMPLETED"},
    )

    response = await client.get(
        "/api/v1/audit-events",
        params={**params(now), "resource_type": "command"},
    )

    assert response.status_code == 200
    assert response.json()[0]["resource_id"] == "OP-01"
    assert "password" not in response.text.lower()
    assert "secret" not in response.text.lower()


@pytest.mark.asyncio
async def test_designer_cannot_read_audit_history(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: make_test_user(AppRole.DESIGNER)

    response = await client.get("/api/v1/audit-events", params=params(datetime.now(UTC)))

    assert response.status_code == 403
