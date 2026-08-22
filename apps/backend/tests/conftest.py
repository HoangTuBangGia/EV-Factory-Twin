from collections.abc import AsyncIterator
from uuid import UUID

import pytest_asyncio
from ev_twin_api.api.dependencies import get_current_user
from ev_twin_api.main import app
from ev_twin_api.schemas.auth import AppRole, CurrentUser
from httpx2 import ASGITransport, AsyncClient


def make_test_user(role: AppRole = AppRole.MONITOR) -> CurrentUser:
    user_number = {
        AppRole.DESIGNER: 1,
        AppRole.MONITOR: 2,
    }[role]
    return CurrentUser(
        id=UUID(f"00000000-0000-0000-0000-{user_number:012d}"),
        email=f"{role.value.lower()}@example.com",
        display_name=f"Test {role.value.title()}",
        role=role,
        is_active=True,
    )


def get_test_monitor() -> CurrentUser:
    return make_test_user()


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    previous_override = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = get_test_monitor
    transport = ASGITransport(app=app)
    try:
        async with (
            app.router.lifespan_context(app),
            AsyncClient(transport=transport, base_url="http://test") as async_client,
        ):
            yield async_client
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_current_user, None)
        else:
            app.dependency_overrides[get_current_user] = previous_override
