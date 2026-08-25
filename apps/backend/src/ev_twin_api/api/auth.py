from fastapi import APIRouter, HTTPException, Response, status

from ev_twin_api.api.dependencies import AuthServiceDep, CurrentUserDep
from ev_twin_api.core.security import AuthenticationUnavailableError, InvalidCredentialsError
from ev_twin_api.schemas.auth import CurrentUser, LoginRequest, LoginResponse
from ev_twin_api.services.auth_service import UserAccessDeniedError

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, auth_service: AuthServiceDep) -> LoginResponse:
    try:
        return await auth_service.login(payload.email, payload.password)
    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        ) from error
    except UserAccessDeniedError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    except AuthenticationUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is unavailable",
        ) from error


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=CurrentUser)
async def get_me(current_user: CurrentUserDep) -> CurrentUser:
    return current_user
