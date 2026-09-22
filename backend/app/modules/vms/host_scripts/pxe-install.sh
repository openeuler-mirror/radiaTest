#!/usr/bin/env bash

# Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
# This project is licensed under the Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
# http://license.coscl.org.cn/MulanPSL2

set -Eeuo pipefail

# PXE install host script — runs ON the PXE server (dhcpd + tftp + httpd).
# Worker calls this via run_host_script to sync boot files and bind DHCP.
# Then worker does ipmitool + SSH check separately.
#
# Input: KRONOS_PAYLOAD_B64 (base64 JSON with target_mac, target_ip,
#        efi_url, repo_url, tftp_root, httpd_root, httpd_prefix, os_name)
# Output: stdout JSON {"status":"ok","efi_relative_path":"..."}
#         stderr KRONOS_EVENT lines for task_events

json_error() {
  local code="$1"
  local message="$2"
  python3 - "$code" "$message" <<'PY'
import json, sys
print(json.dumps({"status": "error", "error_code": sys.argv[1], "error_message": sys.argv[2]}))
PY
  exit 1
}

event() {
  local phase="$1"
  local message="$2"
  printf 'KRONOS_EVENT\t%s\t%s\n' "$phase" "$message" >&2
}

DHCP_CONF="${KRONOS_DHCP_CONF:-/etc/dhcp/dhcpd.conf}"

[[ -n "${KRONOS_PAYLOAD_B64:-}" ]] || json_error invalid_payload "KRONOS_PAYLOAD_B64 is required"
payload_json="$(printf '%s' "$KRONOS_PAYLOAD_B64" | base64 -d)"

eval "$(
  python3 - "$payload_json" <<'PY'
import json, shlex, sys
data = json.loads(sys.argv[1])
for key in ["target_mac", "target_ip", "efi_url", "repo_url", "iso_url", "round", "kernel_variant", "arch", "tftp_root", "httpd_root", "httpd_prefix", "os_name"]:
    value = data.get(key) or ""
    print(f"{key}={shlex.quote(str(value))}")
nics = [m for m in (data.get("nics") or []) if m]
print("nics=(" + " ".join(shlex.quote(m) for m in nics) + ")")
PY
)"

[[ -n "$target_mac" ]] || json_error invalid_payload "target_mac is required"
[[ -n "$target_ip" ]] || json_error invalid_payload "target_ip is required"
# official 优先（本地 OS 树安装源，efi_url+repo_url）；official 字段缺失才走 ISO（本地 ISO 兜底）
if [[ -n "${efi_url:-}" && -n "${repo_url:-}" ]]; then
  :
else
  [[ -n "$iso_url" ]] || json_error invalid_payload "iso_url is required"
fi

event validate_payload "参数校验完成"

# --- Step 1: sync boot files ---

relative_path="radia_test/${target_ip}"
sync_efi_path="${tftp_root}/${relative_path}"
pxe_boot_file_path="${sync_efi_path}/pxeboot"

event sync_boot_files "开始同步引导文件到 TFTP"

rm -rf "${sync_efi_path}" && mkdir -p "${pxe_boot_file_path}"

# official 优先（efi_url+repo_url 齐全 → 本地 OS 树安装源）；仅 official 字段缺失才走 ISO（本地 ISO 兜底）
if [[ -z "${efi_url:-}" || -z "${repo_url:-}" ]]; then
  # --- ISO 模式：dailybuild 开发版 DVD ISO，无 official OS 树 ---
  # 如果 ISO 在本地 httpd（同机），直接用本地文件路径，不下载
  iso_file=""
  if [[ "${iso_url}" == "${httpd_prefix}"* ]]; then
    local_path="/${iso_url#${httpd_prefix}/}"
    if [[ -f "$local_path" ]]; then
      iso_file="$local_path"
      event sync_boot_files "使用本地 ISO: ${local_path}"
    fi
  fi
  # 本地 ISO（httpd 前缀或缓存）未命中则报错——不允许向 PXE 服务器下载大 ISO。
  if [[ -z "$iso_file" ]]; then
    iso_cache_dir="/var/cache/kronos-iso"
    iso_cache_key="${os_name}-${round:-nound}-${kernel_variant:-nokv}"
    cached_iso="${iso_cache_dir}/${iso_cache_key}.iso"
    if [[ -f "$cached_iso" ]]; then
      iso_file="$cached_iso"
      event sync_boot_files "使用缓存 ISO: ${cached_iso}"
    else
      json_error sync_failed "本地无 ISO（不允许从镜像站下载落 PXE 服务器）: ${iso_url}"
    fi
  fi
  # loop mount（每任务独立挂载点，finally umount）
  # 不 trap umount——kickstart 安装在 pxe-install.sh 退出后才执行（物理机 PXE 引导后），
  # 挂载点必须保留供 kickstart repo（http://<pxe>/iso/<target_ip>/）访问
  mount_point="${httpd_root}/iso/${target_ip}"
  umount "$mount_point" 2>/dev/null || true
  rm -rf "$mount_point" && mkdir -p "$mount_point"
  mount -o loop,ro "$iso_file" "$mount_point" || json_error sync_failed "mount ISO failed: ${iso_file}"
  # grubaa64.efi 用 official 版（支持 TFTP 网络引导），不从 ISO 提取
  # ISO 内 grubaa64.efi 是本地引导版，不支持 TFTP → 黑屏光标
  if [[ "$arch" == "x86_64" ]]; then
    grub_efi_name="grubx64.efi"
  else
    grub_efi_name="grubaa64.efi"
  fi
  grub_efi_url="${httpd_prefix}/repo_list/official.repo/openEuler-24.03-LTS-SP4/OS/${arch}/EFI/BOOT/${grub_efi_name}"
  wget -e robots=off -O "${sync_efi_path}/${grub_efi_name}" "${grub_efi_url}" 2>/dev/null || true
  efi_name="$grub_efi_name"
  efi_relative="${relative_path}/${efi_name}"
  # 从挂载点 images/pxeboot 取 vmlinuz/initrd
  if [[ -d "${mount_point}/images/pxeboot" ]]; then
    cp "${mount_point}/images/pxeboot/"* "$pxe_boot_file_path/" 2>/dev/null || true
  fi
  vmlinuz_file="$(cd "${pxe_boot_file_path}" && find . -name 'vmlinu*' | tail -1 || true)"
  initrd_file="$(cd "${pxe_boot_file_path}" && find . -name 'initr*' | tail -1 || true)"
  [[ -n "$vmlinuz_file" ]] || json_error sync_failed "vmlinuz not found in ISO"
  [[ -n "$initrd_file" ]] || json_error sync_failed "initrd not found in ISO"
  vmlinuz_name="$(basename "$vmlinuz_file")"
  initrd_name="$(basename "$initrd_file")"
  # kickstart repo 指向 ISO 挂载点（暴露 HTTP）
  ks_repo_url="${httpd_prefix}/iso/${target_ip}"
  event sync_boot_files "ISO 引导文件提取完成: efi=${efi_name}, vmlinuz=${vmlinuz_name}, initrd=${initrd_name}"
else
  # --- official 模式：efi_url + repo_url（现有） ---
  efi_name="$(basename "${efi_url}")"
  efi_relative="${relative_path}/${efi_name}"
  # EFI 下载失败必须显式报错：wget -O 在 403/断连时仍会创建 0 字节文件，
  # 静默继续只会让装机在 PXE 引导段黑屏，无法定位（prod 2026-09-09 SP1 事故）。
  if ! wget -e robots=off -O "${sync_efi_path}/${efi_name}" "${efi_url}" 2>/dev/null; then
    json_error sync_failed "EFI download failed: ${efi_url}"
  fi
  pxeboot_url="${repo_url}/images/pxeboot/"
  wget -e robots=off -r -nd -l1 --no-parent --reject='index.html*' \
    "${pxeboot_url}" -P "${pxe_boot_file_path}" 2>/dev/null || true
  # 只校验 EFI 非空（-f 会放过 0 字节文件）；pxeboot 递归下载保持宽容，
  # 个别文件缺失不致命，由下方 vmlinuz/initrd 存在性兜底。
  if [[ ! -s "${tftp_root}/${efi_relative}" ]]; then
    json_error sync_failed "EFI file is empty at ${tftp_root}/${efi_relative}"
  fi
  vmlinuz_file="$(cd "${pxe_boot_file_path}" && find . -name 'vmlinu*' | tail -1 || true)"
  initrd_file="$(cd "${pxe_boot_file_path}" && find . -name 'initr*' | tail -1 || true)"
  [[ -n "$vmlinuz_file" ]] || json_error sync_failed "boot kernel download failed from ${pxeboot_url}"
  [[ -n "$initrd_file" ]] || json_error sync_failed "boot initrd download failed from ${pxeboot_url}"
  vmlinuz_name="$(basename "$vmlinuz_file")"
  initrd_name="$(basename "$initrd_file")"
  ks_repo_url="${repo_url}"
  event sync_boot_files "引导文件同步完成: efi=${efi_name}, vmlinuz=${vmlinuz_name}, initrd=${initrd_name}"
fi

# --- Generate ks file ---

ks_dir="${httpd_root}/ks/radia_test"
mkdir -p "$ks_dir"
ks_path="${ks_dir}/${target_ip}.ks"

# Write ks template inline (generic, no hardware-specific device names)
cat > "$ks_path" <<'KSEOF'
#version=DEVEL
ignoredisk --only-use=sda
clearpart --all --initlabel --drives=sda
zerombr
graphical
url --url={os_repo}
keyboard --vckeymap=us --xlayouts='us'
lang en_US.UTF-8
network  --bootproto=dhcp --activate
rootpw --iscrypted $6$rounds=4096$abcdef1234567890$/dummy
firstboot --enable
skipx
timezone Asia/Shanghai --utc
autopart
reboot
%packages
@^minimal-environment
%end
%pre --interpreter=/usr/bin/bash --log=/root/ks_pre_install.log --erroronfail
dmsetup remove_all
wipefs -a --force /dev/sda
%end
%post --interpreter=/usr/bin/bash --log=/root/ks_post_install.log --erroronfail
sed -i 's/^#*PermitRootLogin.*/PermitRootLogin yes/; s/^#*PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config
ssh-keygen -A
systemctl enable sshd
mkdir -p /root
echo "{os_marker}" > /root/.kronos-install-marker
%end
KSEOF

# Replace repo URL
sed -i "s#{os_repo}#${ks_repo_url}#" "$ks_path"
# Replace install marker (os_version round)
sed -i "s#{os_marker}#${os_name} ${round:-official}#" "$ks_path"

# Write root password hash for openEuler12#$
python3 -c "
import crypt, sys
h = crypt.crypt('openEuler12#\$', salt='\$6\$rounds=4096\$kronospxe')
content = open('$ks_path').read()
content = content.replace('\$6\$rounds=4096\$abcdef1234567890\$/dummy', h)
open('$ks_path', 'w').write(content)
"

event sync_boot_files "ks 文件生成完成: ${ks_path}"

# --- Generate grub.cfg ---

grub_path="${sync_efi_path}/grub.cfg"
cat > "$grub_path" <<GRUBEOF
set timeout=5
menuentry 'install ${os_name}' {
  linux /${relative_path}/pxeboot/${vmlinuz_name} ip=dhcp inst.ks=${httpd_prefix}/ks/radia_test/${target_ip}.ks
  initrd /${relative_path}/pxeboot/${initrd_name}
}
GRUBEOF

event sync_boot_files "grub.cfg 生成完成: ${grub_path}"

# --- Step 2: bind DHCP（全部网卡都绑，避免启动网卡非主 MAC 时拿不到引导） ---

bind_macs=( "${nics[@]:-}" )
[[ ${#bind_macs[@]} -eq 0 ]] && bind_macs=( "$target_mac" )
event bind_dhcp "开始绑定 DHCP: MACs=(${bind_macs[*]}) IP=${target_ip}"

# Backup
cp -f "$DHCP_CONF" "${DHCP_CONF}.bak"

for mnic in "${bind_macs[@]}"; do
  # Clear old binding for this MAC
  mac_underscore="$(echo "$mnic" | tr ':' '_')"
  python3 - "$DHCP_CONF" "$mac_underscore" "$mnic" <<'PY'
import re, sys
conf_path, mac_u, mac = sys.argv[1], sys.argv[2], sys.argv[3]
with open(conf_path) as f:
    content = f.read()
# Remove host blocks containing this MAC
pattern = rf'host\s+{re.escape(mac_u)}\s*\{{[^}}]*\}}'
content = re.sub(pattern, '', content, flags=re.DOTALL)
# Also remove any host block containing the raw MAC
pattern2 = rf'host\s+\S+\s*\{{[^}}]*{re.escape(mac)}[^}}]*\}}'
content = re.sub(pattern2, '', content, flags=re.DOTALL)
with open(conf_path, 'w') as f:
    f.write(content)
PY

  # Append new binding
  cat >> "$DHCP_CONF" <<DHCPBIND
host ${mac_underscore} {
    filename "${efi_relative}";
    hardware ethernet ${mnic};
    fixed-address ${target_ip};
}
DHCPBIND
done

# Restart dhcpd
if ! systemctl restart dhcpd 2>/dev/null; then
  event bind_dhcp "dhcpd 重启失败，回滚配置"
  cp -f "${DHCP_CONF}.bak" "$DHCP_CONF"
  systemctl restart dhcpd 2>/dev/null || true
  json_error bind_failed "Failed to restart dhcpd after binding MAC ${target_mac}"
fi

event bind_dhcp "DHCP 绑定完成"

# --- Output ---

python3 - "$efi_relative" <<'PY'
import json, sys
print(json.dumps({"status": "ok", "efi_relative_path": sys.argv[1]}))
PY
