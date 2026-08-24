import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[2]
SIMULATION_SCRIPT = ROOT / "scripts/edge/run-simulation.sh"
BRIDGE_SCRIPT = ROOT / "scripts/edge/run-bridge.sh"
SIMULATION_UNIT = ROOT / "deploy/gcp/systemd/ev-twin-simulation.service"
BRIDGE_UNIT = ROOT / "deploy/gcp/systemd/ev-twin-bridge.service"


def test_edge_shell_wrappers_have_valid_bash_syntax() -> None:
    for script in (SIMULATION_SCRIPT, BRIDGE_SCRIPT):
        subprocess.run(["bash", "-n", script], check=True)


def test_edge_shell_wrappers_enable_nounset_after_ros_setup() -> None:
    for script in (SIMULATION_SCRIPT, BRIDGE_SCRIPT):
        lines = script.read_text().splitlines()
        nounset_line = lines.index("set -u")
        source_lines = [index for index, line in enumerate(lines) if line.startswith("source ")]

        assert lines[1] == "set -eo pipefail"
        assert source_lines
        assert nounset_line > max(source_lines)


def test_gcp_edge_files_do_not_contain_developer_home_paths() -> None:
    paths = (
        SIMULATION_SCRIPT,
        BRIDGE_SCRIPT,
        SIMULATION_UNIT,
        BRIDGE_UNIT,
        ROOT / "deploy/gcp/bridge.env.example",
        ROOT / "docs/runbooks/gcp-edge.md",
        ROOT / "docs/runbooks/mvp-edge-acceptance.md",
    )
    assert all("/home/hung" not in path.read_text() for path in paths)


def test_bridge_owns_secret_and_requires_https() -> None:
    simulation_unit = SIMULATION_UNIT.read_text()
    bridge_unit = BRIDGE_UNIT.read_text()
    bridge_script = BRIDGE_SCRIPT.read_text()

    assert "EDGE_TELEMETRY_SHARED_SECRET" not in simulation_unit
    assert "EnvironmentFile=/etc/ev-factory-twin/bridge.env" in bridge_unit
    assert 'TELEMETRY_BACKEND_URL:-}" != https://*' in bridge_script
    assert 'edge_secret="${EDGE_TELEMETRY_SHARED_SECRET:-}"' in bridge_script


def test_bridge_wrapper_fails_before_ros_for_invalid_credentials() -> None:
    base_environment = {"PATH": os.environ["PATH"]}

    missing_url = subprocess.run(
        ["bash", BRIDGE_SCRIPT], env=base_environment, capture_output=True, text=True
    )
    assert missing_url.returncode == 1
    assert "remote HTTPS URL" in missing_url.stderr

    short_secret = subprocess.run(
        ["bash", BRIDGE_SCRIPT],
        env={
            **base_environment,
            "TELEMETRY_BACKEND_URL": "https://api.example.com",
            "EDGE_TELEMETRY_SHARED_SECRET": "too-short",
        },
        capture_output=True,
        text=True,
    )
    assert short_secret.returncode == 1
    assert "at least 32 characters" in short_secret.stderr


def test_services_are_non_root_and_restart_on_failure() -> None:
    for unit in (SIMULATION_UNIT, BRIDGE_UNIT):
        content = unit.read_text()
        assert "User=ev-twin" in content
        assert "Group=ev-twin" in content
        assert "Restart=on-failure" in content
        assert "NoNewPrivileges=true" in content
