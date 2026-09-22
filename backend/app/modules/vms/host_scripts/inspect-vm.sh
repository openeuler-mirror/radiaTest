#!/usr/bin/env bash

# Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
# This project is licensed under the Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
# http://license.coscl.org.cn/MulanPSL2

set -Eeuo pipefail

vm_name=""
system_disk_path=""
data_disk_paths=""

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

[[ -n "${KRONOS_PAYLOAD_B64:-}" ]] || json_error invalid_payload "KRONOS_PAYLOAD_B64 is required"
payload_json="$(printf '%s' "$KRONOS_PAYLOAD_B64" | base64 -d)"

eval "$(
  python3 - "$payload_json" <<'PY'
import json
import shlex
import sys

data = json.loads(sys.argv[1])
for key in ["vm_name", "system_disk_path"]:
    value = data.get(key) or ""
    print(f"{key}={shlex.quote(str(value))}")
paths = data.get("data_disk_paths") or []
print("data_disk_paths=" + shlex.quote("\n".join(str(path) for path in paths)))
PY
)"

[[ -n "$vm_name" ]] || json_error invalid_payload "vm_name is required"

for command in virsh python3; do
  command -v "$command" >/dev/null 2>&1 ||
    json_error missing_dependency "missing command: $command"
done

domain_exists=false
power_state=""
if virsh dominfo "$vm_name" >/dev/null 2>&1; then
  domain_exists=true
  power_state="$(virsh domstate "$vm_name" 2>/dev/null || true)"
fi

system_disk_exists=false
[[ -n "$system_disk_path" && -f "$system_disk_path" ]] && system_disk_exists=true

data_existing=()
while IFS= read -r path; do
  [[ -n "$path" ]] && data_existing+=("$path")
done <<<"$data_disk_paths"

python3 - "$domain_exists" "$power_state" "$system_disk_exists" ${data_existing[@]+"${data_existing[@]}"} <<'PY'
import json
import sys

print(json.dumps({
    "status": "success",
    "domain_exists": sys.argv[1] == "true",
    "power_state": sys.argv[2] or None,
    "system_disk_exists": sys.argv[3] == "true",
    "data_disks_existing": [path for path in sys.argv[4:] if path],
}))
PY
