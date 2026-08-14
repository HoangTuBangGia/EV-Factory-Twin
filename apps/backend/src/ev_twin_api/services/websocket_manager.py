import asyncio
import contextlib
import logging
from typing import Annotated, Any, cast
from uuid import UUID

from fastapi import Depends, WebSocket

logger = logging.getLogger("ev_twin_api")


class WebSocketManager:
    """Tracks authenticated clients and isolates slow broadcast consumers."""

    def __init__(self, *, send_timeout_seconds: float = 0.5) -> None:
        if send_timeout_seconds <= 0:
            raise ValueError("send_timeout_seconds must be greater than zero")
        self._send_timeout_seconds = send_timeout_seconds
        self._connections: dict[WebSocket, UUID] = {}

    async def accept(self, websocket: WebSocket) -> None:
        await websocket.accept()

    def register_authenticated(self, websocket: WebSocket, user_id: UUID) -> None:
        self._connections[websocket] = user_id
        logger.info("authenticated WebSocket connected (%d active)", len(self._connections))

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.pop(websocket, None)
        logger.info("WebSocket disconnected (%d active)", len(self._connections))

    async def disconnect_user(
        self,
        user_id: UUID,
        *,
        code: int = 4403,
        reason: str = "User account disabled",
    ) -> None:
        connections = [
            connection
            for connection, connection_user_id in list(self._connections.items())
            if connection_user_id == user_id
        ]
        for connection in connections:
            self._connections.pop(connection, None)
        await self._close_connections(connections, code=code, reason=reason)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        connections = list(self._connections)
        if not connections:
            return

        results = await asyncio.gather(
            *(self._send_with_timeout(connection, payload) for connection in connections)
        )
        dead = [
            connection
            for connection, delivered in zip(connections, results, strict=True)
            if not delivered
        ]
        for connection in dead:
            self._connections.pop(connection, None)
        await self._close_connections(
            dead,
            code=1011,
            reason="Realtime delivery failed",
        )

    async def _send_with_timeout(
        self,
        connection: WebSocket,
        payload: dict[str, Any],
    ) -> bool:
        try:
            await asyncio.wait_for(
                connection.send_json(payload),
                timeout=self._send_timeout_seconds,
            )
        except Exception:
            # asyncio.CancelledError is a BaseException, so server shutdown
            # cancellation is not swallowed here.
            logger.debug("dropping slow or dead WebSocket connection", exc_info=True)
            return False
        return True

    async def _close_connections(
        self,
        connections: list[WebSocket],
        *,
        code: int,
        reason: str,
    ) -> None:
        async def close(connection: WebSocket) -> None:
            with contextlib.suppress(Exception):
                await asyncio.wait_for(
                    connection.close(code=code, reason=reason),
                    timeout=self._send_timeout_seconds,
                )

        await asyncio.gather(*(close(connection) for connection in connections))


def get_websocket_manager(websocket: WebSocket) -> WebSocketManager:
    return cast(WebSocketManager, websocket.app.state.websocket_manager)


WebSocketManagerDep = Annotated[WebSocketManager, Depends(get_websocket_manager)]
