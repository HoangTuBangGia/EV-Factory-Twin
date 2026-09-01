import math
import threading
from collections import deque
from dataclasses import dataclass

import rclpy
from amr_interfaces.action import ExecuteTransportTask
from amr_interfaces.msg import TaskState
from amr_interfaces.srv import CreateTransportTask
from rclpy.action import ActionClient
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy

TASK_STATUSES = {
    "QUEUED",
    "ASSIGNED",
    "PICKUP",
    "DELIVERING",
    "COMPLETED",
    "FAILED",
    "TIMED_OUT",
}
DEFAULT_NAVIGATION_TIMEOUT_SECONDS = 120.0


@dataclass
class TaskRecord:
    task_id: str
    payload_id: str
    pickup_station_id: str
    dropoff_station_id: str
    navigation_timeout_seconds: float
    max_retries: int
    status: str = "QUEUED"
    assigned_robot_id: str = ""
    attempt: int = 0
    message: str = ""


def should_retry(outcome: int, attempt: int, max_retries: int) -> bool:
    return (
        outcome
        in {
            ExecuteTransportTask.Result.FAILED,
            ExecuteTransportTask.Result.TIMED_OUT,
        }
        and attempt <= max_retries
    )


def reserve_dispatch_batch(
    queue: deque[str],
    tasks: dict[str, TaskRecord],
    active_task_ids: set[str],
    max_concurrent_tasks: int,
) -> list[TaskRecord]:
    slots = max(0, max_concurrent_tasks - len(active_task_ids))
    reserved = []
    while slots > 0 and queue:
        task = tasks[queue.popleft()]
        active_task_ids.add(task.task_id)
        task.attempt += 1
        reserved.append(task)
        slots -= 1
    return reserved


class TaskManager(Node):
    def __init__(self) -> None:
        super().__init__("task_manager")
        self._lock = threading.Lock()
        self._tasks: dict[str, TaskRecord] = {}
        self._queue: deque[str] = deque()
        self._sequence = 0
        self.declare_parameter("max_concurrent_tasks", 2)
        self.declare_parameter(
            "default_navigation_timeout_seconds", DEFAULT_NAVIGATION_TIMEOUT_SECONDS
        )
        self._max_concurrent_tasks = int(self.get_parameter("max_concurrent_tasks").value)
        self._default_navigation_timeout = float(
            self.get_parameter("default_navigation_timeout_seconds").value
        )
        if self._max_concurrent_tasks < 1:
            raise RuntimeError("max_concurrent_tasks must be positive")
        if (
            not math.isfinite(self._default_navigation_timeout)
            or self._default_navigation_timeout <= 0.0
        ):
            raise RuntimeError("default_navigation_timeout_seconds must be positive and finite")
        self._active_task_ids: set[str] = set()
        self._callback_group = ReentrantCallbackGroup()
        qos = QoSProfile(
            depth=100,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self._updates = self.create_publisher(TaskState, "/fleet/task_updates", qos)
        self._create_service = self.create_service(
            CreateTransportTask,
            "/fleet/tasks/create",
            self._create_task,
            callback_group=self._callback_group,
        )
        self._fleet_client = ActionClient(
            self,
            ExecuteTransportTask,
            "/fleet/execute_transport_task",
            callback_group=self._callback_group,
        )
        self.create_timer(0.2, self._dispatch, callback_group=self._callback_group)

    def _create_task(self, request, response):
        pickup = request.pickup_station_id or "BATTERY_BUFFER"
        dropoff = request.dropoff_station_id or "MARRIAGE_STATION"
        timeout = request.navigation_timeout_seconds or self._default_navigation_timeout
        if not math.isfinite(timeout) or timeout <= 0.0 or pickup == dropoff:
            response.accepted = False
            response.message = "invalid station or timeout"
            return response
        with self._lock:
            self._sequence += 1
            task_id = request.task_id or f"TASK-{self._sequence:04d}"
            payload_id = request.payload_id or f"BP-{self._sequence:04d}"
            if task_id in self._tasks:
                response.accepted = False
                response.task_id = task_id
                response.message = "task_id already exists"
                return response
            task = TaskRecord(
                task_id=task_id,
                payload_id=payload_id,
                pickup_station_id=pickup,
                dropoff_station_id=dropoff,
                navigation_timeout_seconds=timeout,
                max_retries=request.max_retries,
            )
            self._tasks[task_id] = task
            self._queue.append(task_id)
        self._publish(task, "task queued")
        response.accepted = True
        response.task_id = task_id
        response.message = "task accepted"
        return response

    def _dispatch(self) -> None:
        with self._lock:
            tasks = reserve_dispatch_batch(
                self._queue,
                self._tasks,
                self._active_task_ids,
                self._max_concurrent_tasks,
            )
        if not tasks:
            return
        if not self._fleet_client.wait_for_server(timeout_sec=0.0):
            with self._lock:
                for task in reversed(tasks):
                    self._active_task_ids.discard(task.task_id)
                    task.attempt -= 1
                    self._queue.appendleft(task.task_id)
            return
        for task in tasks:
            goal = ExecuteTransportTask.Goal()
            goal.task_id = task.task_id
            goal.payload_id = task.payload_id
            goal.pickup_station_id = task.pickup_station_id
            goal.dropoff_station_id = task.dropoff_station_id
            goal.navigation_timeout_seconds = task.navigation_timeout_seconds
            try:
                future = self._fleet_client.send_goal_async(
                    goal,
                    feedback_callback=lambda message, task_id=task.task_id: self._on_feedback(
                        task_id, message
                    ),
                )
            except Exception as error:
                self._finish_attempt(
                    task.task_id,
                    ExecuteTransportTask.Result.NO_ROBOT_AVAILABLE,
                    f"failed to send goal: {error}",
                )
                continue
            future.add_done_callback(
                lambda result, task_id=task.task_id: self._goal_sent(task_id, result)
            )

    def _goal_sent(self, task_id: str, future) -> None:
        try:
            goal_handle = future.result()
        except Exception as error:
            self._finish_attempt(
                task_id,
                ExecuteTransportTask.Result.NO_ROBOT_AVAILABLE,
                f"goal request failed: {error}",
            )
            return
        if goal_handle is None or not goal_handle.accepted:
            self._finish_attempt(
                task_id, ExecuteTransportTask.Result.NO_ROBOT_AVAILABLE, "goal rejected"
            )
            return
        result = goal_handle.get_result_async()
        result.add_done_callback(
            lambda completed, active_task_id=task_id: self._execution_finished(
                active_task_id, completed
            )
        )

    def _on_feedback(self, task_id: str, feedback_message) -> None:
        feedback = feedback_message.feedback
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None or feedback.status not in TASK_STATUSES:
                return
            task.status = feedback.status
            task.assigned_robot_id = feedback.assigned_robot_id
        self._publish(task, feedback.message)

    def _execution_finished(self, task_id: str, future) -> None:
        try:
            wrapped = future.result()
        except Exception as error:
            self._finish_attempt(
                task_id,
                ExecuteTransportTask.Result.FAILED,
                f"execution failed: {error}",
            )
            return
        if wrapped is None:
            self._finish_attempt(task_id, ExecuteTransportTask.Result.TIMED_OUT, "missing result")
            return
        result = wrapped.result
        with self._lock:
            task = self._tasks[task_id]
            if result.assigned_robot_id:
                task.assigned_robot_id = result.assigned_robot_id
        self._finish_attempt(task_id, result.outcome, result.message)

    def _finish_attempt(self, task_id: str, outcome: int, message: str) -> None:
        with self._lock:
            task = self._tasks[task_id]
            self._active_task_ids.discard(task_id)
            if outcome == ExecuteTransportTask.Result.SUCCESS:
                task.status = "COMPLETED"
            elif outcome == ExecuteTransportTask.Result.TIMED_OUT:
                task.status = "TIMED_OUT"
            elif outcome == ExecuteTransportTask.Result.NO_ROBOT_AVAILABLE:
                task.status = "QUEUED"
                task.attempt -= 1
                self._queue.append(task_id)
            else:
                task.status = "FAILED"
            terminal_status = task.status
        self._publish(task, message)
        if should_retry(outcome, task.attempt, task.max_retries):
            with self._lock:
                task.status = "QUEUED"
                task.message = f"retry after {terminal_status.lower()}"
                self._queue.append(task_id)
            self._publish(task, task.message)

    def _publish(self, task: TaskRecord, message: str) -> None:
        task.message = message
        update = TaskState()
        update.task_id = task.task_id
        update.payload_id = task.payload_id
        update.pickup_station_id = task.pickup_station_id
        update.dropoff_station_id = task.dropoff_station_id
        update.assigned_robot_id = task.assigned_robot_id
        update.status = task.status
        update.attempt = task.attempt
        update.max_retries = task.max_retries
        update.message = message
        update.updated_at = self.get_clock().now().to_msg()
        self._updates.publish(update)


def main() -> None:
    rclpy.init()
    node = TaskManager()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
