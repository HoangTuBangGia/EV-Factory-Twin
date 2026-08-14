from fastapi import APIRouter

from ev_twin_api.api.dependencies import CurrentUserDep
from ev_twin_api.schemas.auth import CurrentUser

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/me", response_model=CurrentUser)
async def get_me(current_user: CurrentUserDep) -> CurrentUser:
    return current_user
