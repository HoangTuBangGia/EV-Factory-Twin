from twin_core.models.telemetry import RobotTelemetry

from ev_twin_api.schemas.robot import Robot

__all__ = ["RobotTelemetry", "robot_to_telemetry"]


def robot_to_telemetry(robot: Robot) -> RobotTelemetry:
    return RobotTelemetry(
        timestamp=robot.last_seen_at,
        robot_id=robot.id,
        pose=robot.pose,
        velocity=robot.velocity,
        battery=robot.battery,
        status=robot.status,
        task_id=robot.task_id,
        payload_id=robot.payload_id,
    )
