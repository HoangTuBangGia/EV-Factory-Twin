from datetime import UTC, datetime
from uuid import UUID

from ev_sim.layout import route_profile
from twin_core.default_layout import default_layout_content
from twin_core.models.layout import LayoutVersion


def _layout(**content_updates: object) -> LayoutVersion:
    content = default_layout_content().model_copy(update=content_updates)
    return LayoutVersion(
        layout_id="LAYOUT-TEST",
        name="Layout test",
        version=1,
        created_by=UUID("00000000-0000-4000-8000-000000000001"),
        created_at=datetime.now(UTC),
        **content.model_dump(),
    )


def test_route_geometry_and_congestion_change_simulation_profile() -> None:
    baseline = _layout()
    route = baseline.routes[0]
    longer_route = route.model_copy(
        update={
            "waypoints": [
                route.waypoints[0],
                route.waypoints[0].model_copy(update={"x": 20.0, "y": 20.0}),
                *route.waypoints[1:],
            ]
        }
    )

    baseline_profile = route_profile(baseline, route.id)
    candidate_profile = route_profile(_layout(routes=[longer_route]), route.id)

    assert candidate_profile.distance_m > baseline_profile.distance_m
    assert baseline_profile.congestion_multiplier > 1.0
