import http.client
import inspect
import json
import math
import threading
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from nav_msgs.msg import Odometry
from telemetry_bridge.node import (
    LatestWorker,
    QueueWorker,
    RejectRedirectHandler,
    RobotSnapshot,
    TelemetryBridge,
    encode_payload,
    is_retryable_status,
    iso_timestamp,
    load_robot_snapshots,
    telemetry_endpoint,
    yaw_from_quaternion,
)


def test_yaw_from_quaternion():
    assert abs(yaw_from_quaternion(0.0, 0.0, 0.70710678, 0.70710678) - 1.5707963) < 1e-5


def test_iso_timestamp_uses_edge_utc_time():
    assert iso_timestamp(datetime(2026, 8, 19, 5, 0, 0, 125000, UTC)) == "2026-08-19T05:00:00.125Z"


def test_payload_is_strict_json_and_validates_inputs():
    odom = Odometry()
    odom.pose.pose.orientation.w = 1.0
    payload = json.loads(
        encode_payload("AMR-01", odom, 0.5, "IDLE", datetime(2026, 8, 19, tzinfo=UTC))
    )
    assert payload["battery"] == 50.0
    odom.twist.twist.linear.x = math.nan
    with pytest.raises(ValueError, match="finite"):
        encode_payload("AMR-01", odom, 0.5, "IDLE", datetime.now(UTC))
    odom.twist.twist.linear.x = 0.0
    odom.pose.pose.orientation.w = 0.0
    with pytest.raises(ValueError, match="unit length"):
        encode_payload("AMR-01", odom, 0.5, "IDLE", datetime.now(UTC))
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        encode_payload("AMR-01", odom, 1.1, "IDLE", datetime.now(UTC))


def test_payload_includes_task_and_payload_ids():
    odom = Odometry()
    odom.pose.pose.orientation.w = 1.0
    payload = json.loads(
        encode_payload(
            "AMR-01",
            odom,
            0.5,
            "DELIVERING",
            datetime.now(UTC),
            "TASK-0001",
            "BP-0001",
        )
    )
    assert payload["task_id"] == "TASK-0001"
    assert payload["payload_id"] == "BP-0001"


def test_robot_config_creates_independent_snapshots(tmp_path):
    config = tmp_path / "robots.json"
    config.write_text(
        json.dumps(
            {
                "robots": [
                    {"robot_id": "AMR-01", "namespace": "amr_01"},
                    {"robot_id": "AMR-02", "namespace": "amr_02"},
                ]
            }
        )
    )
    snapshots = load_robot_snapshots(config)
    snapshots["AMR-01"].task_id = "TASK-1"
    assert snapshots["AMR-02"].task_id == ""


def test_payload_matches_cross_component_contract_fixture():
    odom = Odometry()
    odom.pose.pose.position.x = 1.25
    odom.pose.pose.position.y = 2.5
    odom.pose.pose.orientation.w = 1.0
    odom.twist.twist.linear.x = 0.75
    odom.twist.twist.angular.z = 0.1
    actual = json.loads(
        encode_payload("AMR-01", odom, 0.5, "IDLE", datetime(2026, 8, 19, 5, 0, 0, 125000, UTC))
    )
    expected = json.loads((Path(__file__).parent / "fixtures" / "robot_telemetry.json").read_text())
    assert actual == expected


@pytest.mark.parametrize("url", ["http://example.com", "ftp://localhost", "http://localhost?x=1"])
def test_backend_url_rejects_insecure_or_malformed_urls(url):
    with pytest.raises(ValueError):
        telemetry_endpoint(url)


def test_backend_url_allows_loopback_http_and_remote_https():
    assert (
        telemetry_endpoint("http://127.0.0.1:8000") == "http://127.0.0.1:8000/internal/v1/telemetry"
    )
    assert telemetry_endpoint("http://[::1]:8000") == "http://[::1]:8000/internal/v1/telemetry"
    assert (
        telemetry_endpoint("https://example.com/base")
        == "https://example.com/base/internal/v1/telemetry"
    )


def test_http_client_rejects_redirect_without_forwarding_secret():
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            requests.append((self.path, self.headers.get("Authorization")))
            if self.path == "/redirect":
                self.send_response(307)
                self.send_header("Location", "/destination")
            else:
                self.send_response(204)
            self.end_headers()

        def log_message(self, format, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        request = urllib.request.Request(
            f"http://127.0.0.1:{server.server_port}/redirect",
            b"{}",
            {"Authorization": "Bearer secret"},
        )
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.build_opener(RejectRedirectHandler()).open(request)
        assert error.value.code == 307
        assert requests == [("/redirect", "Bearer secret")]
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def test_retry_classification():
    assert is_retryable_status(429)
    assert is_retryable_status(500)
    assert not is_retryable_status(400)
    assert not is_retryable_status(401)
    assert not is_retryable_status(404)
    assert not is_retryable_status(409)
    assert not is_retryable_status(422)


def test_worker_keeps_only_latest_pending_payload():
    entered = threading.Event()
    release = threading.Event()
    sent = []

    def send(body):
        sent.append(body)
        if body == b"first":
            entered.set()
            release.wait(1)
        return 204

    worker = LatestWorker(send, lambda _message: None)
    worker.submit(b"first")
    assert entered.wait(1)
    worker.submit(b"second")
    worker.submit(b"latest")
    release.set()
    deadline = time.monotonic() + 1
    while sent != [b"first", b"latest"] and time.monotonic() < deadline:
        time.sleep(0.01)
    worker.close()
    assert sent == [b"first", b"latest"]


def test_queue_worker_preserves_task_lifecycle_order():
    sent = []
    worker = QueueWorker(lambda body: sent.append(body) or 204, lambda _message: None)
    for state in (b"QUEUED", b"ASSIGNED", b"COMPLETED"):
        worker.submit(state)
    deadline = time.monotonic() + 1
    while len(sent) < 3 and time.monotonic() < deadline:
        time.sleep(0.01)
    worker.close()
    assert sent == [b"QUEUED", b"ASSIGNED", b"COMPLETED"]


def test_worker_retries_5xx_but_not_permanent_4xx():
    statuses = iter((500, 204))
    calls = []
    done = threading.Event()

    def send(_body):
        calls.append(1)
        status = next(statuses)
        if status == 204:
            done.set()
        return status

    worker = LatestWorker(send, lambda _message: None)
    worker.submit(b"retry")
    assert done.wait(1)
    worker.close()
    assert len(calls) == 2

    calls.clear()
    worker = LatestWorker(lambda _body: calls.append(1) or 422, lambda _message: done.set())
    worker.submit(b"reject")
    deadline = time.monotonic() + 1
    while len(calls) < 1 and time.monotonic() < deadline:
        time.sleep(0.01)
    worker.close()
    assert len(calls) == 1


def test_new_samples_do_not_interrupt_retry_backoff():
    calls = []
    first_call = threading.Event()

    def send(body):
        calls.append((body, time.monotonic()))
        first_call.set()
        return 500

    worker = LatestWorker(send, lambda _message: None)
    worker.submit(b"first")
    assert first_call.wait(1)
    worker.submit(b"latest")
    deadline = time.monotonic() + 1
    while len(calls) < 2 and time.monotonic() < deadline:
        time.sleep(0.01)
    worker.close()

    assert len(calls) >= 2
    assert calls[1][1] - calls[0][1] >= 0.09


def test_worker_survives_malformed_http_response():
    calls = []
    delivered = threading.Event()

    def send(body):
        calls.append(body)
        if body == b"malformed":
            raise http.client.BadStatusLine("broken")
        delivered.set()
        return 204

    worker = LatestWorker(send, lambda _message: None)
    worker.submit(b"malformed")
    deadline = time.monotonic() + 2
    while len(calls) < 4 and time.monotonic() < deadline:
        time.sleep(0.01)
    worker.submit(b"healthy")
    assert delivered.wait(1)
    worker.close()
    assert calls[-1] == b"healthy"


def test_edge_secret_is_not_declared_as_a_ros_parameter():
    source = inspect.getsource(TelemetryBridge.__init__)
    assert 'declare_parameter("edge_secret"' not in source
    assert "EDGE_TELEMETRY_SHARED_SECRET" in source


def test_telemetry_waits_for_authoritative_registry_registration():
    bridge = TelemetryBridge.__new__(TelemetryBridge)
    bridge._lock = threading.Lock()
    bridge._registry_ready = False
    odom = Odometry()
    odom.pose.pose.orientation.w = 1.0
    bridge._robots = {"AMR-01": RobotSnapshot("AMR-01", "amr_01", odom=odom)}
    submitted = []

    class RecordingWorker:
        def submit(self, body):
            submitted.append(body)

    bridge._workers = {"AMR-01": RecordingWorker()}

    bridge._queue_latest()
    assert submitted == []
    assert bridge._robots["AMR-01"].odom is not None

    bridge._record_health_result(True, "")
    bridge._queue_latest()
    assert len(submitted) == 1
