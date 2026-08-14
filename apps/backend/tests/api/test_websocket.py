import asyncio
import time
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest
from ev_twin_api.api.websocket import factory_websocket
from ev_twin_api.core.config import Settings
from ev_twin_api.core.security import AuthenticationUnavailableError, InvalidAccessTokenError
from ev_twin_api.schemas.auth import AppRole, CurrentUser
from ev_twin_api.schemas.factory import MockFactoryConfig
from ev_twin_api.schemas.task import Task
from ev_twin_api.schemas.telemetry import RobotTelemetry
from ev_twin_api.schemas.websocket import WebSocketEvent
from ev_twin_api.services.auth_service import AuthenticatedSession, UserAccessDeniedError
from ev_twin_api.services.factory_state import FactoryState
from ev_twin_api.services.mock_factory import MockFactory
from ev_twin_api.services.websocket_manager import WebSocketManager
from fastapi import WebSocketDisconnect

ALLOWED_ORIGIN = "http://localhost:3000"
USER_ID = UUID("00000000-0000-0000-0000-000000000001")


class AsyncWebSocketClient:
    """Small ASGI-independent client for exercising the real WS route."""

    def __init__(self, manager: WebSocketManager, *, origin: str | None = ALLOWED_ORIGIN) -> None:
        self.manager = manager
        self.app = SimpleNamespace(state=SimpleNamespace(websocket_manager=manager))
        self.headers = {"origin": origin} if origin is not None else {}
        self.messages: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.incoming: asyncio.Queue[object] = asyncio.Queue()
        self.accepted = asyncio.Event()
        self.closed = asyncio.Event()
        self.close_code: int | None = None
        self.close_reason: str | None = None
        self._disconnected = asyncio.Event()

    async def accept(self) -> None:
        self.accepted.set()

    async def send_json(self, payload: dict[str, Any]) -> None:
        await self.messages.put(payload)

    async def receive_json(self) -> object:
        return await self.incoming.get()

    async def receive_text(self) -> str:
        await self._disconnected.wait()
        raise WebSocketDisconnect()

    async def close(self, code: int = 1000, reason: str | None = None) -> None:
        self.close_code = code
        self.close_reason = reason
        self.closed.set()
        self._disconnected.set()

    async def next_message(self, timeout: float = 2.0) -> dict[str, Any]:
        return await asyncio.wait_for(self.messages.get(), timeout)

    async def authenticate(self, token: str = "valid-token") -> None:
        await self.incoming.put({"type": "auth", "access_token": token})

    def disconnect(self) -> None:
        self._disconnected.set()


class StubAuthService:
    def __init__(
        self,
        *,
        error: Exception | None = None,
        expires_at: int | None = None,
    ) -> None:
        self._error = error
        self._expires_at = expires_at

    async def authenticate(self, token: str | None) -> AuthenticatedSession:
        if self._error is not None:
            raise self._error
        if token != "valid-token":
            raise InvalidAccessTokenError("invalid access token")
        return AuthenticatedSession(
            user=CurrentUser(
                id=USER_ID,
                email="monitor@example.com",
                display_name="Factory Monitor",
                role=AppRole.MONITOR,
                is_active=True,
            ),
            expires_at=(
                self._expires_at if self._expires_at is not None else int(time.time()) + 3600
            ),
        )


def websocket_settings(*, timeout: float = 1.0) -> Settings:
    return Settings(
        _env_file=None,
        cors_origins=[ALLOWED_ORIGIN],
        websocket_auth_timeout_seconds=timeout,
    )


async def start_client(
    manager: WebSocketManager,
    *,
    auth_service: StubAuthService | None = None,
    settings: Settings | None = None,
    origin: str | None = ALLOWED_ORIGIN,
) -> tuple[AsyncWebSocketClient, asyncio.Task[None]]:
    client = AsyncWebSocketClient(manager, origin=origin)
    route_task = asyncio.create_task(
        factory_websocket(
            client,  # type: ignore[arg-type]
            manager,
            auth_service or StubAuthService(),  # type: ignore[arg-type]
            settings or websocket_settings(),
        )
    )
    await asyncio.wait_for(client.accepted.wait(), 1.0)
    return client, route_task


async def connect_client(
    manager: WebSocketManager,
) -> tuple[AsyncWebSocketClient, asyncio.Task[None]]:
    client, route_task = await start_client(manager)
    await client.authenticate()
    auth_ok = await client.next_message()
    assert auth_ok["type"] == "auth.ok"
    await asyncio.sleep(0)
    return client, route_task


async def disconnect_client(client: AsyncWebSocketClient, route_task: asyncio.Task[None]) -> None:
    client.disconnect()
    await asyncio.wait_for(route_task, 1.0)
    assert client not in client.manager._connections


def make_engine(
    manager: WebSocketManager, *, task_interval: float = 8.0, simulation_speed: float = 1.0
) -> MockFactory:
    config = MockFactoryConfig(
        task_interval_seconds=task_interval,
        simulation_speed=simulation_speed,
        robot_speed_mps=3.0,
    )
    return MockFactory(FactoryState(config), config, manager)


@pytest.mark.asyncio
async def test_unauthenticated_client_is_not_registered_or_sent_telemetry() -> None:
    manager = WebSocketManager()
    client, route_task = await start_client(manager)
    engine = make_engine(manager)

    assert client not in manager._connections
    await engine.tick(0.1)
    assert client.messages.empty()

    await client.authenticate()
    auth_ok = await client.next_message()
    assert auth_ok["type"] == "auth.ok"
    await asyncio.sleep(0)
    assert client in manager._connections
    assert manager._connections[client] == USER_ID

    await disconnect_client(client, route_task)


@pytest.mark.asyncio
async def test_valid_auth_returns_identity_ack_without_email_or_token() -> None:
    manager = WebSocketManager()
    client, route_task = await start_client(manager)
    await client.authenticate()

    auth_ok = await client.next_message()

    assert auth_ok == {
        "type": "auth.ok",
        "data": {
            "user_id": str(USER_ID),
            "display_name": "Factory Monitor",
            "role": "MONITOR",
            "expires_at": auth_ok["data"]["expires_at"],
        },
    }
    assert "email" not in auth_ok["data"]
    assert "access_token" not in str(auth_ok)
    await disconnect_client(client, route_task)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("auth_service", "expected_code"),
    [
        (StubAuthService(), 4401),
        (StubAuthService(error=UserAccessDeniedError("inactive")), 4403),
        (StubAuthService(error=AuthenticationUnavailableError("unavailable")), 1013),
    ],
)
async def test_authentication_failure_closes_without_registration(
    auth_service: StubAuthService,
    expected_code: int,
) -> None:
    manager = WebSocketManager()
    client, route_task = await start_client(manager, auth_service=auth_service)
    token = "invalid-token" if expected_code == 4401 else "valid-token"

    await client.authenticate(token)
    await asyncio.wait_for(client.closed.wait(), 1.0)
    await asyncio.wait_for(route_task, 1.0)

    assert client.close_code == expected_code
    assert client not in manager._connections
    assert client.messages.empty()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"type": "wrong", "access_token": "valid-token"},
        {"type": "auth"},
        {"type": "auth", "access_token": "valid-token", "extra": "rejected"},
    ],
)
async def test_malformed_first_message_closes_4401(payload: dict[str, object]) -> None:
    manager = WebSocketManager()
    client, route_task = await start_client(manager)

    await client.incoming.put(payload)
    await asyncio.wait_for(client.closed.wait(), 1.0)
    await asyncio.wait_for(route_task, 1.0)

    assert client.close_code == 4401
    assert client not in manager._connections


@pytest.mark.asyncio
async def test_authentication_timeout_closes_4401() -> None:
    manager = WebSocketManager()
    client, route_task = await start_client(manager, settings=websocket_settings(timeout=0.1))

    await asyncio.wait_for(client.closed.wait(), 1.0)
    await asyncio.wait_for(route_task, 1.0)

    assert client.close_code == 4401
    assert client not in manager._connections


@pytest.mark.asyncio
@pytest.mark.parametrize("origin", [None, "https://attacker.example"])
async def test_missing_or_disallowed_origin_closes_1008(origin: str | None) -> None:
    manager = WebSocketManager()
    client, route_task = await start_client(manager, origin=origin)

    await asyncio.wait_for(client.closed.wait(), 1.0)
    await asyncio.wait_for(route_task, 1.0)

    assert client.close_code == 1008
    assert client not in manager._connections


@pytest.mark.asyncio
async def test_connection_closes_and_unregisters_at_token_expiry() -> None:
    manager = WebSocketManager()
    auth_service = StubAuthService(expires_at=int(time.time()) + 1)
    client, route_task = await start_client(manager, auth_service=auth_service)
    await client.authenticate()
    assert (await client.next_message())["type"] == "auth.ok"
    await asyncio.sleep(0)
    assert client in manager._connections

    await asyncio.wait_for(client.closed.wait(), 2.0)
    await asyncio.wait_for(route_task, 1.0)

    assert client.close_code == 4401
    assert client not in manager._connections


@pytest.mark.asyncio
async def test_client_connects_and_receives_robot_telemetry() -> None:
    manager = WebSocketManager()
    client, route_task = await connect_client(manager)
    engine = make_engine(manager)

    await engine.tick(0.1)
    message = await client.next_message()
    await disconnect_client(client, route_task)

    event = WebSocketEvent.model_validate(message)
    assert event.type == "robot.telemetry"
    telemetry = RobotTelemetry.model_validate(message["data"])
    assert telemetry.robot_id.startswith("AMR-")


@pytest.mark.asyncio
async def test_client_receives_changing_amr_coordinates_without_polling() -> None:
    manager = WebSocketManager()
    client, route_task = await connect_client(manager)
    engine = make_engine(manager, task_interval=1.0)

    positions: list[tuple[float, float]] = []
    for _ in range(80):
        await engine.tick(0.1)
        while not client.messages.empty():
            message = await client.next_message()
            if message["type"] != "robot.telemetry":
                continue
            telemetry = RobotTelemetry.model_validate(message["data"])
            if telemetry.robot_id == "AMR-01":
                positions.append((telemetry.pose.x, telemetry.pose.y))
        if len(positions) >= 2 and positions[-1] != positions[0]:
            break
    await disconnect_client(client, route_task)

    assert len(positions) >= 2
    assert positions[-1] != positions[0]


@pytest.mark.asyncio
async def test_multiple_clients_receive_the_same_broadcast() -> None:
    manager = WebSocketManager()
    client1, task1 = await connect_client(manager)
    client2, task2 = await connect_client(manager)
    engine = make_engine(manager)

    await engine.tick(0.1)
    message1 = await client1.next_message()
    message2 = await client2.next_message()
    await disconnect_client(client1, task1)
    await disconnect_client(client2, task2)

    assert message1 == message2
    assert message1["type"] == "robot.telemetry"


@pytest.mark.asyncio
async def test_client_disconnect_does_not_crash_subsequent_connections() -> None:
    manager = WebSocketManager()
    first, first_task = await connect_client(manager)
    await disconnect_client(first, first_task)

    second, second_task = await connect_client(manager)
    engine = make_engine(manager)
    await engine.tick(0.1)
    message = await second.next_message()
    await disconnect_client(second, second_task)

    assert message["type"] == "robot.telemetry"


@pytest.mark.asyncio
async def test_task_updated_event_is_broadcast() -> None:
    manager = WebSocketManager()
    client, route_task = await connect_client(manager)
    engine = make_engine(manager, task_interval=1.0, simulation_speed=10.0)

    await engine.tick(1.0)
    messages = []
    while not client.messages.empty():
        messages.append(await client.next_message())
    await disconnect_client(client, route_task)

    task_messages = [message for message in messages if message["type"] == "task.updated"]
    assert task_messages
    Task.model_validate(task_messages[0]["data"])
