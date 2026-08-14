import asyncio
import contextlib
import time
from typing import Annotated, cast

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from ev_twin_api.core.config import Settings, get_settings
from ev_twin_api.core.security import AuthenticationUnavailableError, InvalidAccessTokenError
from ev_twin_api.schemas.websocket import WebSocketAuthMessage, WebSocketAuthOkData, auth_ok_event
from ev_twin_api.services.auth_service import AuthService, UserAccessDeniedError
from ev_twin_api.services.websocket_manager import WebSocketManagerDep

router = APIRouter(tags=["websocket"])

WS_CLOSE_POLICY_VIOLATION = 1008
WS_CLOSE_TRY_AGAIN_LATER = 1013
WS_CLOSE_UNAUTHORIZED = 4401
WS_CLOSE_FORBIDDEN = 4403


def get_websocket_auth_service(websocket: WebSocket) -> AuthService:
    return cast(AuthService, websocket.app.state.auth_service)


WebSocketAuthServiceDep = Annotated[AuthService, Depends(get_websocket_auth_service)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def origin_is_allowed(origin: str | None, allowed_origins: list[str]) -> bool:
    if origin is None:
        return False
    normalized_origin = origin.rstrip("/")
    normalized_allowed = {allowed.rstrip("/") for allowed in allowed_origins}
    return "*" in normalized_allowed or normalized_origin in normalized_allowed


async def _close(websocket: WebSocket, *, code: int, reason: str) -> None:
    # The peer may disappear while an authentication failure is handled.
    with contextlib.suppress(RuntimeError, WebSocketDisconnect):
        await websocket.close(code=code, reason=reason)


async def _receive_auth_message(websocket: WebSocket, timeout_seconds: float) -> str | None:
    try:
        payload = await asyncio.wait_for(websocket.receive_json(), timeout=timeout_seconds)
        message = WebSocketAuthMessage.model_validate(payload)
    except TimeoutError:
        await _close(
            websocket,
            code=WS_CLOSE_UNAUTHORIZED,
            reason="Authentication timed out",
        )
        return None
    except (ValidationError, ValueError, TypeError, RuntimeError):
        await _close(
            websocket,
            code=WS_CLOSE_UNAUTHORIZED,
            reason="Invalid authentication message",
        )
        return None
    except WebSocketDisconnect:
        return None
    return message.access_token


async def _wait_until_disconnect(websocket: WebSocket) -> None:
    while True:
        await websocket.receive_text()


@router.websocket("/ws/factory")
async def factory_websocket(
    websocket: WebSocket,
    manager: WebSocketManagerDep,
    auth_service: WebSocketAuthServiceDep,
    settings: SettingsDep,
) -> None:
    await manager.accept(websocket)

    if not origin_is_allowed(websocket.headers.get("origin"), settings.cors_origins):
        await _close(
            websocket,
            code=WS_CLOSE_POLICY_VIOLATION,
            reason="Origin not allowed",
        )
        return

    access_token = await _receive_auth_message(
        websocket,
        settings.websocket_auth_timeout_seconds,
    )
    if access_token is None:
        return

    try:
        session = await auth_service.authenticate(access_token)
    except InvalidAccessTokenError:
        await _close(
            websocket,
            code=WS_CLOSE_UNAUTHORIZED,
            reason="Invalid or expired access token",
        )
        return
    except UserAccessDeniedError:
        await _close(
            websocket,
            code=WS_CLOSE_FORBIDDEN,
            reason="User account is not active",
        )
        return
    except AuthenticationUnavailableError:
        await _close(
            websocket,
            code=WS_CLOSE_TRY_AGAIN_LATER,
            reason="Authentication service is unavailable",
        )
        return

    seconds_until_expiry = session.expires_at - time.time()
    if seconds_until_expiry <= 0:
        await _close(
            websocket,
            code=WS_CLOSE_UNAUTHORIZED,
            reason="Access token expired",
        )
        return

    try:
        await websocket.send_json(
            auth_ok_event(
                WebSocketAuthOkData(
                    user_id=session.user.id,
                    display_name=session.user.display_name,
                    role=session.user.role,
                    expires_at=session.expires_at,
                )
            )
        )
    except (RuntimeError, WebSocketDisconnect):
        return

    seconds_until_expiry = session.expires_at - time.time()
    if seconds_until_expiry <= 0:
        await _close(
            websocket,
            code=WS_CLOSE_UNAUTHORIZED,
            reason="Access token expired",
        )
        return

    manager.register_authenticated(websocket, session.user.id)
    try:
        try:
            await asyncio.wait_for(
                _wait_until_disconnect(websocket),
                timeout=seconds_until_expiry,
            )
        except TimeoutError:
            await _close(
                websocket,
                code=WS_CLOSE_UNAUTHORIZED,
                reason="Access token expired",
            )
        except WebSocketDisconnect:
            pass
    finally:
        manager.disconnect(websocket)
