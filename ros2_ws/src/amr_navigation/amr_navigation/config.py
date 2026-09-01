import heapq
import json
import math
from dataclasses import dataclass
from pathlib import Path

Point = tuple[float, float]


@dataclass(frozen=True)
class Station:
    station_id: str
    station_type: str
    position: Point
    arrival_status: str


@dataclass(frozen=True)
class Route:
    route_id: str
    start_station_id: str
    end_station_id: str
    waypoints: tuple[Point, ...]


@dataclass(frozen=True)
class NavigationConfig:
    layout_id: str
    layout_version: int
    width: float
    height: float
    stations: dict[str, Station]
    routes: dict[str, Route]
    no_go_zones: tuple[tuple[Point, ...], ...]

    def station_positions(self) -> dict[str, Point]:
        return {station_id: station.position for station_id, station in self.stations.items()}

    def route_for(self, start_station_id: str, end_station_id: str) -> str:
        for route in self.routes.values():
            if (
                route.start_station_id == start_station_id
                and route.end_station_id == end_station_id
            ):
                return route.route_id
        return ""

    def path_to(self, origin: Point, station_id: str, route_id: str = "") -> tuple[Point, ...]:
        if station_id not in self.stations:
            raise ValueError(f"unknown station: {station_id}")
        if route_id:
            route = self.routes.get(route_id)
            if route is None:
                raise ValueError(f"unknown route: {route_id}")
            if station_id == route.end_station_id:
                path = route.waypoints
            elif station_id == route.start_station_id:
                path = tuple(reversed(route.waypoints))
            else:
                raise ValueError(f"route {route_id} does not serve station {station_id}")
        else:
            origin_station = min(
                self.stations.values(),
                key=lambda station: (
                    math.hypot(origin[0] - station.position[0], origin[1] - station.position[1]),
                    station.station_id,
                ),
            )
            path = self._network_path(origin_station.station_id, station_id)

        path = _deduplicate_path((*path, self.stations[station_id].position))
        self._validate_path((origin, *path), "runtime path")
        return path

    def _network_path(self, start_station_id: str, end_station_id: str) -> tuple[Point, ...]:
        if start_station_id == end_station_id:
            return (self.stations[end_station_id].position,)
        graph: dict[str, list[tuple[float, str, tuple[Point, ...]]]] = {
            station_id: [] for station_id in self.stations
        }
        for route in self.routes.values():
            distance = _path_length(route.waypoints)
            graph[route.start_station_id].append(
                (distance, route.end_station_id, route.waypoints)
            )
            graph[route.end_station_id].append(
                (distance, route.start_station_id, tuple(reversed(route.waypoints)))
            )

        queue: list[tuple[float, str, tuple[Point, ...]]] = [(0.0, start_station_id, ())]
        best = {start_station_id: 0.0}
        while queue:
            distance, station_id, path = heapq.heappop(queue)
            if distance > best[station_id]:
                continue
            if station_id == end_station_id:
                return _deduplicate_path(path)
            for edge_distance, neighbor, edge_path in graph[station_id]:
                candidate = distance + edge_distance
                if candidate >= best.get(neighbor, math.inf):
                    continue
                best[neighbor] = candidate
                heapq.heappush(queue, (candidate, neighbor, (*path, *edge_path)))
        raise ValueError(f"no configured route from {start_station_id} to {end_station_id}")

    def _validate_path(self, path: tuple[Point, ...], label: str) -> None:
        for start, end in zip(path, path[1:], strict=False):
            if any(
                _segment_intersects_polygon(start, end, polygon)
                for polygon in self.no_go_zones
            ):
                raise ValueError(f"{label} crosses a no-go zone")


def _number(value, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be numeric")
    if not math.isfinite(value):
        raise ValueError(f"{label} must be finite")
    return float(value)


def _point(value, label: str) -> Point:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return _number(value.get("x"), f"{label}.x"), _number(value.get("y"), f"{label}.y")


def _status_for(station_type: str, explicit_status) -> str:
    statuses = {
        "BATTERY_BUFFER": "PICKING",
        "CHARGING_STATION": "CHARGING",
    }
    status = statuses.get(station_type, "IDLE") if explicit_status is None else explicit_status
    if status not in {"IDLE", "PICKING", "CHARGING"}:
        raise ValueError("station arrival_status must be IDLE, PICKING, or CHARGING")
    return status


def load_navigation_config(path: str | Path) -> NavigationConfig:
    with Path(path).open(encoding="utf-8") as config_file:
        document = json.load(config_file)
    if not isinstance(document, dict):
        raise ValueError("navigation config must be an object")

    width = _number(document.get("width", 120.0), "width")
    height = _number(document.get("height", 40.0), "height")
    if width <= 0.0 or height <= 0.0:
        raise ValueError("width and height must be positive")
    source = document.get("stations")
    if not isinstance(source, dict) or not source:
        raise ValueError("stations config must contain a non-empty stations object")
    stations: dict[str, Station] = {}
    for station_id, station_value in source.items():
        if not isinstance(station_id, str) or not station_id:
            raise ValueError("station IDs must be non-empty strings")
        position = _point(station_value, f"station {station_id}")
        if not 0.0 <= position[0] <= width or not 0.0 <= position[1] <= height:
            raise ValueError(f"station {station_id} must be inside the layout")
        station_type = station_value.get("type", "WAYPOINT")
        if not isinstance(station_type, str) or not station_type:
            raise ValueError(f"station {station_id}.type must be a non-empty string")
        stations[station_id] = Station(
            station_id,
            station_type,
            position,
            _status_for(station_type, station_value.get("arrival_status")),
        )

    zone_values = document.get("no_go_zones", [])
    if not isinstance(zone_values, list):
        raise ValueError("no_go_zones must be an array")
    zones = []
    zone_ids: set[str] = set()
    for index, zone in enumerate(zone_values):
        if not isinstance(zone, dict):
            raise ValueError(f"no_go_zones[{index}] must be an object")
        zone_id = zone.get("id")
        if not isinstance(zone_id, str) or not zone_id or zone_id in zone_ids:
            raise ValueError("no-go zone IDs must be non-empty and unique")
        points = zone.get("points")
        if not isinstance(points, list) or len(points) < 3:
            raise ValueError(f"no-go zone {zone_id} must have at least three points")
        polygon = tuple(_point(point, f"no-go zone {zone_id}") for point in points)
        if any(not 0.0 <= x <= width or not 0.0 <= y <= height for x, y in polygon):
            raise ValueError(f"no-go zone {zone_id} must be inside the layout")
        zones.append(polygon)
        zone_ids.add(zone_id)
    for station in stations.values():
        if any(_point_in_polygon(station.position, polygon) for polygon in zones):
            raise ValueError(f"station {station.station_id} is inside a no-go zone")

    route_values = document.get("routes", [])
    if not isinstance(route_values, list):
        raise ValueError("routes must be an array")
    routes: dict[str, Route] = {}
    for index, route_value in enumerate(route_values):
        if not isinstance(route_value, dict):
            raise ValueError(f"routes[{index}] must be an object")
        route_id = route_value.get("id")
        start = route_value.get("start_station_id")
        end = route_value.get("end_station_id")
        if not isinstance(route_id, str) or not route_id or route_id in routes:
            raise ValueError("route IDs must be non-empty and unique")
        if start not in stations or end not in stations or start == end:
            raise ValueError(f"route {route_id} must connect two configured stations")
        waypoint_values = route_value.get("waypoints")
        if not isinstance(waypoint_values, list) or len(waypoint_values) < 2:
            raise ValueError(f"route {route_id} must have at least two waypoints")
        waypoints = tuple(
            _point(point, f"route {route_id} waypoint") for point in waypoint_values
        )
        if any(not 0.0 <= x <= width or not 0.0 <= y <= height for x, y in waypoints):
            raise ValueError(f"route {route_id} must stay inside the layout")
        if (
            waypoints[0] != stations[start].position
            or waypoints[-1] != stations[end].position
        ):
            raise ValueError(f"route {route_id} endpoints must match its stations")
        route = Route(route_id, start, end, waypoints)
        config_for_validation = NavigationConfig("", 1, width, height, stations, {}, tuple(zones))
        config_for_validation._validate_path(waypoints, f"route {route_id}")
        routes[route_id] = route

    layout_id = document.get("layout_id", "LAYOUT-DEFAULT")
    layout_version = document.get("layout_version", 3)
    if not isinstance(layout_id, str) or not layout_id:
        raise ValueError("layout_id must be a non-empty string")
    if (
        isinstance(layout_version, bool)
        or not isinstance(layout_version, int)
        or layout_version < 1
    ):
        raise ValueError("layout_version must be a positive integer")
    return NavigationConfig(
        layout_id, layout_version, width, height, stations, routes, tuple(zones)
    )


def load_stations(path: str | Path) -> dict[str, Point]:
    return load_navigation_config(path).station_positions()


def _deduplicate_path(path: tuple[Point, ...]) -> tuple[Point, ...]:
    return tuple(
        point
        for index, point in enumerate(path)
        if index == 0 or point != path[index - 1]
    )


def _path_length(path: tuple[Point, ...]) -> float:
    return sum(
        math.hypot(end[0] - start[0], end[1] - start[1])
        for start, end in zip(path, path[1:], strict=False)
    )


def _orientation(a: Point, b: Point, c: Point) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _on_segment(a: Point, b: Point, point: Point) -> bool:
    return (
        min(a[0], b[0]) <= point[0] <= max(a[0], b[0])
        and min(a[1], b[1]) <= point[1] <= max(a[1], b[1])
    )


def _segments_intersect(a: Point, b: Point, c: Point, d: Point) -> bool:
    values = (
        _orientation(a, b, c),
        _orientation(a, b, d),
        _orientation(c, d, a),
        _orientation(c, d, b),
    )
    if values[0] * values[1] < 0.0 and values[2] * values[3] < 0.0:
        return True
    return any(
        math.isclose(value, 0.0, abs_tol=1e-9) and _on_segment(start, end, point)
        for value, start, end, point in (
            (values[0], a, b, c),
            (values[1], a, b, d),
            (values[2], c, d, a),
            (values[3], c, d, b),
        )
    )


def _point_in_polygon(point: Point, polygon: tuple[Point, ...]) -> bool:
    inside = False
    previous = polygon[-1]
    for current in polygon:
        if ((current[1] > point[1]) != (previous[1] > point[1])) and point[0] < (
            (previous[0] - current[0]) * (point[1] - current[1])
            / (previous[1] - current[1])
            + current[0]
        ):
            inside = not inside
        previous = current
    return inside


def _segment_intersects_polygon(start: Point, end: Point, polygon: tuple[Point, ...]) -> bool:
    if _point_in_polygon(start, polygon) or _point_in_polygon(end, polygon):
        return True
    return any(
        _segments_intersect(start, end, edge_start, edge_end)
        for edge_start, edge_end in zip(
            polygon, (*polygon[1:], polygon[0]), strict=True
        )
    )
