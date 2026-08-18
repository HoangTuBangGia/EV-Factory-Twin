from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ev_twin_api.schemas.auth import AppRole
from ev_twin_api.schemas.base import UtcDatetime


class AdminUser(BaseModel):
    id: UUID
    email: str
    display_name: str
    role: AppRole
    is_active: bool
    created_at: UtcDatetime


class AdminUserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: AppRole | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def require_at_least_one_change(self) -> "AdminUserUpdate":
        if self.role is None and self.is_active is None:
            raise ValueError("at least one user field must be updated")
        return self


class AdminInviteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    email: str = Field(min_length=3, max_length=254)
    display_name: str = Field(min_length=1, max_length=120)
    role: AppRole

    @field_validator("email")
    @classmethod
    def validate_email_shape(cls, value: str) -> str:
        local_part, separator, domain = value.rpartition("@")
        if (
            not separator
            or not local_part
            or "." not in domain
            or domain.startswith(".")
            or domain.endswith(".")
            or any(character.isspace() for character in value)
        ):
            raise ValueError("email must be a valid address")
        return value.casefold()
