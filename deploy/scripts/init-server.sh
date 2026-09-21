# Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
# This project is licensed under the Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
# http://license.coscl.org.cn/MulanPSL2

#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

REPOSITORY_URL="${KRONOS_REPOSITORY_URL:-https://gitcode.com/xu_yishen/kronos.git}"
DEV_APP_DIR="/opt/kronos/dev/app"
PROD_APP_DIR="/opt/kronos/prod/app"
ENV_DIR="/etc/kronos"
SSH_DIR="/etc/kronos/ssh"
BACKUP_DIR="/data/backups/kronos/prod"
DEV_ISO_UPLOAD_DIR="/data/kronos/uploads/dev"
PROD_ISO_UPLOAD_DIR="/data/kronos/uploads/prod"

log() {
  printf '\n==> %s\n' "$1"
}

fail() {
  printf 'Error: %s\n' "$1" >&2
  exit 1
}

require_root() {
  [[ "$(id -u)" -eq 0 ]] || fail "run this script as root"
}

install_packages() {
  log "install packages"
  yum install -y curl git openssl util-linux
}

create_directories() {
  log "create directories"
  install -d -m 755 "$DEV_APP_DIR" "$PROD_APP_DIR"
  install -d -m 755 "$DEV_ISO_UPLOAD_DIR" "$PROD_ISO_UPLOAD_DIR"
  install -d -m 700 "$ENV_DIR" "$SSH_DIR" "$BACKUP_DIR"
}

normalize_ownership() {
  log "normalize ownership"
  chown -R root:root "$DEV_APP_DIR" "$PROD_APP_DIR"
  chown root:root \
    "$ENV_DIR" \
    "$SSH_DIR" \
    "$BACKUP_DIR" \
    "$DEV_ISO_UPLOAD_DIR" \
    "$PROD_ISO_UPLOAD_DIR"
}

ensure_repository() {
  local app_dir="$1"

  if [[ -d "$app_dir/.git" ]]; then
    git -C "$app_dir" remote set-url origin "$REPOSITORY_URL"
    git -C "$app_dir" fetch --quiet --prune origin
    git -C "$app_dir" checkout --quiet -B main origin/main
    return
  fi

  if [[ -n "$(find "$app_dir" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
    fail "$app_dir exists but is not an empty Git repository"
  fi

  git clone "$REPOSITORY_URL" "$app_dir"
}

clone_repositories() {
  log "verify GitCode access"
  git ls-remote "$REPOSITORY_URL" HEAD >/dev/null

  log "clone repositories"
  ensure_repository "$DEV_APP_DIR"
  ensure_repository "$PROD_APP_DIR"
}

docker_ready() {
  command -v docker >/dev/null &&
    docker ps >/dev/null 2>&1 &&
    docker compose version >/dev/null 2>&1 &&
    docker buildx version >/dev/null 2>&1
}

install_docker() {
  if docker_ready; then
    log "docker already installed"
    docker version
    docker compose version
    docker buildx version
    return
  fi

  log "install docker"
  bash "$DEV_APP_DIR/deploy/scripts/install-docker.sh"
}

replace_env_value() {
  local file="$1"
  local key="$2"
  local value="$3"

  sed -i "s|^${key}=.*|${key}=${value}|" "$file"
}

create_env_file() {
  local target_env="$1"
  local app_env="$2"
  local web_port="$3"
  local database_name="$4"
  local worker_concurrency="$5"
  local env_file="$ENV_DIR/${target_env}.env"
  local postgres_password
  local jwt_secret_key
  local resource_secret_key
  local database_url

  if [[ -e "$env_file" ]]; then
    log "keep existing $env_file"
    if ! grep -Eq '^RESOURCE_SECRET_KEY=.+$' "$env_file"; then
      resource_secret_key="$(openssl rand -base64 32 | tr '+/' '-_')"
      printf 'RESOURCE_SECRET_KEY=%s\n' "$resource_secret_key" >>"$env_file"
    fi
    if ! grep -Eq '^ADMIN_PASSWORD=.+$' "$env_file"; then
      printf 'ADMIN_USERNAME=admin\nADMIN_PASSWORD=openEuler12#$\n' >>"$env_file"
    fi
    chmod 600 "$env_file"
    chown root:root "$env_file"
    return
  fi

  log "create $env_file"
  cp "$DEV_APP_DIR/deploy/server.env.example" "$env_file"

  postgres_password="$(openssl rand -hex 24)"
  jwt_secret_key="$(openssl rand -hex 32)"
  resource_secret_key="$(openssl rand -base64 32 | tr '+/' '-_')"
  database_url="postgresql+psycopg://kronos:${postgres_password}@postgres:5432/${database_name}"

  replace_env_value "$env_file" "APP_ENV" "$app_env"
  replace_env_value "$env_file" "WEB_PORT" "$web_port"
  replace_env_value "$env_file" "POSTGRES_DB" "$database_name"
  replace_env_value "$env_file" "POSTGRES_PASSWORD" "$postgres_password"
  replace_env_value "$env_file" "DATABASE_URL" "$database_url"
  replace_env_value "$env_file" "JWT_SECRET_KEY" "$jwt_secret_key"
  replace_env_value "$env_file" "RESOURCE_SECRET_KEY" "$resource_secret_key"
  replace_env_value "$env_file" "CELERY_WORKER_CONCURRENCY" "$worker_concurrency"

  chown root:root "$env_file"
  chmod 600 "$env_file"
}

create_env_files() {
  create_env_file "dev" "development" "8080" "kronos_dev" "100"
  create_env_file "prod" "production" "80" "kronos_prod" "100"
}

main() {
  require_root
  install_packages
  create_directories
  normalize_ownership
  clone_repositories
  install_docker
  create_env_files

  log "done"
  printf 'Next step on the server:\n'
  printf '  cd /opt/kronos/dev/app && ./scripts/deploy.sh\n'
}

main "$@"
