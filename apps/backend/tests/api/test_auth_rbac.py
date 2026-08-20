from functools import partial
from typing import Any
from uuid import UUID

import pytest
from conftest import make_test_user
from ev_twin_api.api.dependencies import get_current_user
from ev_twin_api.core.security import VerifiedIdentity
from ev_twin_api.main import app
from ev_twin_api.schemas.auth import AppRole
from ev_twin_api.services.auth_service import AuthService, ProfileRecord
from httpx2 import AsyncClient

SCENARIO_PAYLOAD = {
    "name": "rbac-candidate",
    "num_robots": 3,
    "num_tasks": 10,
    "task_arrival_interval": 10.0,
    "travel_time": 30.0,
    "loading_time": 10.0,
    "simulation_time": 3600.0,
}

MOCK_CONFIG = {
    "robot_count": 3,
    "task_interval_seconds": 10.0,
    "robot_speed_mps": 1.0,
    "simulation_speed": 1.0,
    "low_battery_threshold": 20.0,
}

READ_ENDPOINTS = [
    ("/api/v1/auth/me", 200),
    ("/api/v1/factory", 200),
    ("/api/v1/robots", 200),
    ("/api/v1/robots/AMR-01", 200),
    ("/api/v1/tasks", 200),
    ("/api/v1/tasks/TASK-9999", 404),
    ("/api/v1/metrics", 200),
    ("/api/v1/alerts", 200),
    ("/api/v1/scenarios", 200),
    ("/api/v1/scenarios/baseline", 200),
    ("/api/v1/scenarios/SCN-9999", 404),
]

PROTECTED_REQUESTS: list[tuple[str, str, dict[str, object] | None]] = [
    *(("GET", path, None) for path, _ in READ_ENDPOINTS),
    ("POST", "/api/v1/scenarios/run", SCENARIO_PAYLOAD),
    ("POST", "/api/v1/scenarios/SCN-9999/approve", None),
    ("POST", "/api/v1/scenarios/SCN-9999/reject", None),
    ("POST", "/api/v1/scenarios/SCN-9999/apply", None),
    ("POST", "/api/v1/mock/start", None),
    ("POST", "/api/v1/mock/stop", None),
    ("POST", "/api/v1/mock/reset", None),
    ("POST", "/api/v1/mock/config", MOCK_CONFIG),
    ("GET", "/api/v1/admin/audit", None),
    ("GET", "/api/v1/admin/users", None),
    (
        "PATCH",
        "/api/v1/admin/users/00000000-0000-0000-0000-000000000008",
        {"is_active": False},
    ),
    (
        "POST",
        "/api/v1/admin/users/invite",
        {
            "email": "new@example.com",
            "display_name": "New User",
            "role": "DESIGNER",
        },
    ),
]


def use_role(role: AppRole) -> None:
    app.dependency_overrides[get_current_user] = partial(make_test_user, role)


class FixedVerifier:
    async def verify(self, token: str) -> VerifiedIdentity:
        assert token == "test-token"
        return VerifiedIdentity(
            id=UUID("00000000-0000-0000-0000-000000000009"),
            email="inactive@example.com",
            expires_at=2_000_000_000,
        )


class FixedProfiles:
    def __init__(self, profile: ProfileRecord | None) -> None:
        self._profile = profile

    async def get(self, user_id: UUID) -> ProfileRecord | None:
        del user_id
        return self._profile


async def request(
    client: AsyncClient,
    method: str,
    path: str,
    payload: dict[str, object] | None,
) -> Any:
    if payload is None:
        return await client.request(method, path)
    return await client.request(method, path, json=payload)


@pytest.mark.asyncio
@pytest.mark.parametrize("role", list(AppRole))
@pytest.mark.parametrize(("path", "expected_status"), READ_ENDPOINTS)
async def test_all_roles_can_read_protected_resources(
    client: AsyncClient,
    role: AppRole,
    path: str,
    expected_status: int,
) -> None:
    use_role(role)

    response = await client.get(path)

    assert response.status_code == expected_status


@pytest.mark.asyncio
async def test_designer_run_then_monitor_review_and_apply(client: AsyncClient) -> None:
    use_role(AppRole.DESIGNER)
    run_response = await client.post("/api/v1/scenarios/run", json=SCENARIO_PAYLOAD)
    assert run_response.status_code == 200
    scenario_id = run_response.json()["id"]

    use_role(AppRole.MONITOR)
    approve_response = await client.post(f"/api/v1/scenarios/{scenario_id}/approve")
    apply_response = await client.post(f"/api/v1/scenarios/{scenario_id}/apply")

    assert approve_response.status_code == 200
    assert apply_response.status_code == 200
    assert apply_response.json()["status"] == "APPLIED"


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [AppRole.MONITOR, AppRole.ADMIN])
async def test_only_designer_can_run_scenario(client: AsyncClient, role: AppRole) -> None:
    use_role(role)

    response = await client.post("/api/v1/scenarios/run", json=SCENARIO_PAYLOAD)

    assert response.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [AppRole.DESIGNER, AppRole.ADMIN])
@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/scenarios/SCN-9999/approve",
        "/api/v1/scenarios/SCN-9999/reject",
        "/api/v1/scenarios/SCN-9999/apply",
        "/api/v1/mock/start",
        "/api/v1/mock/stop",
        "/api/v1/mock/reset",
        "/api/v1/mock/config",
    ],
)
async def test_only_monitor_can_mutate_review_or_factory(
    client: AsyncClient,
    role: AppRole,
    path: str,
) -> None:
    use_role(role)
    payload = MOCK_CONFIG if path.endswith("/config") else None

    response = await request(client, "POST", path, payload)

    assert response.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [AppRole.DESIGNER, AppRole.MONITOR])
async def test_only_admin_can_read_audit_events(client: AsyncClient, role: AppRole) -> None:
    use_role(role)

    response = await client.get("/api/v1/admin/audit")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_reads_scenario_audit_with_actor_and_time(client: AsyncClient) -> None:
    designer = make_test_user(AppRole.DESIGNER)
    use_role(AppRole.DESIGNER)
    run_response = await client.post("/api/v1/scenarios/run", json=SCENARIO_PAYLOAD)
    assert run_response.status_code == 200
    scenario_id = run_response.json()["id"]

    use_role(AppRole.ADMIN)
    response = await client.get(
        "/api/v1/admin/audit",
        params={"resource_type": "scenario", "resource_id": scenario_id},
    )

    assert response.status_code == 200
    events = response.json()
    assert len(events) == 1
    assert events[0]["action"] == "SCENARIO_RUN"
    assert events[0]["actor_id"] == str(designer.id)
    assert events[0]["created_at"].endswith("Z")


@pytest.mark.asyncio
async def test_manual_factory_reset_is_audited(client: AsyncClient) -> None:
    monitor = make_test_user(AppRole.MONITOR)
    use_role(AppRole.MONITOR)
    reset_response = await client.post("/api/v1/mock/reset")
    assert reset_response.status_code == 200

    use_role(AppRole.ADMIN)
    response = await client.get(
        "/api/v1/admin/audit",
        params={"resource_type": "factory", "resource_id": "mock-factory"},
    )

    assert response.status_code == 200
    events = response.json()
    assert [event["action"] for event in events[:2]] == [
        "FACTORY_RESET",
        "FACTORY_RESET_REQUESTED",
    ]
    assert {event["request_id"] for event in events[:2]} == {events[0]["request_id"]}
    assert events[0]["actor_id"] == str(monitor.id)
    assert events[0]["after_data"]["reason"] == "manual"


@pytest.mark.asyncio
async def test_manual_factory_config_records_before_after_and_intent(client: AsyncClient) -> None:
    monitor = make_test_user(AppRole.MONITOR)
    use_role(AppRole.MONITOR)
    config_response = await client.post("/api/v1/mock/config", json=MOCK_CONFIG)
    assert config_response.status_code == 200

    use_role(AppRole.ADMIN)
    response = await client.get(
        "/api/v1/admin/audit",
        params={"resource_type": "factory", "resource_id": "mock-factory"},
    )

    assert response.status_code == 200
    events = response.json()
    assert [event["action"] for event in events[:2]] == [
        "FACTORY_CONFIG_CHANGED",
        "FACTORY_CONFIG_CHANGE_REQUESTED",
    ]
    assert {event["request_id"] for event in events[:2]} == {events[0]["request_id"]}
    assert events[0]["actor_id"] == str(monitor.id)
    assert events[0]["after_data"] == MOCK_CONFIG


@pytest.mark.asyncio
@pytest.mark.parametrize(("method", "path", "payload"), PROTECTED_REQUESTS)
async def test_every_non_health_rest_endpoint_requires_authentication(
    client: AsyncClient,
    method: str,
    path: str,
    payload: dict[str, object] | None,
) -> None:
    app.dependency_overrides.pop(get_current_user, None)

    response = await request(client, method, path, payload)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.asyncio
@pytest.mark.parametrize("stored_profile", [None, "inactive"])
async def test_missing_or_inactive_database_profile_returns_403(
    client: AsyncClient,
    stored_profile: str | None,
) -> None:
    app.dependency_overrides.pop(get_current_user, None)
    profile = (
        ProfileRecord(
            id=UUID("00000000-0000-0000-0000-000000000009"),
            display_name="Inactive User",
            role=AppRole.DESIGNER,
            is_active=False,
        )
        if stored_profile
        else None
    )
    app.state.auth_service = AuthService(
        verifier=FixedVerifier(),
        profiles=FixedProfiles(profile),
    )

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_missing_server_auth_configuration_returns_503(client: AsyncClient) -> None:
    app.dependency_overrides.pop(get_current_user, None)
    app.state.auth_service = AuthService(
        verifier=None,
        profiles=FixedProfiles(None),
    )

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 503


def test_openapi_declares_bearer_security_for_all_non_health_rest_operations() -> None:
    schema = app.openapi()
    schemes = schema["components"]["securitySchemes"]
    assert schemes["SupabaseAccessToken"]["scheme"] == "bearer"
    assert schemes["SupabaseAccessToken"]["bearerFormat"] == "JWT"

    for path, path_item in schema["paths"].items():
        for method, operation in path_item.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            if path == "/health":
                assert "security" not in operation
            elif path == "/internal/v1/telemetry":
                assert {"EdgeTelemetrySecret": []} in operation["security"]
            else:
                assert {"SupabaseAccessToken": []} in operation["security"]
