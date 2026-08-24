#!/usr/bin/env bash
set -eo pipefail

script_dir="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repository_root="${EV_TWIN_ROOT:-$(CDPATH= cd -- "${script_dir}/../.." && pwd)}"
ros_setup="${ROS_SETUP:-/opt/ros/jazzy/setup.bash}"
workspace_setup="${repository_root}/ros2_ws/install/setup.bash"

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
  robots_config:="${ROBOTS_CONFIG:-${repository_root}/ros2_ws/src/amr_gazebo/config/robots.json}"
