#!/usr/bin/env bash
set -eo pipefail

script_dir="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repository_root="${EV_TWIN_ROOT:-$(CDPATH= cd -- "${script_dir}/../.." && pwd)}"
ros_setup="${ROS_SETUP:-/opt/ros/jazzy/setup.bash}"
workspace_setup="${repository_root}/ros2_ws/install/setup.bash"
robots_config="${ROBOTS_CONFIG:-${repository_root}/ros2_ws/src/amr_gazebo/config/robots.json}"
stations_config="${STATIONS_CONFIG:-${repository_root}/ros2_ws/src/amr_navigation/config/stations.json}"
runtime_layout_id="${RUNTIME_LAYOUT_ID:-LAYOUT-DEFAULT}"
runtime_layout_version="${RUNTIME_LAYOUT_VERSION:-3}"
runtime_route_id="${RUNTIME_ROUTE_ID:-BATTERY_DELIVERY}"
runtime_robot_speed_mps="${RUNTIME_ROBOT_SPEED_MPS:-1.2}"
runtime_charger_count="${RUNTIME_CHARGER_COUNT:-2}"
runtime_demand_interval_seconds="${RUNTIME_DEMAND_INTERVAL_SECONDS:-8.0}"

for setup_file in "${ros_setup}" "${workspace_setup}"; do
  if [[ ! -r "${setup_file}" ]]; then
    echo "required ROS setup file is not readable: ${setup_file}" >&2
    exit 1
  fi
done

source "${ros_setup}"
source "${workspace_setup}"
set -u

exec ros2 launch amr_gazebo sim.launch.py \
  gz_args:="${GZ_SIM_ARGS:--s -r}" \
  robots_config:="${robots_config}" \
  stations_config:="${stations_config}" \
  runtime_layout_id:="${runtime_layout_id}" \
  runtime_layout_version:="${runtime_layout_version}" \
  runtime_route_id:="${runtime_route_id}" \
  runtime_robot_speed_mps:="${runtime_robot_speed_mps}" \
  runtime_charger_count:="${runtime_charger_count}" \
  runtime_demand_interval_seconds:="${runtime_demand_interval_seconds}"
