from __future__ import annotations

import math
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from twin_core.models.telemetry import UtcDatetime

EPSILON = 1e-9


class StationType(StrEnum):
    BATTERY_BUFFER = "BATTERY_BUFFER"
    MARRIAGE_STATION = "MARRIAGE_STATION"
    CHARGING_STATION = "CHARGING_STATION"


class Point(BaseModel):
    model_config = ConfigDict(frozen=True)

    x: float
    y: float

    @model_validator(mode="after")
    def finite(self) -> Point:
        if not math.isfinite(self.x) or not math.isfinite(self.y):
            raise ValueError("coordinates must be finite")
        return self


class LayoutStation(Point):
    id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Z][A-Z0-9_-]*$")
    type: StationType


class LayoutRoute(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Z][A-Z0-9_-]*$")
    start_station_id: str = Field(min_length=1, max_length=80)
    end_station_id: str = Field(min_length=1, max_length=80)
    waypoints: list[Point] = Field(min_length=2, max_length=200)


class PolygonZone(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Z][A-Z0-9_-]*$")
    points: list[Point] = Field(min_length=3, max_length=100)


class CongestionZone(PolygonZone):
    delay_multiplier: float = Field(ge=1.0, le=10.0)


class LayoutRuntimeConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    robot_count: int = Field(default=2, ge=2, le=50)
    demand_interval_seconds: float = Field(default=8.0, ge=0.1, le=3600.0)
    robot_speed_mps: float = Field(default=1.0, gt=0.0, le=10.0)
    charger_count: int = Field(default=1, ge=1, le=20)


def _orientation(a: Point, b: Point, c: Point) -> float:
    return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)


def _on_segment(a: Point, b: Point, point: Point) -> bool:
    return (
        abs(_orientation(a, b, point)) <= EPSILON
        and min(a.x, b.x) - EPSILON <= point.x <= max(a.x, b.x) + EPSILON
        and min(a.y, b.y) - EPSILON <= point.y <= max(a.y, b.y) + EPSILON
    )


def _same_point(a: Point, b: Point) -> bool:
    return abs(a.x - b.x) <= EPSILON and abs(a.y - b.y) <= EPSILON


def segments_intersect(a: Point, b: Point, c: Point, d: Point) -> bool:
    orientations = (
        _orientation(a, b, c),
        _orientation(a, b, d),
        _orientation(c, d, a),
        _orientation(c, d, b),
    )
    if (
        orientations[0] * orientations[1] < -EPSILON
        and orientations[2] * orientations[3] < -EPSILON
    ):
        return True
    return any(
        abs(value) <= EPSILON and _on_segment(start, end, point)
        for value, start, end, point in (
            (orientations[0], a, b, c),
            (orientations[1], a, b, d),
            (orientations[2], c, d, a),
            (orientations[3], c, d, b),
        )
    )


def point_in_polygon(point: Point, polygon: list[Point]) -> bool:
    inside = False
    previous = polygon[-1]
    for current in polygon:
        if _on_segment(previous, current, point):
            return True
        crosses = (current.y > point.y) != (previous.y > point.y)
        if crosses:
            x_at_y = (previous.x - current.x) * (point.y - current.y) / (
                previous.y - current.y
            ) + current.x
            if point.x < x_at_y:
                inside = not inside
        previous = current
    return inside


def _validate_polygon(zone: PolygonZone) -> None:
    points = zone.points
    area_twice = sum(
        point.x * points[(index + 1) % len(points)].y
        - points[(index + 1) % len(points)].x * point.y
        for index, point in enumerate(points)
    )
    if abs(area_twice) <= EPSILON:
        raise ValueError(f"zone '{zone.id}' polygon has zero area")
    edges = [(points[index], points[(index + 1) % len(points)]) for index in range(len(points))]
    for left_index, (a, b) in enumerate(edges):
        if a == b:
            raise ValueError(f"zone '{zone.id}' has a zero-length edge")
        for right_index, (c, d) in enumerate(edges[left_index + 1 :], left_index + 1):
            adjacent = right_index == left_index + 1 or (
                left_index == 0 and right_index == len(edges) - 1
            )
            if not adjacent and segments_intersect(a, b, c, d):
                raise ValueError(f"zone '{zone.id}' polygon self-intersects")


class LayoutVersionContent(BaseModel):
    model_config = ConfigDict(frozen=True)

    width: float = Field(gt=0.0, le=10_000.0)
    height: float = Field(gt=0.0, le=10_000.0)
    stations: list[LayoutStation] = Field(min_length=3, max_length=200)
    routes: list[LayoutRoute] = Field(min_length=1, max_length=200)
    no_go_zones: list[PolygonZone] = Field(default_factory=list, max_length=100)
    congestion_zones: list[CongestionZone] = Field(default_factory=list, max_length=100)
    config: LayoutRuntimeConfig = Field(default_factory=LayoutRuntimeConfig)

    @model_validator(mode="after")
    def validate_geometry(self) -> LayoutVersionContent:
        all_points = [
            *self.stations,
            *(point for route in self.routes for point in route.waypoints),
            *(
                point
                for zone in [*self.no_go_zones, *self.congestion_zones]
                for point in zone.points
            ),
        ]
        if any(
            point.x < 0.0 or point.x > self.width or point.y < 0.0 or point.y > self.height
            for point in all_points
        ):
            raise ValueError("layout points must be inside the factory footprint")

        station_ids = [station.id for station in self.stations]
        route_ids = [route.id for route in self.routes]
        zone_ids = [zone.id for zone in [*self.no_go_zones, *self.congestion_zones]]
        for label, identifiers in (
            ("station", station_ids),
            ("route", route_ids),
            ("zone", zone_ids),
        ):
            if len(identifiers) != len(set(identifiers)):
                raise ValueError(f"{label} IDs must be unique")

        present_types = {station.type for station in self.stations}
        missing_types = set(StationType) - present_types
        if missing_types:
            raise ValueError(f"missing required station types: {sorted(missing_types)}")

        stations = {station.id: station for station in self.stations}
        for zone in [*self.no_go_zones, *self.congestion_zones]:
            _validate_polygon(zone)
        for station in self.stations:
            if any(point_in_polygon(station, zone.points) for zone in self.no_go_zones):
                raise ValueError(f"station '{station.id}' is inside a no-go zone")

        for route in self.routes:
            if route.start_station_id not in stations or route.end_station_id not in stations:
                raise ValueError(f"route '{route.id}' references an unknown station")
            if route.start_station_id == route.end_station_id:
                raise ValueError(f"route '{route.id}' endpoints must be different stations")
            if not _same_point(route.waypoints[0], stations[route.start_station_id]):
                raise ValueError(f"route '{route.id}' must start at its start station")
            if not _same_point(route.waypoints[-1], stations[route.end_station_id]):
                raise ValueError(f"route '{route.id}' must end at its end station")
            for a, b in zip(route.waypoints, route.waypoints[1:], strict=False):
                if a == b:
                    raise ValueError(f"route '{route.id}' has duplicate consecutive waypoints")
                for zone in self.no_go_zones:
                    if point_in_polygon(a, zone.points) or point_in_polygon(b, zone.points):
                        raise ValueError(f"route '{route.id}' enters no-go zone '{zone.id}'")
                    edges = list(zip(zone.points, [*zone.points[1:], zone.points[0]], strict=True))
                    if any(segments_intersect(a, b, c, d) for c, d in edges):
                        raise ValueError(f"route '{route.id}' crosses no-go zone '{zone.id}'")
        return self


class LayoutVersion(LayoutVersionContent):
    layout_id: str
    name: str
    version: int = Field(ge=1)
    created_by: UUID
    created_at: UtcDatetime
    archived_at: UtcDatetime | None = None


class LayoutSummary(BaseModel):
    id: str
    name: str
    latest_version: int = Field(ge=1)
    created_by: UUID
    created_at: UtcDatetime
    archived_at: UtcDatetime | None = None
