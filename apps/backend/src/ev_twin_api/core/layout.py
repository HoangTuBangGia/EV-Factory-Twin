from ev_twin_api.schemas.factory import Station

FACTORY_WIDTH_M = 20.0
FACTORY_HEIGHT_M = 15.0

STATIONS: tuple[Station, ...] = (
    Station(id="BATTERY_BUFFER", name="Battery Buffer", type="BUFFER", x=2, y=4),
    Station(id="INTERSECTION_A", name="Intersection A", type="WAYPOINT", x=8, y=4),
    Station(id="INTERSECTION_B", name="Intersection B", type="WAYPOINT", x=12, y=8),
    Station(id="MARRIAGE_STATION", name="Marriage Station", type="MARRIAGE", x=16, y=8),
    Station(id="CHARGING_STATION", name="Charging Station", type="CHARGER", x=2, y=12),
    Station(id="IDLE_ZONE", name="Idle Zone", type="IDLE", x=5, y=12),
)

IDLE_ZONE_X = 5.0
IDLE_ZONE_Y = 12.0
ROBOT_SPAWN_SPACING_M = 1.0
