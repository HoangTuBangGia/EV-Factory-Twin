from __future__ import annotations

import heapq
import math

from twin_core.models.layout import LayoutVersionContent, Point

Node = tuple[float, float]


def shortest_station_path(
    layout: LayoutVersionContent,
    start_station_id: str,
    end_station_id: str,
) -> tuple[Node, ...]:
    """Return the shortest path along the explicitly drawn route network.

    Routes are treated as bidirectional for the mock twin. Two routes connect
    only when they share an exact waypoint, keeping navigation constrained to
    geometry approved in the layout editor.
    """

    stations = {station.id: station for station in layout.stations}
    try:
        start = _node(stations[start_station_id])
        end = _node(stations[end_station_id])
    except KeyError as error:
        raise ValueError(f"Unknown station: {error.args[0]}") from error
    if start == end:
        return (start,)

    graph: dict[Node, list[tuple[float, Node]]] = {}
    for route in layout.routes:
        for left, right in zip(route.waypoints, route.waypoints[1:], strict=False):
            a, b = _node(left), _node(right)
            distance = math.dist(a, b)
            graph.setdefault(a, []).append((distance, b))
            graph.setdefault(b, []).append((distance, a))

    distances = {start: 0.0}
    previous: dict[Node, Node] = {}
    queue = [(0.0, start)]
    while queue:
        distance, node = heapq.heappop(queue)
        if distance != distances.get(node):
            continue
        if node == end:
            break
        for edge_distance, neighbour in graph.get(node, []):
            candidate = distance + edge_distance
            if candidate < distances.get(neighbour, math.inf):
                distances[neighbour] = candidate
                previous[neighbour] = node
                heapq.heappush(queue, (candidate, neighbour))

    if end not in distances:
        raise ValueError(f"No route-network path from '{start_station_id}' to '{end_station_id}'")

    path = [end]
    while path[-1] != start:
        path.append(previous[path[-1]])
    return tuple(reversed(path))


def _node(point: Point) -> Node:
    return (point.x, point.y)
