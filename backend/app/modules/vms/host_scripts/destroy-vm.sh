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

event() {
  local phase="$1"
  local message="$2"
  printf 'KRONOS_EVENT\t%s\t%s\n' "$phase" "$message" >&2
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

event validate_payload "参数校验完成"
event check_dependencies "检查宿主机依赖"
for command in virsh python3 rm; do
  command -v "$command" >/dev/null 2>&1 ||
    json_error missing_dependency "missing command: $command"
done

if virsh dominfo "$vm_name" >/dev/null 2>&1; then
  event destroy_domain "销毁并取消定义 libvirt domain"
  virsh destroy "$vm_name" >/dev/null 2>&1 || true
  virsh undefine "$vm_name" --nvram >/dev/null 2>&1 ||
    json_error vm_destroy_failed "failed to undefine VM"
fi

event remove_disks "删除 VM 磁盘文件"
[[ -n "$system_disk_path" ]] && rm -f "$system_disk_path"
while IFS= read -r path; do
  [[ -n "$path" ]] && rm -f "$path"
done <<<"$data_disk_paths"

event completed "宿主机销毁流程完成"
python3 - <<'PY'
import json

print(json.dumps({"status": "success"}))
PY
