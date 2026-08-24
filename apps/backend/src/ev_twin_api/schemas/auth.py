from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AppRole(StrEnum):
    DESIGNER = "DESIGNER"
    MONITOR = "MONITOR"


class CurrentUser(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    email: str
    display_name: str
    role: AppRole
    is_active: bool


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=1024)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized.count("@") != 1:
            raise ValueError("invalid email")
        return normalized


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: int
    user: CurrentUser
