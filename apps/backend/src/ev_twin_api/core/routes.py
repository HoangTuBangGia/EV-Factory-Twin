CHARGER_ROUTE_KEY: tuple[str, str] = ("ANY", "CHARGING_STATION")

ROUTES: dict[tuple[str, str], tuple[tuple[float, float], ...]] = {
    ("BATTERY_BUFFER", "MARRIAGE_STATION"): (
        (2.0, 4.0),
        (8.0, 4.0),
        (12.0, 8.0),
        (16.0, 8.0),
    ),
    # Single-waypoint route: a straight line from wherever the robot
    # currently is to the Charging Station, reusing the same
    # advance_along_route mechanism as the pickup approach leg.
    CHARGER_ROUTE_KEY: ((2.0, 12.0),),
}
