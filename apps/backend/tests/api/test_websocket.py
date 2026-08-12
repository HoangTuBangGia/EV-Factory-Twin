import asyncio
from types import SimpleNamespace
from typing import Any

import pytest
from ev_twin_api.api.websocket import factory_websocket
from ev_twin_api.schemas.factory import MockFactoryConfig
from ev_twin_api.schemas.task import Task
from ev_twin_api.schemas.telemetry import RobotTelemetry
from ev_twin_api.schemas.websocket import WebSocketEvent
from ev_twin_api.services.factory_state import FactoryState
from ev_twin_api.services.mock_factory import MockFactory
from ev_twin_api.services.websocket_manager import WebSocketManager
from fastapi import WebSocketDisconnect


class AsyncWebSocketClient:
    """Small ASGI-independent client for exercising the real WS route."""

    def __init__(self, manager: WebSocketManager) -> None:
        self.app = SimpleNamespace(state=SimpleNamespace(websocket_manager=manager))
        self.messages: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.accepted = asyncio.Event()
        self._disconnected = asyncio.Event()

    async def accept(self) -> None:
        self.accepted.set()

    async def send_json(self, payload: dict[str, Any]) -> None:
        await self.messages.put(payload)

    async def receive_text(self) -> str:
        await self._disconnected.wait()
        raise WebSocketDisconnect()

    async def receive_json(self, timeout: float = 2.0) -> dict[str, Any]:
        return await asyncio.wait_for(self.messages.get(), timeout)

    def disconnect(self) -> None:
        self._disconnected.set()


async def connect_client(
    manager: WebSocketManager,
) -> tuple[AsyncWebSocketClient, asyncio.Task[None]]:
    client = AsyncWebSocketClient(manager)
    route_task = asyncio.create_task(factory_websocket(client, manager))  # type: ignore[arg-type]
    await asyncio.wait_for(client.accepted.wait(), 1.0)
    return client, route_task


async def disconnect_client(client: AsyncWebSocketClient, route_task: asyncio.Task[None]) -> None:
    client.disconnect()
    await asyncio.wait_for(route_task, 1.0)


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
async def test_client_connects_and_receives_robot_telemetry() -> None:
    manager = WebSocketManager()
    client, route_task = await connect_client(manager)
    engine = make_engine(manager)

    await engine.tick(0.1)
    message = await client.receive_json()
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
            message = await client.receive_json()
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
    message1 = await client1.receive_json()
    message2 = await client2.receive_json()
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
    message = await second.receive_json()
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
        messages.append(await client.receive_json())
    await disconnect_client(client, route_task)

    task_messages = [message for message in messages if message["type"] == "task.updated"]
    assert task_messages
    Task.model_validate(task_messages[0]["data"])
