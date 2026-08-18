#!/usr/bin/env python3
"""Smoke-test the complete MVP scenario workflow against a running backend."""

import argparse
import json
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def request_json(
    api_url: str,
    method: str,
    path: str,
    payload: dict[str, object] | None = None,
    expected_status: int = 200,
    access_token: str | None = None,
) -> object:
    body = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"} if body is not None else {}
    if access_token is not None:
        headers["Authorization"] = f"Bearer {access_token}"
    request = Request(f"{api_url}{path}", data=body, headers=headers, method=method)

    try:
        with urlopen(request, timeout=15) as response:  # noqa: S310 - URL is operator-supplied
            status = response.status
            response_body = response.read()
    except HTTPError as error:
        status = error.code
        response_body = error.read()

    parsed = json.loads(response_body) if response_body else None
    if status != expected_status:
        raise RuntimeError(f"{method} {path}: expected {expected_status}, got {status}: {parsed}")
    return parsed


def require_dict(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} did not return a JSON object")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    api_url = args.api_url.rstrip("/")
    designer_token = os.getenv("DESIGNER_ACCESS_TOKEN")
    monitor_token = os.getenv("MONITOR_ACCESS_TOKEN")
    if not designer_token or not monitor_token:
        raise RuntimeError(
            "Set DESIGNER_ACCESS_TOKEN and MONITOR_ACCESS_TOKEN before running the smoke test"
        )

    health = require_dict(request_json(api_url, "GET", "/health"), "health")
    baseline = require_dict(
        request_json(
            api_url,
            "GET",
            "/api/v1/scenarios/baseline",
            access_token=designer_token,
        ),
        "baseline",
    )
    scenario_payload = {
        "name": "mvp-smoke",
        "num_robots": 4,
        "num_tasks": 500,
        "task_arrival_interval": 6,
        "travel_time": 30,
        "loading_time": 10,
        "simulation_time": 3600,
    }

    request_json(
        api_url,
        "POST",
        "/api/v1/scenarios/run",
        scenario_payload,
        expected_status=403,
        access_token=monitor_token,
    )
    candidate = require_dict(
        request_json(
            api_url,
            "POST",
            "/api/v1/scenarios/run",
            scenario_payload,
            access_token=designer_token,
        ),
        "candidate",
    )
    scenario_id = candidate.get("id")
    if not isinstance(scenario_id, str):
        raise RuntimeError("run response has no scenario id")

    request_json(
        api_url,
        "POST",
        f"/api/v1/scenarios/{scenario_id}/apply",
        expected_status=403,
        access_token=designer_token,
    )
    request_json(
        api_url,
        "POST",
        f"/api/v1/scenarios/{scenario_id}/apply",
        expected_status=409,
        access_token=monitor_token,
    )
    approved = require_dict(
        request_json(
            api_url,
            "POST",
            f"/api/v1/scenarios/{scenario_id}/approve",
            access_token=monitor_token,
        ),
        "approve",
    )
    applied = require_dict(
        request_json(
            api_url,
            "POST",
            f"/api/v1/scenarios/{scenario_id}/apply",
            access_token=monitor_token,
        ),
        "apply",
    )
    robots = request_json(
        api_url,
        "GET",
        "/api/v1/robots",
        access_token=monitor_token,
    )

    if approved.get("status") != "APPROVED" or applied.get("status") != "APPLIED":
        raise RuntimeError("scenario did not complete the approval workflow")
    if not isinstance(robots, list) or len(robots) != 4:
        raise RuntimeError("applied scenario did not reset the factory to four robots")

    baseline_metrics = require_dict(baseline.get("metrics"), "metrics")
    print(f"Health: {health.get('status')}")
    print(f"Baseline throughput: {baseline_metrics.get('throughput_per_hour')}")
    print(f"Candidate: {scenario_id} -> {applied.get('status')}")
    print(f"Factory robots after apply: {len(robots)}")
    print("RBAC checks: Monitor run = 403; Designer apply = 403; premature apply = 409")
    print("MVP smoke test passed.")


if __name__ == "__main__":
    main()
