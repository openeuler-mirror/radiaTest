#!/usr/bin/env bash

# Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
# This project is licensed under the Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
# http://license.coscl.org.cn/MulanPSL2

set -Eeuo pipefail

BASE_DIR="${KRONOS_BASE_DIR:-/var/lib/libvirt/images/kronos}"
CACHE_DIR="$BASE_DIR/cache"
INSTANCE_DIR="$BASE_DIR/instances"
CACHE_RETENTION_DAYS=30
INSTANCE_PATH=""
DATA_DISK_PATHS=()
DOMAIN_XML_PATH=""
VIRT_INSTALL_XML_PATH=""
VIRT_INSTALL_ERR_PATH=""
VM_DEFINED=false
vm_uuid=""
vm_name=""
install_type=""
image_url=""
cache_filename=""
arch=""
system_disk_size_gb=""
vcpu_count=""
memory_mb=""
data_disk_count=""
data_disk_size_gb=""
extra_nic_num=""
dhcp_leases_url=""
network_bridge=""
cache_path=""

json_error() {
  local code="$1"
  local message="$2"
  trap - ERR HUP INT TERM
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

shell_quote_command() {
  printf '%q ' "$@"
}

event_command() {
  event host_command "$(shell_quote_command "$@")"
}

enable_vnc_websocket_xml() {
  local install_type="$1"
  python3 -c '
import sys
import xml.etree.ElementTree as ET

install_type = sys.argv[1]
tree = ET.parse(sys.stdin)
root = tree.getroot()
vnc_graphics = None
for graphics in root.findall(".//graphics"):
    if graphics.get("type") == "vnc":
        vnc_graphics = graphics
        break
if vnc_graphics is None:
    print("missing VNC graphics element", file=sys.stderr)
    sys.exit(1)

def set_lifecycle(name, value, after=None):
    element = root.find(name)
    if element is None:
        element = ET.Element(name)
        children = list(root)
        after_element = root.find(after) if after else None
        devices = root.find("devices")
        if after_element is not None:
            root.insert(children.index(after_element) + 1, element)
        elif devices is not None:
            root.insert(children.index(devices), element)
        else:
            root.append(element)
    element.text = value

vnc_graphics.set("websocket", "-1")
set_lifecycle("on_reboot", "restart", "on_poweroff")
if install_type == "manual":
    os_element = root.find("os")
    if os_element is None:
        print("missing os element", file=sys.stderr)
        sys.exit(1)
    for boot in list(os_element.findall("boot")):
        os_element.remove(boot)
    os_element.append(ET.Element("boot", {"dev": "hd"}))
    os_element.append(ET.Element("boot", {"dev": "cdrom"}))
tree.write(sys.stdout, encoding="unicode")
' "$install_type"
}

compact_text() {
  python3 -c '
import sys

text = sys.stdin.read().strip()
lines = [line.strip() for line in text.splitlines() if line.strip()]
text = "\n".join(lines[-20:])
sys.stdout.write(text[-2000:])
'
}

compact_event_text() {
  compact_text | python3 -c '
import sys

text = sys.stdin.read().rstrip("\n")
sys.stdout.write(text.replace("\t", " ").replace("\n", r"\n"))
'
}

fail_command_output() {
  local code="$1"
  local message="$2"
  local output="$3"
  shift 3
  local command_line
  local diagnostic
  command_line="$(shell_quote_command "$@")"
  event host_command_failed "$command_line"
  diagnostic="$(printf '%s' "$output" | compact_text)"
  if [[ -n "$diagnostic" ]]; then
    event host_command_stderr "$(printf '%s' "$diagnostic" | compact_event_text)"
    cleanup_and_error "$code" "${message}"$'\n'"failed command: ${command_line}"$'\n'"stderr:"$'\n'"${diagnostic}"
  fi
  cleanup_and_error "$code" "${message}"$'\n'"failed command: ${command_line}"
}

collect_command_diagnostic() {
  local output
  event_command "$@"
  if output="$("$@" 2>&1)"; then
    [[ -n "$output" ]] && event host_command_output "$(printf '%s' "$output" | compact_event_text)"
    return 0
  fi
  [[ -n "$output" ]] && event host_command_stderr "$(printf '%s' "$output" | compact_event_text)"
  return 0
}

collect_failure_diagnostics() {
  [[ "${VM_DEFINED}" == "true" && -n "${vm_name}" ]] || return 0
  event failure_diagnostics "采集回滚前 libvirt domain 诊断"
  collect_command_diagnostic virsh domstate "$vm_name"
  collect_command_diagnostic virsh dominfo "$vm_name"
  collect_command_diagnostic virsh dumpxml "$vm_name"
}

cleanup() {
  event rollback "清理已创建的 VM 和磁盘"
  if [[ "${VM_DEFINED}" == "true" ]]; then
    event_command virsh destroy "$vm_name"
    virsh destroy "$vm_name" >/dev/null 2>&1 || true
    event_command virsh undefine "$vm_name" --nvram
    virsh undefine "$vm_name" --nvram >/dev/null 2>&1 || true
  fi
  if [[ -n "${INSTANCE_PATH}" ]]; then
    event_command virsh vol-delete --pool instances "$(basename "${INSTANCE_PATH}")"
    virsh vol-delete --pool instances "$(basename "${INSTANCE_PATH}")" >/dev/null 2>&1 || true
    rm -f "${INSTANCE_PATH}" "${INSTANCE_PATH}.part" || true
  fi
  if [[ -n "${cache_path}" ]]; then
    rm -f "${cache_path}.part" || true
  fi
  for path in "${DATA_DISK_PATHS[@]}"; do
    event_command virsh vol-delete --pool instances "$(basename "$path")"
    virsh vol-delete --pool instances "$(basename "$path")" >/dev/null 2>&1 || true
    rm -f "$path" "$path.part" || true
  done
  for path in "$DOMAIN_XML_PATH" "$VIRT_INSTALL_XML_PATH" "$VIRT_INSTALL_ERR_PATH"; do
    [[ -n "$path" ]] && rm -f "$path" || true
  done
}

cleanup_and_error() {
  local code="$1"
  local message="$2"
  collect_failure_diagnostics
  cleanup
  json_error "$code" "$message"
}

trap 'cleanup_and_error cleanup_failed "unexpected create-vm failure at line ${LINENO}"' ERR
trap 'cleanup_and_error interrupted "create-vm interrupted"' HUP INT TERM

[[ -n "${KRONOS_PAYLOAD_B64:-}" ]] || json_error invalid_payload "KRONOS_PAYLOAD_B64 is required"
payload_json="$(printf '%s' "$KRONOS_PAYLOAD_B64" | base64 -d)"

eval "$(
  python3 - "$payload_json" <<'PY'
import json
import shlex
import sys

data = json.loads(sys.argv[1])
keys = [
    "vm_uuid",
    "vm_name",
    "install_type",
    "image_url",
    "cache_filename",
    "arch",
    "system_disk_size_gb",
    "vcpu_count",
    "memory_mb",
    "data_disk_count",
    "data_disk_size_gb",
    "extra_nic_num",
    "dhcp_leases_url",
    "network_bridge",
]
for key in keys:
    value = data.get(key)
    if value is None:
        value = ""
    print(f"{key}={shlex.quote(str(value))}")
PY
)"

for key in \
  vm_uuid \
  vm_name \
  install_type \
  image_url \
  cache_filename \
  arch \
  system_disk_size_gb \
  vcpu_count \
  memory_mb \
  data_disk_count \
  data_disk_size_gb \
  extra_nic_num \
  dhcp_leases_url \
  network_bridge; do
  [[ -n "${!key}" ]] || json_error invalid_payload "$key is required"
done

[[ "$install_type" == "auto" || "$install_type" == "manual" ]] ||
  json_error invalid_payload "install_type must be auto or manual"

for key in system_disk_size_gb vcpu_count memory_mb data_disk_count data_disk_size_gb extra_nic_num; do
  [[ "${!key}" =~ ^[0-9]+$ ]] || json_error invalid_payload "$key must be a number"
done

event validate_payload "参数校验完成"
event check_dependencies "检查宿主机依赖"
for command in virsh virt-install qemu-img curl flock python3 nproc free df cp mv rm find grep mktemp; do
  command -v "$command" >/dev/null 2>&1 ||
    json_error missing_dependency "missing command: $command"
done

tcp_port_open() {
  local host="$1"
  local port="$2"
  python3 - "$host" "$port" <<'PY'
import socket
import sys

try:
    with socket.create_connection((sys.argv[1], int(sys.argv[2])), timeout=5):
        pass
except OSError:
    sys.exit(1)
PY
}

bytes_to_gb() {
  local bytes="$1"
  printf '%s\n' $(((bytes + 1073741824 - 1) / 1073741824))
}

image_content_length_bytes() {
  local headers
  local content_length
  event_command curl --fail --silent --show-error --location --head "$image_url"
  headers="$(curl --fail --silent --show-error --location --head "$image_url" 2>/dev/null)" ||
    return 1
  content_length="$(
    printf '%s\n' "$headers" |
      awk 'BEGIN { IGNORECASE = 1 } /^content-length:/ { gsub("\r", "", $2); value = $2 } END { print value }'
  )"
  [[ "$content_length" =~ ^[0-9]+$ ]] || return 1
  printf '%s\n' "$content_length"
}

check_image_download_capacity() {
  local content_length_bytes
  local content_length_gb
  local available_disk_gb
  local required_disk_gb

  [[ ! -s "$cache_path" ]] || return 0
  event image_download_capacity "检查镜像下载所需空间"
  if ! content_length_bytes="$(image_content_length_bytes)"; then
    event image_download_capacity "镜像服务未返回 Content-Length，跳过下载前容量预检"
    return 0
  fi

  content_length_gb="$(bytes_to_gb "$content_length_bytes")"
  required_disk_gb=$((content_length_gb + 10))
  if [[ "$install_type" == "manual" ]]; then
    required_disk_gb=$((content_length_gb + system_disk_size_gb + data_disk_count * data_disk_size_gb + 10))
  fi

  event_command df -BG /var/lib/libvirt/images
  available_disk_gb="$(df -BG /var/lib/libvirt/images | awk 'NR == 2 {gsub(/G/, "", $4); print $4}')"
  (( available_disk_gb >= required_disk_gb )) ||
    json_error capacity_insufficient "insufficient disk for image download"
}

cache_file_is_referenced() {
  local path="$1"
  local domains
  local domain
  if ! domains="$(virsh list --all --name 2>/dev/null)"; then
    return 0
  fi
  while IFS= read -r domain; do
    [[ -n "$domain" ]] || continue
    if virsh dumpxml "$domain" 2>/dev/null | grep -Fq -- "$path"; then
      return 0
    fi
  done <<<"$domains"
  return 1
}

cleanup_old_cache_files() {
  local path
  while IFS= read -r -d '' path; do
    if cache_file_is_referenced "$path"; then
      event cache_in_use "跳过仍被 libvirt domain 引用的缓存 ${path##*/}"
      continue
    fi
    if rm -f "$path"; then
      event cache_removed "删除过期缓存 ${path##*/}"
    else
      event cache_cleanup_warning "删除过期缓存失败 ${path##*/}"
    fi
  done < <(
    find "$CACHE_DIR" \
      -maxdepth 1 \
      -type f \
      \( -name "*.iso" -o -name "*.qcow2" \) \
      -mtime +"$CACHE_RETENTION_DAYS" \
      -print0 2>/dev/null || true
  )
}

mkdir -p "$CACHE_DIR" "$INSTANCE_DIR"
cleanup_old_cache_files || event cache_cleanup_warning "缓存清理失败，继续创建 VM"

event check_capacity "检查宿主机实时容量"
# vCPU 配置总和容量检查已取消：libvirt overcommit 下配置总和远超物理是正常的，
# 但脚本用配置总和判断会误报 insufficient vCPU（实际 CPU 可能 idle）。
# 宿主机实际容量由内存检查 + virsh start 失败兜底。

event_command free -m
available_memory_mb="$(free -m | awk '/^Mem:/ {print $7}')"
(( available_memory_mb >= memory_mb + 1024 )) ||
  json_error capacity_insufficient "insufficient memory"

cache_path="$CACHE_DIR/$cache_filename"
lock_path="$cache_path.lock"
check_image_download_capacity
event cache_image "检查或下载缓存镜像 $cache_filename"
if ! (
  flock -x 200
  if [[ ! -s "$cache_path" ]]; then
    event_command curl --fail --location --retry 3 "$image_url" --output "$cache_path.part"
    curl --fail --location --retry 3 "$image_url" --output "$cache_path.part" || exit 1
    mv "$cache_path.part" "$cache_path"
  fi
) 200>"$lock_path"; then
  cleanup_and_error image_download_failed "failed to download image"
fi

if [[ "$install_type" == "auto" ]]; then
  event_command qemu-img info --output=json "$cache_path"
  image_virtual_gb="$(
    qemu-img info --output=json "$cache_path" |
      python3 -c '
import json
import math
import sys

size = int((json.load(sys.stdin).get("virtual-size") or 0))
if size <= 0:
    sys.exit(1)
print(math.ceil(size / 1024 / 1024 / 1024))
'
  )" ||
    cleanup_and_error vm_create_failed "failed to read system disk virtual size"
else
  image_virtual_gb="$system_disk_size_gb"
fi

event_command df -BG /var/lib/libvirt/images
available_disk_gb="$(df -BG /var/lib/libvirt/images | awk 'NR == 2 {gsub(/G/, "", $4); print $4}')"
required_disk_gb=$((image_virtual_gb + data_disk_count * data_disk_size_gb + 10))
(( available_disk_gb >= required_disk_gb )) ||
  json_error capacity_insufficient "insufficient disk"

INSTANCE_PATH="$INSTANCE_DIR/$vm_name.qcow2"
event create_system_disk "创建系统盘实例"
if [[ "$install_type" == "auto" ]]; then
  event_command cp --reflink=auto --sparse=always "$cache_path" "$INSTANCE_PATH.part"
  cp --reflink=auto --sparse=always "$cache_path" "$INSTANCE_PATH.part" ||
    cleanup_and_error vm_create_failed "failed to copy system disk"
else
  event_command qemu-img create -f qcow2 "$INSTANCE_PATH.part" "${system_disk_size_gb}G"
  qemu-img create -f qcow2 "$INSTANCE_PATH.part" "${system_disk_size_gb}G" >/dev/null ||
    cleanup_and_error vm_create_failed "failed to create system disk"
fi
mv "$INSTANCE_PATH.part" "$INSTANCE_PATH"

for index in $(seq 1 "$data_disk_count"); do
  disk_path="$INSTANCE_DIR/$vm_name.$index.qcow2"
  DATA_DISK_PATHS+=("$disk_path")
  event create_data_disk "创建数据盘 $index"
  event_command qemu-img create -f qcow2 "$disk_path.part" "${data_disk_size_gb}G"
  qemu-img create -f qcow2 "$disk_path.part" "${data_disk_size_gb}G" >/dev/null ||
    cleanup_and_error vm_create_failed "failed to create data disk"
  mv "$disk_path.part" "$disk_path"
done

vcpu_topology="${vcpu_count},sockets=1,cores=${vcpu_count},threads=1"
virt_install_args=(
  --os-type generic
  --name "$vm_name"
  --memory "$memory_mb"
  --vcpus "$vcpu_topology"
  --cpu host-passthrough
  --disk "path=$INSTANCE_PATH,bus=virtio,format=qcow2"
  --network "bridge=$network_bridge,model=virtio"
  --video virtio
  --noautoconsole
  --graphics "vnc,listen=0.0.0.0"
  --os-variant unknown
)
for index in $(seq 1 "$extra_nic_num"); do
  virt_install_args+=(--network "bridge=$network_bridge,model=virtio")
done
if [[ "$arch" == "aarch64" ]]; then
  # Keep the pci root on bus 1 so virtio NIC uses PCI bus 2.
  virt_install_args+=(--controller "type=pci,model=pcie-root-port,index=50")
fi
if [[ "$install_type" == "auto" ]]; then
  virt_install_args+=(--import --noreboot)
else
  virt_install_args+=(--cdrom "$cache_path" --boot "hd,cdrom" --wait 0)
fi
for disk_path in "${DATA_DISK_PATHS[@]}"; do
  virt_install_args+=(--disk "path=$disk_path,bus=virtio,format=qcow2")
done

event define_vm "定义 libvirt domain"
VIRT_INSTALL_XML_PATH="$(mktemp)"
VIRT_INSTALL_ERR_PATH="$(mktemp)"
DOMAIN_XML_PATH="$(mktemp)"
print_xml_args=(--print-xml 1)
create_lock_path="$BASE_DIR/.kronos-create.lock"
define_rc=0
(
  flock -x 200
  set +e
  trap - ERR HUP INT TERM
  event_command virt-install "${virt_install_args[@]}" "${print_xml_args[@]}"
  if ! virt-install "${virt_install_args[@]}" "${print_xml_args[@]}" >"$VIRT_INSTALL_XML_PATH" 2>"$VIRT_INSTALL_ERR_PATH"; then
    exit 1
  fi
  event configure_vnc_websocket "配置 VNC WebSocket"
  : >"$VIRT_INSTALL_ERR_PATH"
  if ! enable_vnc_websocket_xml "$install_type" <"$VIRT_INSTALL_XML_PATH" >"$DOMAIN_XML_PATH" 2>"$VIRT_INSTALL_ERR_PATH"; then
    exit 2
  fi
  event_command virsh define "$DOMAIN_XML_PATH"
  if ! virsh_define_output="$(virsh define "$DOMAIN_XML_PATH" 2>&1 >/dev/null)"; then
    printf '%s' "$virsh_define_output" >"$VIRT_INSTALL_ERR_PATH"
    exit 3
  fi
) 200>"$create_lock_path" || define_rc=$?
if [[ "$define_rc" != "0" ]]; then
  case "$define_rc" in
    1)
      virt_install_output="$(<"$VIRT_INSTALL_ERR_PATH")"
      [[ -n "$virt_install_output" ]] || virt_install_output="$(<"$VIRT_INSTALL_XML_PATH")"
      fail_command_output vm_create_failed "failed to generate VM XML" "$virt_install_output" virt-install "${virt_install_args[@]}" "${print_xml_args[@]}"
      ;;
    2)
      xml_patch_output="$(<"$VIRT_INSTALL_ERR_PATH")"
      [[ -n "$xml_patch_output" ]] || xml_patch_output="$(<"$DOMAIN_XML_PATH")"
      fail_command_output vm_create_failed "failed to configure VM VNC WebSocket" "$xml_patch_output" enable_vnc_websocket_xml
      ;;
    3)
      virsh_define_output="$(<"$VIRT_INSTALL_ERR_PATH")"
      fail_command_output vm_create_failed "failed to define VM" "$virsh_define_output" virsh define "$DOMAIN_XML_PATH"
      ;;
    *)
      cleanup_and_error vm_create_failed "failed to define VM (virt-install/vnc/define locked, rc=$define_rc)"
      ;;
  esac
fi
VM_DEFINED=true
rm -f "$DOMAIN_XML_PATH" "$VIRT_INSTALL_XML_PATH" "$VIRT_INSTALL_ERR_PATH"
DOMAIN_XML_PATH=""
VIRT_INSTALL_XML_PATH=""
VIRT_INSTALL_ERR_PATH=""

event start_vm "启动 VM"
event_command virsh domstate "$vm_name"
if [[ "$(virsh domstate "$vm_name" 2>/dev/null || true)" != "running" ]]; then
  event_command virsh start "$vm_name"
  if ! virsh_start_output="$(virsh start "$vm_name" 2>&1 >/dev/null)"; then
    fail_command_output vm_create_failed "failed to start VM" "$virsh_start_output" virsh start "$vm_name"
  fi
fi

event_command virsh dumpxml "$vm_name"
if ! domain_xml="$(virsh dumpxml "$vm_name" 2>&1)"; then
  fail_command_output vm_create_failed "failed to dump VM XML" "$domain_xml" virsh dumpxml "$vm_name"
fi
mac_address="$(printf '%s' "$domain_xml" | awk -F"'" '/mac address/ {print $2; exit}')"
[[ -n "$mac_address" ]] || cleanup_and_error vm_create_failed "failed to read VM MAC"
vnc_websocket_port="$(
  printf '%s' "$domain_xml" | python3 -c '
import re
import sys

xml = sys.stdin.read()
match = re.search(r"<graphics\b[^>]*\btype=.vnc.[^>]*\bwebsocket=.([0-9]+).", xml)
print(match.group(1) if match else "")
  '
)"
[[ "$vnc_websocket_port" =~ ^[0-9]+$ ]] ||
  cleanup_and_error vm_create_failed "failed to parse VM VNC WebSocket port"

event_command virsh vncdisplay "$vm_name"
if ! vnc_display_output="$(virsh vncdisplay "$vm_name" 2>&1)"; then
  fail_command_output vm_create_failed "failed to read VM VNC display" "$vnc_display_output" virsh vncdisplay "$vm_name"
fi
vnc_display="$(printf '%s' "$vnc_display_output" | tr -d ':')"
[[ "$vnc_display" =~ ^[0-9]+$ ]] ||
  cleanup_and_error vm_create_failed "failed to parse VM VNC display"
vnc_port=$((5900 + vnc_display))

primary_ip=""
if [[ "$install_type" == "auto" ]]; then
  deadline=$((SECONDS + 3600))
  event wait_dhcp "等待 DHCP 分配 IP"
  event_command curl --fail --silent --show-error "$dhcp_leases_url"
  while (( SECONDS < deadline )); do
    leases="$(curl --fail --silent --show-error "$dhcp_leases_url" || true)"
    primary_ip="$(
      python3 -c '
import re
import sys

mac = sys.argv[1].lower()
text = sys.stdin.read()
matches = []
for block in re.finditer(r"lease\s+([0-9.]+)\s+\{(.*?)\}", text, re.S):
    ip, body = block.group(1), block.group(2).lower()
    if mac in body:
        matches.append(ip)
print(matches[-1] if matches else "")
      ' "$mac_address" <<<"$leases"
    )"
    if [[ -n "$primary_ip" ]]; then
      if tcp_port_open "$primary_ip" 22; then
        break
      fi
    fi
    sleep 5
  done

  [[ -n "$primary_ip" ]] || cleanup_and_error dhcp_ip_not_found "failed to find VM DHCP lease"
  event wait_ssh "检查 VM 22 端口可连接"
  tcp_port_open "$primary_ip" 22 ||
    cleanup_and_error ssh_port_not_ready "VM SSH port is not ready"
else
  event manual_install_ready "ISO 安装 VM 已启动，请通过 VNC 完成系统安装"
fi

event completed "宿主机创建流程完成"
python3 - "$vm_uuid" "$vm_name" "$primary_ip" "$mac_address" "$vnc_port" "$vnc_websocket_port" "$image_virtual_gb" "$INSTANCE_PATH" "${DATA_DISK_PATHS[@]}" <<'PY'
import json
import sys

primary_ip = sys.argv[3] or None
print(json.dumps({
    "status": "success",
    "vm_uuid": sys.argv[1],
    "vm_name": sys.argv[2],
    "primary_ip": primary_ip,
    "mac_address": sys.argv[4],
    "vnc_port": int(sys.argv[5]),
    "vnc_websocket_port": int(sys.argv[6]),
    "disk_gb": int(sys.argv[7]),
    "system_disk_path": sys.argv[8],
    "data_disk_paths": sys.argv[9:],
}))
PY
