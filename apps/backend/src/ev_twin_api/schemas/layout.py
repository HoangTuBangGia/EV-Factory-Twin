from typing import Annotated

from pydantic import BaseModel, StringConstraints
from twin_core.models.layout import LayoutSummary, LayoutVersion, LayoutVersionContent

LayoutName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class CreateLayoutRequest(BaseModel):
    name: LayoutName
    content: LayoutVersionContent


class CreateLayoutVersionRequest(BaseModel):
    content: LayoutVersionContent


class UpdateLayoutRequest(BaseModel):
    name: LayoutName


__all__ = [
    "CreateLayoutRequest",
    "CreateLayoutVersionRequest",
    "LayoutSummary",
    "LayoutVersion",
    "UpdateLayoutRequest",
]
