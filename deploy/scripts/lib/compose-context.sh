# Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
# This project is licensed under the Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
# http://license.coscl.org.cn/MulanPSL2

# shellcheck shell=bash

compose_context_fail() {
  if declare -F fail >/dev/null 2>&1; then
    fail "$1"
  fi
  printf 'Error: %s\n' "$1" >&2
  exit 1
}

validate_target_env() {
  local target_env="$1"
  [[ "$target_env" == "dev" || "$target_env" == "prod" ]] ||
    compose_context_fail "target environment must be dev or prod"
}

health_url_for_env() {
  local target_env="$1"
  if [[ "$target_env" == "dev" ]]; then
    printf 'http://127.0.0.1:8080/api/v1/health/database'
  else
    printf 'http://127.0.0.1/api/v1/health/database'
  fi
}

detect_compose_command() {
  if docker compose version >/dev/null 2>&1; then
    COMPOSE=(docker compose)
  elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE=(docker-compose)
  else
    compose_context_fail "Docker Compose is not installed"
  fi
}

set_compose_context() {
  local target_env="$1"
  local commit="${2:-}"

  validate_target_env "$target_env"

  BASE_DIR="/opt/kronos/$target_env"
  APP_DIR="$BASE_DIR/app"
  DEPLOYED_COMMIT_FILE="$BASE_DIR/deployed-commit"
  ENV_FILE="/etc/kronos/$target_env.env"
  VM_ISO_UPLOAD_HOST_DIR="/data/kronos/uploads/$target_env"
  PROJECT_NAME="kronos-$target_env"
  COMPOSE_FILE="$APP_DIR/deploy/docker-compose.server.yml"
  # shellcheck disable=SC2034
  HEALTH_URL="$(health_url_for_env "$target_env")"

  [[ -d "$APP_DIR" ]] || compose_context_fail "$APP_DIR is missing"
  [[ -r "$ENV_FILE" ]] || compose_context_fail "$ENV_FILE is missing or unreadable"

  if [[ -z "$commit" ]]; then
    if [[ -f "$DEPLOYED_COMMIT_FILE" ]]; then
      COMMIT="$(cat "$DEPLOYED_COMMIT_FILE")"
    else
      COMMIT="none"
    fi
  else
    COMMIT="$commit"
  fi

  if [[ "$COMMIT" == "none" ]]; then
    IMAGE_TAG="$target_env-none"
  else
    [[ "$COMMIT" =~ ^[0-9a-f]{40}$ ]] || compose_context_fail "commit is invalid"
    IMAGE_TAG="$target_env-${COMMIT:0:12}"
  fi

  detect_compose_command
  COMPOSE_BASE=(
    "${COMPOSE[@]}"
    --env-file "$ENV_FILE"
    -p "$PROJECT_NAME"
    -f "$COMPOSE_FILE"
  )
}

set_deployed_compose_context() {
  local target_env="$1"
  local base_dir="/opt/kronos/$target_env"
  local deployed_commit_file="$base_dir/deployed-commit"

  [[ -f "$deployed_commit_file" ]] ||
    compose_context_fail "$deployed_commit_file is missing"
  set_compose_context "$target_env" "$(cat "$deployed_commit_file")"
}

print_shell_words() {
  local arg
  local separator=''

  for arg in "$@"; do
    printf '%s%q' "$separator" "$arg"
    separator=' '
  done
}

print_shell_command() {
  print_shell_words "$@"
  printf '\n'
}

print_compose_prefix() {
  print_shell_words \
    "KRONOS_IMAGE_TAG=$IMAGE_TAG" \
    "VM_ISO_UPLOAD_HOST_DIR=$VM_ISO_UPLOAD_HOST_DIR" \
    "${COMPOSE_BASE[@]}"
}

print_compose_command() {
  print_compose_prefix
  printf ' '
  print_shell_command "$@"
}

compose() {
  KRONOS_IMAGE_TAG="$IMAGE_TAG" \
    VM_ISO_UPLOAD_HOST_DIR="$VM_ISO_UPLOAD_HOST_DIR" \
    "${COMPOSE_BASE[@]}" "$@" </dev/null
}

compose_with_stdin() {
  KRONOS_IMAGE_TAG="$IMAGE_TAG" \
    VM_ISO_UPLOAD_HOST_DIR="$VM_ISO_UPLOAD_HOST_DIR" \
    "${COMPOSE_BASE[@]}" "$@"
}
