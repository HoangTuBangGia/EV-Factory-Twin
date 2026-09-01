#!/usr/bin/env bash
set -eo pipefail

script_dir="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repository_root="${EV_TWIN_ROOT:-$(CDPATH= cd -- "${script_dir}/../.." && pwd)}"
ros_setup="${ROS_SETUP:-/opt/ros/jazzy/setup.bash}"
workspace_setup="${repository_root}/ros2_ws/install/setup.bash"
robots_config="${ROBOTS_CONFIG:-${repository_root}/ros2_ws/src/amr_gazebo/config/robots.json}"
runtime_layout_id="${RUNTIME_LAYOUT_ID:-LAYOUT-DEFAULT}"
runtime_layout_version="${RUNTIME_LAYOUT_VERSION:-3}"
runtime_route_id="${RUNTIME_ROUTE_ID:-BATTERY_DELIVERY}"
runtime_robot_speed_mps="${RUNTIME_ROBOT_SPEED_MPS:-1.2}"
runtime_charger_count="${RUNTIME_CHARGER_COUNT:-2}"
runtime_demand_interval_seconds="${RUNTIME_DEMAND_INTERVAL_SECONDS:-8.0}"

if [[ "${TELEMETRY_BACKEND_URL:-}" != https://* ]]; then
  echo "TELEMETRY_BACKEND_URL must be a remote HTTPS URL" >&2
  exit 1
fi
edge_secret="${EDGE_TELEMETRY_SHARED_SECRET:-}"
if (( ${#edge_secret} < 32 )); then
  echo "EDGE_TELEMETRY_SHARED_SECRET must contain at least 32 characters" >&2
  exit 1
fi
for setup_file in "${ros_setup}" "${workspace_setup}"; do
  if [[ ! -r "${setup_file}" ]]; then
    echo "required ROS setup file is not readable: ${setup_file}" >&2
    exit 1
  fi
done

source "${ros_setup}"
source "${workspace_setup}"
set -u

exec ros2 launch telemetry_bridge telemetry_bridge.launch.py \
  backend_url:="${TELEMETRY_BACKEND_URL}" \
  robots_config:="${robots_config}" \
  bridge_id:="${BRIDGE_ID:-gcp-edge-main}" \
  runtime_layout_id:="${runtime_layout_id}" \
  runtime_layout_version:="${runtime_layout_version}" \
  runtime_route_id:="${runtime_route_id}" \
  runtime_robot_speed_mps:="${runtime_robot_speed_mps}" \
  runtime_charger_count:="${runtime_charger_count}" \
  runtime_demand_interval_seconds:="${runtime_demand_interval_seconds}"
