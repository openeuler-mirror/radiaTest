# Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
# This project is licensed under the Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
# http://license.coscl.org.cn/MulanPSL2

#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  printf 'Error: run this script as root.\n' >&2
  exit 1
fi

running_containers=""
if command -v docker >/dev/null; then
  running_containers="$(docker ps --quiet 2>/dev/null || true)"
fi
if [[ -n "$running_containers" ]]; then
  printf 'Error: stop running containers before upgrading Docker.\n' >&2
  exit 1
fi

yum install -y curl git iptables procps-ng tar util-linux xz

CURL_OPTIONS=(
  --fail
  --location
  --retry 5
  --retry-all-errors
)

machine_arch="$(arch)"
docker_base="${DOCKER_DOWNLOAD_BASE:-https://mirrors.aliyun.com/docker-ce/linux/static/stable/${machine_arch}}"
docker_archive="$(
  curl "${CURL_OPTIONS[@]}" --silent --show-error "$docker_base/" |
    grep -oE 'docker-[0-9]+(\.[0-9]+){2}(-[0-9]+)?\.tgz' |
    sort --version-sort --unique |
    tail -n 1
)"
[[ -n "$docker_archive" ]]

buildx_arch="$(printf '%s' "$machine_arch" | sed 's/x86_64/amd64/; s/aarch64/arm64/')"
buildx_release="$(
  curl "${CURL_OPTIONS[@]}" --silent --show-error \
    'https://api.github.com/repos/docker/buildx/releases/latest'
)"
buildx_url="$(
  printf '%s' "$buildx_release" |
    grep '"browser_download_url":' |
    cut -d '"' -f 4 |
    grep "linux-${buildx_arch}$" |
    head -n 1
)"
[[ -n "$buildx_url" ]]

temp_dir="$(mktemp -d)"
trap 'rm -rf "$temp_dir"' EXIT

curl "${CURL_OPTIONS[@]}" \
  "$docker_base/$docker_archive" \
  --output "$temp_dir/docker.tgz"
curl "${CURL_OPTIONS[@]}" \
  "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-${machine_arch}" \
  --output "$temp_dir/docker-compose"
curl "${CURL_OPTIONS[@]}" \
  "$buildx_url" \
  --output "$temp_dir/docker-buildx"

tar -xzf "$temp_dir/docker.tgz" -C "$temp_dir"

systemctl stop docker.service 2>/dev/null || true
install -m 755 "$temp_dir"/docker/* /usr/local/bin/
groupadd --force docker

install -d -m 755 /usr/local/lib/docker/cli-plugins
install -m 755 \
  "$temp_dir/docker-compose" \
  /usr/local/lib/docker/cli-plugins/docker-compose
install -m 755 \
  "$temp_dir/docker-buildx" \
  /usr/local/lib/docker/cli-plugins/docker-buildx
ln -sfn /usr/local/lib/docker/cli-plugins/docker-compose /usr/local/bin/docker-compose

cat >/etc/systemd/system/docker.service <<'EOF'
[Unit]
Description=Docker Application Container Engine
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/local/bin/dockerd
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=2
LimitNOFILE=infinity
TasksMax=infinity
Delegate=yes
KillMode=process

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now docker.service

sleep 3

docker version
docker buildx version
docker compose version
docker run --rm hello-world
