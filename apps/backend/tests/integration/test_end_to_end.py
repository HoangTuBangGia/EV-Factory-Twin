from ev_twin_api.main import app
from ev_twin_api.schemas.metrics import FactoryMetrics
from ev_twin_api.schemas.task import Task
from ev_twin_api.schemas.telemetry import RobotTelemetry
from fastapi.testclient import TestClient


def test_mock_engine_end_to_end_task_delivery() -> None:
    """Guide BE-11 scenario, exercised through the real app/REST/WebSocket
    together (not a standalone engine instance, unlike the "through the real
    engine" tests in tests/services/test_mock_factory.py):

    mock starts -> task created -> AMR assigned -> AMR moves ->
    telemetry broadcast -> delivery completes -> metrics change
    """
    with TestClient(app) as client:
        mock_factory = app.state.mock_factory
        assert mock_factory.running is True  # mock starts

        mock_factory.config.task_interval_seconds = 1.0
        mock_factory.config.simulation_speed = 10.0
        mock_factory.config.robot_speed_mps = 3.0

        seen_queued = False
        assigned_robot_id: str | None = None
        positions: list[tuple[float, float]] = []
        seen_completed = False
        seen_metrics_change = False

        with client.websocket_connect("/ws/factory") as websocket:
            for _ in range(3000):
                message = websocket.receive_json()

                if message["type"] == "task.updated":
                    task = Task.model_validate(message["data"])
                    if task.status == "QUEUED":
                        seen_queued = True  # task created
                    elif task.status == "ASSIGNED" and assigned_robot_id is None:
                        assigned_robot_id = task.assigned_robot_id  # AMR assigned
                    elif task.status == "COMPLETED" and task.assigned_robot_id == assigned_robot_id:
                        seen_completed = True  # delivery completes

                elif message["type"] == "robot.telemetry" and assigned_robot_id is not None:
                    # telemetry broadcast
                    telemetry = RobotTelemetry.model_validate(message["data"])
                    if telemetry.robot_id == assigned_robot_id:
                        positions.append((telemetry.pose.x, telemetry.pose.y))

                elif message["type"] == "metrics.updated":
                    metrics = FactoryMetrics.model_validate(message["data"])
                    if metrics.completed_tasks >= 1:
                        seen_metrics_change = True  # metrics change

                if seen_queued and seen_completed and seen_metrics_change:
                    break

        assert seen_queued, "task.updated with QUEUED status was never observed"
        assert assigned_robot_id is not None, "task.updated with ASSIGNED status was never observed"
        assert len(positions) >= 2, "robot.telemetry for the assigned AMR was never observed"
        assert positions[0] != positions[-1], "assigned AMR's position never changed"  # AMR moves
        assert seen_completed, "task.updated with COMPLETED status was never observed"
        assert seen_metrics_change, "metrics.updated never reflected the completed task"

        # cross-check against REST after the WS-observed flow, confirming the
        # engine, REST layer, and WebSocket broadcast all agree on the outcome
        tasks_response = client.get("/api/v1/tasks")
        assert tasks_response.status_code == 200
        completed_tasks = [
            Task.model_validate(item)
            for item in tasks_response.json()
            if item["status"] == "COMPLETED"
        ]
        assert len(completed_tasks) >= 1
        assert any(task.assigned_robot_id == assigned_robot_id for task in completed_tasks)

        metrics_response = client.get("/api/v1/metrics")
        assert metrics_response.status_code == 200
        rest_metrics = FactoryMetrics.model_validate(metrics_response.json())
        assert rest_metrics.completed_tasks >= 1
