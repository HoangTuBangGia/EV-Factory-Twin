import hmac
import logging
from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ev_twin_api.core.config import Settings, get_settings
from ev_twin_api.core.security import AuthenticationUnavailableError, InvalidAccessTokenError
from ev_twin_api.schemas.auth import AppRole, CurrentUser
from ev_twin_api.services.auth_service import AuthService, UserAccessDeniedError

logger = logging.getLogger("ev_twin_api")

bearer_scheme = HTTPBearer(
    auto_error=False,
    bearerFormat="JWT",
    scheme_name="FactoryTwinAccessToken",
    description="Factory Twin access token",
)

edge_bearer_scheme = HTTPBearer(
    auto_error=False,
    bearerFormat="opaque secret",
    scheme_name="EdgeTelemetrySecret",
    description="Factory-edge telemetry bridge credential",
)


def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service  # type: ignore[no-any-return]


BearerCredentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
EdgeBearerCredentials = Annotated[HTTPAuthorizationCredentials | None, Depends(edge_bearer_scheme)]


async def get_current_user(
    credentials: BearerCredentials,
    auth_service: AuthServiceDep,
) -> CurrentUser:
    token = credentials.credentials if credentials is not None else None
    try:
        session = await auth_service.authenticate(token)
        return session.user
    except InvalidAccessTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error
    except UserAccessDeniedError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    except AuthenticationUnavailableError as error:
        logger.warning("authentication service unavailable: %s", error)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is unavailable",
        ) from error


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
RoleDependency = Callable[..., Coroutine[Any, Any, CurrentUser]]


def require_roles(*allowed_roles: AppRole) -> RoleDependency:
    allowed = frozenset(allowed_roles)

    async def check_role(current_user: CurrentUserDep) -> CurrentUser:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return check_role


READ_ROLES = (AppRole.DESIGNER, AppRole.MONITOR)


async def require_edge_telemetry_secret(
    credentials: EdgeBearerCredentials,
    settings: SettingsDep,
) -> None:
    configured = settings.edge_telemetry_shared_secret
    if configured is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Edge telemetry ingress is not configured",
        )
    supplied = credentials.credentials if credentials is not None else ""
    if not hmac.compare_digest(supplied, configured.get_secret_value()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid edge telemetry credential",
            headers={"WWW-Authenticate": "Bearer"},
        )
