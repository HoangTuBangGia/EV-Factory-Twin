#!/usr/bin/env bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install --yes ca-certificates curl git locales make software-properties-common

locale-gen en_US en_US.UTF-8
update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8

add-apt-repository --yes universe

ros_apt_source_version="$({
  curl --fail --silent --show-error \
    https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest
} | python3 -c 'import json, sys; print(json.load(sys.stdin)["tag_name"])')"
test -n "${ros_apt_source_version}"

curl --fail --location --show-error \
  --output /tmp/ros2-apt-source.deb \
  "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ros_apt_source_version}/ros2-apt-source_${ros_apt_source_version}.noble_all.deb"
dpkg --install /tmp/ros2-apt-source.deb

apt-get update
apt-get install --yes \
  python3-colcon-common-extensions \
  python3-colcon-ros \
  python3-rosdep \
  ros-dev-tools \
  ros-jazzy-ros-base \
  ros-jazzy-ros-gz

if [[ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]]; then
  rosdep init
fi

if ! id --user ev-twin >/dev/null 2>&1; then
  useradd --create-home --shell /bin/bash ev-twin
fi

install -d -o ev-twin -g ev-twin /opt/ev-factory-twin
runuser --user ev-twin -- rosdep update --rosdistro jazzy

set +u
source /opt/ros/jazzy/setup.bash
set -u
ros2 --help >/dev/null
gz sim --versions
colcon version-check
rosdep --version
