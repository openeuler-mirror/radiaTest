#!/usr/bin/env bash

# Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
# This project is licensed under the Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
# http://license.coscl.org.cn/MulanPSL2

set -Eeuo pipefail

vm_name=""
action=""

json_error() {
  local code="$1"
  local message="$2"
  python3 - "$code" "$message" <<'PY'
import json
import sys

print(json.dumps({"status": "error", "error_code": sys.argv[1], "error_message": sys.argv[2]}))
PY
  exit 1
}

json_success() {
  local power_state="$1"
  python3 - "$power_state" <<'PY'
import json
import sys

print(json.dumps({"status": "success", "power_state": sys.argv[1]}))
PY
}

event() {
  local phase="$1"
  local message="$2"
  printf 'KRONOS_EVENT\t%s\t%s\n' "$phase" "$message" >&2
}

run_power_command() {
  local subcommand="$1"
  local command_output=""
  if ! command_output="$(virsh "$subcommand" "$vm_name" 2>&1)"; then
    [[ -n "$command_output" ]] || command_output="failed to $subcommand VM"
    json_error vm_power_failed "$command_output"
  fi
}

[[ -n "${KRONOS_PAYLOAD_B64:-}" ]] || json_error invalid_payload "KRONOS_PAYLOAD_B64 is required"
payload_json="$(printf '%s' "$KRONOS_PAYLOAD_B64" | base64 -d)"

eval "$(
  python3 - "$payload_json" <<'PY'
import json
import shlex
import sys

data = json.loads(sys.argv[1])
for key in ["vm_name", "action"]:
    value = data.get(key) or ""
    print(f"{key}={shlex.quote(str(value))}")
PY
)"

[[ -n "$vm_name" ]] || json_error invalid_payload "vm_name is required"
[[ "$action" == "state" || "$action" == "start" || "$action" == "shutdown" || "$action" == "reboot" ]] ||
  json_error invalid_payload "action must be state, start, shutdown or reboot"

event check_dependencies "检查宿主机依赖"
for command in virsh python3; do
  command -v "$command" >/dev/null 2>&1 ||
    json_error missing_dependency "missing command: $command"
done

event domstate "读取 VM 电源状态"
if ! current_state="$(virsh domstate "$vm_name" 2>&1)"; then
  json_error vm_power_failed "$current_state"
fi
current_state="$(printf '%s' "$current_state" | tr -d '\r' | head -n 1)"

case "$action" in
  state)
    json_success "$current_state"
    ;;
  start)
    if [[ "$current_state" != "running" ]]; then
      event host_command "virsh start $vm_name"
      run_power_command start
    fi
    ;;
  shutdown)
    if [[ "$current_state" == "running" || "$current_state" == "paused" ]]; then
      event host_command "virsh shutdown $vm_name"
      run_power_command shutdown
    fi
    ;;
  reboot)
    if [[ "$current_state" != "running" ]]; then
      json_error vm_power_failed "VM must be running to reboot"
    fi
    event host_command "virsh reboot $vm_name"
    run_power_command reboot
    ;;
esac

event domstate "读取操作后的 VM 电源状态"
if ! next_state="$(virsh domstate "$vm_name" 2>&1)"; then
  json_error vm_power_failed "$next_state"
fi
next_state="$(printf '%s' "$next_state" | tr -d '\r' | head -n 1)"
json_success "$next_state"
