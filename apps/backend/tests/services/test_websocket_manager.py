from typing import Any

import pytest
from ev_twin_api.services.websocket_manager import WebSocketManager


class FakeWebSocket:
    def __init__(self, *, fail_on_send: bool = False) -> None:
        self.accepted = False
        self.sent: list[dict[str, Any]] = []
        self._fail_on_send = fail_on_send

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, data: dict[str, Any]) -> None:
        if self._fail_on_send:
            raise RuntimeError("connection closed")
        self.sent.append(data)


@pytest.mark.asyncio
async def test_connect_accepts_and_tracks_the_websocket() -> None:
    manager = WebSocketManager()
    websocket = FakeWebSocket()

    await manager.connect(websocket)  # type: ignore[arg-type]

    assert websocket.accepted is True
    assert websocket in manager._connections


def test_disconnect_removes_the_websocket() -> None:
    manager = WebSocketManager()
    websocket = FakeWebSocket()
    manager._connections.add(websocket)  # type: ignore[arg-type]

    manager.disconnect(websocket)  # type: ignore[arg-type]

    assert websocket not in manager._connections


def test_disconnect_of_unknown_websocket_does_not_raise() -> None:
    manager = WebSocketManager()
    manager.disconnect(FakeWebSocket())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_broadcast_sends_the_same_payload_to_every_connection() -> None:
    manager = WebSocketManager()
    ws1, ws2 = FakeWebSocket(), FakeWebSocket()
    await manager.connect(ws1)  # type: ignore[arg-type]
    await manager.connect(ws2)  # type: ignore[arg-type]

    await manager.broadcast({"type": "robot.telemetry", "data": {"robot_id": "AMR-01"}})

    assert ws1.sent == [{"type": "robot.telemetry", "data": {"robot_id": "AMR-01"}}]
    assert ws2.sent == ws1.sent


@pytest.mark.asyncio
async def test_broadcast_survives_one_dead_connection_and_drops_it() -> None:
    manager = WebSocketManager()
    healthy = FakeWebSocket()
    dead = FakeWebSocket(fail_on_send=True)
    await manager.connect(healthy)  # type: ignore[arg-type]
    await manager.connect(dead)  # type: ignore[arg-type]

    await manager.broadcast({"type": "factory.reset", "data": None})

    assert healthy.sent == [{"type": "factory.reset", "data": None}]
    assert dead not in manager._connections
    assert healthy in manager._connections
