from .models.layout import LayoutVersionContent

DEFAULT_LAYOUT_ID = "LAYOUT-DEFAULT"
DEFAULT_LAYOUT_VERSION = 3
DEFAULT_ROUTE_ID = "BATTERY_DELIVERY"


def default_layout_content() -> LayoutVersionContent:
    """Return the canonical 120 × 40 m battery-intralogistics layout."""

    return LayoutVersionContent.model_validate(
        {
            "width": 120,
            "height": 40,
            "stations": [
                {
                    "id": "BATTERY_BUFFER",
                    "type": "BATTERY_BUFFER",
                    "x": 32,
                    "y": 29,
                },
                {
                    "id": "MARRIAGE_STATION",
                    "type": "MARRIAGE_STATION",
                    "x": 52,
                    "y": 6,
                },
                {
                    "id": "MARRIAGE_STATION_2",
                    "type": "MARRIAGE_STATION",
                    "x": 82,
                    "y": 8,
                },
                {
                    "id": "CHARGING_STATION",
                    "type": "CHARGING_STATION",
                    "x": 32,
                    "y": 11,
                },
            ],
            "routes": [
                {
                    "id": DEFAULT_ROUTE_ID,
                    "kind": "DELIVERY",
                    "start_station_id": "BATTERY_BUFFER",
                    "end_station_id": "MARRIAGE_STATION",
                    "waypoints": [
                        {"x": 32, "y": 29},
                        {"x": 32, "y": 20},
                        {"x": 40, "y": 20},
                        {"x": 52, "y": 20},
                        {"x": 52, "y": 6},
                    ],
                },
                {
                    "id": "BATTERY_DELIVERY_LONG",
                    "kind": "DELIVERY",
                    "start_station_id": "BATTERY_BUFFER",
                    "end_station_id": "MARRIAGE_STATION_2",
                    "waypoints": [
                        {"x": 32, "y": 29},
                        {"x": 32, "y": 20},
                        {"x": 40, "y": 20},
                        {"x": 60, "y": 20},
                        {"x": 82, "y": 20},
                        {"x": 82, "y": 8},
                    ],
                },
                {
                    "id": "CHARGER_LINK",
                    "kind": "SUPPORT",
                    "start_station_id": "CHARGING_STATION",
                    "end_station_id": "BATTERY_BUFFER",
                    "waypoints": [
                        {"x": 32, "y": 11},
                        {"x": 32, "y": 20},
                        {"x": 32, "y": 29},
                    ],
                },
            ],
            "no_go_zones": [
                {
                    "id": "GIGA_PRESS_CLEARANCE",
                    "points": [
                        {"x": 44, "y": 27},
                        {"x": 58, "y": 27},
                        {"x": 58, "y": 37},
                        {"x": 44, "y": 37},
                    ],
                }
            ],
            "congestion_zones": [
                {
                    "id": "WAREHOUSE_PRODUCTION_DOOR",
                    "delay_multiplier": 1.25,
                    "points": [
                        {"x": 38, "y": 17.5},
                        {"x": 42, "y": 17.5},
                        {"x": 42, "y": 22.5},
                        {"x": 38, "y": 22.5},
                    ],
                }
            ],
            "config": {
                "robot_count": 2,
                "demand_interval_seconds": 8,
                "robot_speed_mps": 1.2,
                "charger_count": 2,
            },
        }
    )
