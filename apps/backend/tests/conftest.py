from collections.abc import AsyncIterator

import pytest_asyncio
from ev_twin_api.main import app
from httpx2 import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://test") as async_client,
    ):
        yield async_client
