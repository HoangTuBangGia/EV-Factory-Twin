from datetime import UTC, datetime
from typing import Annotated

from pydantic import PlainSerializer


def serialize_utc_z(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


UtcDatetime = Annotated[
    datetime, PlainSerializer(serialize_utc_z, return_type=str, when_used="json")
]
