from collections.abc import AsyncIterator
from datetime import UTC, datetime
from functools import partial
from uuid import UUID

import pytest
import pytest_asyncio
from conftest import make_test_user
from ev_twin_api.api.admin_users import get_admin_user_service
from ev_twin_api.api.dependencies import get_current_user
from ev_twin_api.main import app
from ev_twin_api.schemas.admin import AdminInviteRequest, AdminUser, AdminUserUpdate
from ev_twin_api.schemas.auth import AppRole, CurrentUser
from ev_twin_api.services.admin_user_service import (
    AdminUserConflictError,
    AdminUserNotFoundError,
    LastActiveAdminError,
    UserAdministrationUnavailableError,
)
from httpx2 import AsyncClient

TARGET_ID = UUID("00000000-0000-0000-0000-000000000008")
CREATED_AT = datetime(2026, 8, 14, 3, 0, tzinfo=UTC)


def user() -> AdminUser:
    return AdminUser(
        id=TARGET_ID,
        email="user@example.com",
        display_name="Factory User",
        role=AppRole.DESIGNER,
        is_active=True,
        created_at=CREATED_AT,
    )


class StubAdminUserService:
    def __init__(self) -> None:
        self.users = [user()]
        self.list_error: Exception | None = None
        self.update_error: Exception | None = None
        self.invite_error: Exception | None = None
        self.update_calls: list[tuple[UUID, AdminUserUpdate, CurrentUser]] = []
        self.invite_calls: list[tuple[AdminInviteRequest, CurrentUser]] = []

    async def list(self) -> list[AdminUser]:
        if self.list_error is not None:
            raise self.list_error
        return self.users

    async def update(
        self,
        user_id: UUID,
        update: AdminUserUpdate,
        *,
        actor: CurrentUser,
    ) -> AdminUser:
        self.update_calls.append((user_id, update, actor))
        if self.update_error is not None:
            raise self.update_error
        result = self.users[0].model_copy(
            update={
                "role": update.role or self.users[0].role,
                "is_active": (
                    update.is_active if update.is_active is not None else self.users[0].is_active
                ),
            }
        )
        self.users = [result]
        return result

    async def invite(
        self,
        invite: AdminInviteRequest,
        *,
        actor: CurrentUser,
    ) -> AdminUser:
        self.invite_calls.append((invite, actor))
        if self.invite_error is not None:
            raise self.invite_error
        invited = AdminUser(
            id=TARGET_ID,
            email=invite.email,
            display_name=invite.display_name,
            role=invite.role,
            is_active=True,
            created_at=CREATED_AT,
        )
        self.users = [invited]
        return invited


@pytest_asyncio.fixture
async def admin_service() -> AsyncIterator[StubAdminUserService]:
    service = StubAdminUserService()
    previous = app.dependency_overrides.get(get_admin_user_service)
    app.dependency_overrides[get_admin_user_service] = lambda: service
    try:
        yield service
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_admin_user_service, None)
        else:
            app.dependency_overrides[get_admin_user_service] = previous


def use_role(role: AppRole) -> None:
    app.dependency_overrides[get_current_user] = partial(make_test_user, role)


@pytest.mark.asyncio
async def test_admin_list_contract_excludes_credentials(
    client: AsyncClient,
    admin_service: StubAdminUserService,
) -> None:
    del admin_service
    use_role(AppRole.ADMIN)

    response = await client.get("/api/v1/admin/users")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(TARGET_ID),
            "email": "user@example.com",
            "display_name": "Factory User",
            "role": "DESIGNER",
            "is_active": True,
            "created_at": "2026-08-14T03:00:00.000Z",
        }
    ]
    assert {"password", "encrypted_password", "token", "access_token"}.isdisjoint(
        response.json()[0]
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [AppRole.DESIGNER, AppRole.MONITOR])
@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("GET", "/api/v1/admin/users", None),
        ("PATCH", f"/api/v1/admin/users/{TARGET_ID}", {"role": "MONITOR"}),
        (
            "POST",
            "/api/v1/admin/users/invite",
            {
                "email": "new@example.com",
                "display_name": "New User",
                "role": "DESIGNER",
            },
        ),
    ],
)
async def test_non_admin_cannot_use_any_admin_user_endpoint(
    client: AsyncClient,
    admin_service: StubAdminUserService,
    role: AppRole,
    method: str,
    path: str,
    payload: dict[str, object] | None,
) -> None:
    use_role(role)

    response = await client.request(method, path, json=payload)

    assert response.status_code == 403
    assert admin_service.update_calls == []
    assert admin_service.invite_calls == []


@pytest.mark.asyncio
async def test_admin_updates_role_and_status_contract(
    client: AsyncClient,
    admin_service: StubAdminUserService,
) -> None:
    use_role(AppRole.ADMIN)

    response = await client.patch(
        f"/api/v1/admin/users/{TARGET_ID}",
        json={"role": "MONITOR", "is_active": False},
    )

    assert response.status_code == 200
    assert response.json()["role"] == "MONITOR"
    assert response.json()["is_active"] is False
    assert admin_service.update_calls[0][0] == TARGET_ID
    assert admin_service.update_calls[0][2].role == AppRole.ADMIN


@pytest.mark.asyncio
async def test_admin_invite_is_201_and_never_accepts_password(
    client: AsyncClient,
    admin_service: StubAdminUserService,
) -> None:
    use_role(AppRole.ADMIN)
    payload = {
        "email": "new@example.com",
        "display_name": "New Monitor",
        "role": "MONITOR",
    }

    response = await client.post("/api/v1/admin/users/invite", json=payload)
    rejected = await client.post(
        "/api/v1/admin/users/invite",
        json={**payload, "password": "must-not-reach-the-service"},
    )

    assert response.status_code == 201
    assert response.json()["email"] == "new@example.com"
    assert rejected.status_code == 422
    assert len(admin_service.invite_calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (AdminUserNotFoundError("missing"), 404),
        (LastActiveAdminError("final admin"), 409),
        (UserAdministrationUnavailableError("database"), 503),
    ],
)
async def test_update_errors_have_safe_http_statuses(
    client: AsyncClient,
    admin_service: StubAdminUserService,
    error: Exception,
    expected_status: int,
) -> None:
    use_role(AppRole.ADMIN)
    admin_service.update_error = error

    response = await client.patch(
        f"/api/v1/admin/users/{TARGET_ID}",
        json={"is_active": False},
    )

    assert response.status_code == expected_status
    if expected_status == 503:
        assert response.json() == {"detail": "User administration is unavailable"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (AdminUserConflictError("email already exists"), 409),
        (UserAdministrationUnavailableError("missing service key"), 503),
    ],
)
async def test_invite_errors_have_safe_http_statuses(
    client: AsyncClient,
    admin_service: StubAdminUserService,
    error: Exception,
    expected_status: int,
) -> None:
    use_role(AppRole.ADMIN)
    admin_service.invite_error = error

    response = await client.post(
        "/api/v1/admin/users/invite",
        json={
            "email": "new@example.com",
            "display_name": "New User",
            "role": "DESIGNER",
        },
    )

    assert response.status_code == expected_status
    if expected_status == 503:
        assert response.json() == {"detail": "User administration is unavailable"}
