import logging
from typing import Annotated, Any, cast

from fastapi import Depends, WebSocket

logger = logging.getLogger("ev_twin_api")


class WebSocketManager:
    """Tracks connected `/ws/factory` clients and broadcasts JSON payloads.

    A dead or slow connection must not stop the broadcast from reaching the
    rest of the clients: send failures are caught per-connection, logged, and
    the connection is dropped from the active set rather than raised.
    """

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)
        logger.info("WebSocket connected (%d active)", len(self._connections))

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)
        logger.info("WebSocket disconnected (%d active)", len(self._connections))

    async def broadcast(self, payload: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        for connection in list(self._connections):
            try:
                await connection.send_json(payload)
            except Exception:
                logger.debug("dropping dead WebSocket connection", exc_info=True)
                dead.append(connection)
        for connection in dead:
            self._connections.discard(connection)


def get_websocket_manager(websocket: WebSocket) -> WebSocketManager:
    return cast(WebSocketManager, websocket.app.state.websocket_manager)


WebSocketManagerDep = Annotated[WebSocketManager, Depends(get_websocket_manager)]
