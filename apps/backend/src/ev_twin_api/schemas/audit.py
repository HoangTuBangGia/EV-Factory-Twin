from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from ev_twin_api.schemas.auth import AppRole
from ev_twin_api.schemas.base import UtcDatetime


class AuditAction(StrEnum):
    LAYOUT_CREATED = "LAYOUT_CREATED"
    LAYOUT_METADATA_UPDATED = "LAYOUT_METADATA_UPDATED"
    LAYOUT_VERSION_CREATED = "LAYOUT_VERSION_CREATED"
    LAYOUT_ARCHIVED = "LAYOUT_ARCHIVED"
    SCENARIO_RUN = "SCENARIO_RUN"
    SCENARIO_APPROVED = "SCENARIO_APPROVED"
    SCENARIO_REJECTED = "SCENARIO_REJECTED"
    SCENARIO_APPLIED = "SCENARIO_APPLIED"
    FACTORY_RESET_REQUESTED = "FACTORY_RESET_REQUESTED"
    FACTORY_RESET = "FACTORY_RESET"
    FACTORY_CONFIG_CHANGE_REQUESTED = "FACTORY_CONFIG_CHANGE_REQUESTED"
    FACTORY_CONFIG_CHANGED = "FACTORY_CONFIG_CHANGED"
    ROLE_CHANGED = "ROLE_CHANGED"
    USER_DISABLED = "USER_DISABLED"
    USER_ENABLED = "USER_ENABLED"
    USER_INVITED = "USER_INVITED"


class AuditEvent(BaseModel):
    id: int
    actor_id: UUID
    actor_role: AppRole
    action: AuditAction
    resource_type: str
    resource_id: str
    before_data: dict[str, Any] | None = None
    after_data: dict[str, Any] | None = None
    request_id: UUID
    created_at: UtcDatetime
