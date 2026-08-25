#!/usr/bin/env bash
set -Eeuo pipefail

repository=/opt/ev-factory-twin
state_directory=/var/lib/ev-twin-deploy
requested_sha="${1:-}"

if [[ ! "${requested_sha}" =~ ^[0-9a-f]{40}$ ]]; then
  echo "usage: ev-twin-deploy FULL_40_CHARACTER_GIT_SHA" >&2
  exit 2
fi

exec 9>/run/lock/ev-twin-deploy.lock
flock --exclusive --nonblock 9 || {
  echo "another edge deployment is already running" >&2
  exit 3
}

test -d "${repository}/.git"
remote_url="$(runuser --user ev-twin -- git -C "${repository}" remote get-url origin)"
case "${remote_url}" in
  https://github.com/HoangTuBangGia/EV-Factory-Twin | \
    https://github.com/HoangTuBangGia/EV-Factory-Twin.git)
    ;;
  *)
    echo "unexpected repository origin: ${remote_url}" >&2
    exit 4
    ;;
esac

install -d -o root -g root -m 0755 "${state_directory}"
previous_sha="$(runuser --user ev-twin -- git -C "${repository}" rev-parse HEAD)"
services_stopped=false

build_sha() {
  local sha="$1"
  runuser --user ev-twin -- git -C "${repository}" checkout --detach "${sha}"
  runuser --user ev-twin -- bash -lc \
    "cd '${repository}' && set +u && source /opt/ros/jazzy/setup.bash && make ros-check"
}

install_units_and_start() {
  install -o root -g root -m 0644 \
    "${repository}/deploy/gcp/systemd/ev-twin-simulation.service" \
    /etc/systemd/system/ev-twin-simulation.service
  install -o root -g root -m 0644 \
    "${repository}/deploy/gcp/systemd/ev-twin-bridge.service" \
    /etc/systemd/system/ev-twin-bridge.service
  systemctl daemon-reload
  systemctl enable ev-twin-simulation.service ev-twin-bridge.service
  systemctl start ev-twin-simulation.service ev-twin-bridge.service
  systemctl is-active --quiet ev-twin-simulation.service
  systemctl is-active --quiet ev-twin-bridge.service
}

rollback() {
  local exit_code=$?
  trap - ERR
  echo "edge deployment failed; rolling back to ${previous_sha}" >&2
  if [[ "${services_stopped}" == true && "${previous_sha}" =~ ^[0-9a-f]{40}$ ]]; then
    systemctl stop ev-twin-bridge.service ev-twin-simulation.service || true
    if build_sha "${previous_sha}" && install_units_and_start; then
      printf '%s\n' "${previous_sha}" >"${state_directory}/current-sha"
      echo "rollback completed" >&2
    else
      echo "rollback failed; operator intervention is required" >&2
    fi
  fi
  exit "${exit_code}"
}
trap rollback ERR

runuser --user ev-twin -- git -C "${repository}" fetch --no-tags origin "${requested_sha}"
runuser --user ev-twin -- git -C "${repository}" cat-file -e "${requested_sha}^{commit}"

systemctl stop ev-twin-bridge.service ev-twin-simulation.service || true
services_stopped=true
build_sha "${requested_sha}"
install_units_and_start

printf '%s\n' "${requested_sha}" >"${state_directory}/current-sha"
trap - ERR
echo "edge deployment completed: ${requested_sha}"
