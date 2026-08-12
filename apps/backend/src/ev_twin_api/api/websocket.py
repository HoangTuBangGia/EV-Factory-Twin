from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ev_twin_api.services.websocket_manager import WebSocketManagerDep

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/factory")
async def factory_websocket(websocket: WebSocket, manager: WebSocketManagerDep) -> None:
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)
