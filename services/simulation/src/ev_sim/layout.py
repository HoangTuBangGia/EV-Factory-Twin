import math
from dataclasses import dataclass

from twin_core.models.layout import LayoutVersion, Point, point_in_polygon


@dataclass(frozen=True)
class RouteProfile:
    route_id: str
    distance_m: float
    congestion_multiplier: float


def route_profile(layout: LayoutVersion, route_id: str) -> RouteProfile:
    route = next((candidate for candidate in layout.routes if candidate.id == route_id), None)
    if route is None:
        raise ValueError(f"Route '{route_id}' not found in layout '{layout.layout_id}'")
    distance = sum(
        math.hypot(b.x - a.x, b.y - a.y)
        for a, b in zip(route.waypoints, route.waypoints[1:], strict=False)
    )
    if distance <= 0.0:
        raise ValueError(f"Route '{route_id}' has zero distance")
    weighted = sum(
        _segment_congestion(a, b, layout)
        for a, b in zip(route.waypoints, route.waypoints[1:], strict=False)
    )
    return RouteProfile(route.id, distance, weighted / distance)


def _segment_congestion(a: Point, b: Point, layout: LayoutVersion) -> float:
    length = math.hypot(b.x - a.x, b.y - a.y)
    # ponytail: 0.25 m midpoint sampling is deterministic and bounded for MVP;
    # replace with exact polygon clipping if sub-centimetre planning is required.
    sample_count = max(1, math.ceil(length / 0.25))
    weighted = 0.0
    for index in range(sample_count):
        ratio = (index + 0.5) / sample_count
        point = Point(x=a.x + (b.x - a.x) * ratio, y=a.y + (b.y - a.y) * ratio)
        multiplier = max(
            (
                zone.delay_multiplier
                for zone in layout.congestion_zones
                if point_in_polygon(point, zone.points)
            ),
            default=1.0,
        )
        weighted += length / sample_count * multiplier
    return weighted
