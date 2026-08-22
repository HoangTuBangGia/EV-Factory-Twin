from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


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
