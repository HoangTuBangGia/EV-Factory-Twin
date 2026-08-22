from datetime import UTC, datetime
from uuid import uuid4

from ev_twin_api.schemas.alert import AlertCode, AlertSeverity, FactoryAlert


def test_alert_severity_values() -> None:
    assert {severity.value for severity in AlertSeverity} == {"INFO", "WARNING", "CRITICAL"}


def test_alert_code_values() -> None:
    assert {code.value for code in AlertCode} == {
        "LOW_BATTERY",
        "ROBOT_WAITING",
        "TASK_BACKLOG",
        "STARVATION",
        "ROBOT_ERROR",
        "STALE_TELEMETRY",
        "BRIDGE_DISCONNECTED",
        "COMMAND_TIMEOUT",
        "CONGESTION",
    }


def test_factory_alert_robot_and_task_default_to_none() -> None:
    alert = FactoryAlert(
        id=uuid4(),
        dedupe_key="LOW_BATTERY:AMR-01",
        severity=AlertSeverity.WARNING,
        code=AlertCode.LOW_BATTERY,
        message="AMR-01 battery below threshold",
        timestamp=datetime.now(UTC),
    )
    assert alert.robot_id is None
    assert alert.task_id is None
