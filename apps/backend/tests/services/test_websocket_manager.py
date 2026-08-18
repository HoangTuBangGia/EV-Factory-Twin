import asyncio
import time
from typing import Any
from uuid import UUID

import pytest
from ev_twin_api.services.websocket_manager import WebSocketManager


class FakeWebSocket:
    def __init__(self, *, fail_on_send: bool = False, send_delay: float = 0.0) -> None:
        self.accepted = False
        self.sent: list[dict[str, Any]] = []
        self.close_code: int | None = None
        self.close_reason: str | None = None
        self._fail_on_send = fail_on_send
        self._send_delay = send_delay

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, data: dict[str, Any]) -> None:
        if self._send_delay:
            await asyncio.sleep(self._send_delay)
        if self._fail_on_send:
            raise RuntimeError("connection closed")
        self.sent.append(data)

    async def close(self, code: int = 1000, reason: str | None = None) -> None:
        self.close_code = code
        self.close_reason = reason


USER_1 = UUID("00000000-0000-0000-0000-000000000001")
USER_2 = UUID("00000000-0000-0000-0000-000000000002")


@pytest.mark.asyncio
async def test_accept_does_not_register_unauthenticated_websocket() -> None:
    manager = WebSocketManager()
    websocket = FakeWebSocket()

    await manager.accept(websocket)  # type: ignore[arg-type]

    assert websocket.accepted is True
    assert websocket not in manager._connections


def test_register_authenticated_tracks_the_websocket() -> None:
    manager = WebSocketManager()
    websocket = FakeWebSocket()

    manager.register_authenticated(websocket, USER_1)  # type: ignore[arg-type]

    assert websocket in manager._connections
    assert manager._connections[websocket] == USER_1


def test_disconnect_removes_the_websocket() -> None:
    manager = WebSocketManager()
    websocket = FakeWebSocket()
    manager.register_authenticated(websocket, USER_1)  # type: ignore[arg-type]

    manager.disconnect(websocket)  # type: ignore[arg-type]

    assert websocket not in manager._connections


def test_disconnect_of_unknown_websocket_does_not_raise() -> None:
    manager = WebSocketManager()
    manager.disconnect(FakeWebSocket())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_broadcast_sends_the_same_payload_to_every_connection() -> None:
    manager = WebSocketManager()
    ws1, ws2 = FakeWebSocket(), FakeWebSocket()
    manager.register_authenticated(ws1, USER_1)  # type: ignore[arg-type]
    manager.register_authenticated(ws2, USER_2)  # type: ignore[arg-type]

    await manager.broadcast({"type": "robot.telemetry", "data": {"robot_id": "AMR-01"}})

    assert ws1.sent == [{"type": "robot.telemetry", "data": {"robot_id": "AMR-01"}}]
    assert ws2.sent == ws1.sent


@pytest.mark.asyncio
async def test_broadcast_survives_one_dead_connection_and_drops_it() -> None:
    manager = WebSocketManager()
    healthy = FakeWebSocket()
    dead = FakeWebSocket(fail_on_send=True)
    manager.register_authenticated(healthy, USER_1)  # type: ignore[arg-type]
    manager.register_authenticated(dead, USER_2)  # type: ignore[arg-type]

    await manager.broadcast({"type": "factory.reset", "data": None})

    assert healthy.sent == [{"type": "factory.reset", "data": None}]
    assert dead not in manager._connections
    assert healthy in manager._connections
    assert dead.close_code == 1011


@pytest.mark.asyncio
async def test_disconnect_user_closes_every_session_for_only_that_user() -> None:
    manager = WebSocketManager()
    user_socket_1 = FakeWebSocket()
    user_socket_2 = FakeWebSocket()
    other_user_socket = FakeWebSocket()
    manager.register_authenticated(user_socket_1, USER_1)  # type: ignore[arg-type]
    manager.register_authenticated(user_socket_2, USER_1)  # type: ignore[arg-type]
    manager.register_authenticated(other_user_socket, USER_2)  # type: ignore[arg-type]

    await manager.disconnect_user(USER_1, reason="Account disabled by administrator")

    assert user_socket_1 not in manager._connections
    assert user_socket_2 not in manager._connections
    assert other_user_socket in manager._connections
    for websocket in (user_socket_1, user_socket_2):
        assert websocket.close_code == 4403
        assert websocket.close_reason == "Account disabled by administrator"
    assert other_user_socket.close_code is None


@pytest.mark.asyncio
async def test_slow_client_times_out_without_blocking_healthy_client() -> None:
    manager = WebSocketManager(send_timeout_seconds=0.05)
    slow = FakeWebSocket(send_delay=1.0)
    healthy = FakeWebSocket()
    manager.register_authenticated(slow, USER_1)  # type: ignore[arg-type]
    manager.register_authenticated(healthy, USER_2)  # type: ignore[arg-type]
    payload = {"type": "robot.telemetry", "data": {"robot_id": "AMR-01"}}

    started_at = time.monotonic()
    await manager.broadcast(payload)
    elapsed = time.monotonic() - started_at

    assert elapsed < 0.2
    assert healthy.sent == [payload]
    assert healthy in manager._connections
    assert slow.sent == []
    assert slow not in manager._connections
    assert slow.close_code == 1011
