# Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
# This project is licensed under the Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
# http://license.coscl.org.cn/MulanPSL2

#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=deploy/scripts/lib/compose-context.sh
source "$SCRIPT_DIR/lib/compose-context.sh"

ACTION="${1:-}"
TARGET_ENV="${2:-}"
BACKUP_FILE="${3:-}"
CONFIRMATION="${4:-}"

usage() {
  cat <<'EOF'
Usage:
  deploy/scripts/db.sh backup prod
  deploy/scripts/db.sh restore prod /data/backups/kronos/prod/<backup>.dump prod
EOF
}

fail() {
  printf 'Error: %s\n' "$1" >&2
  exit 1
}

if [[ "$ACTION" != "backup" && "$ACTION" != "restore" ]]; then
  usage >&2
  exit 2
fi
if [[ "$TARGET_ENV" != "prod" ]]; then
  usage >&2
  exit 2
fi
if [[ "$ACTION" == "restore" ]]; then
  if [[ -z "$BACKUP_FILE" || "$CONFIRMATION" != "prod" ]]; then
    usage >&2
    exit 2
  fi
  case "$BACKUP_FILE" in
    /data/backups/kronos/prod/*.dump) ;;
    *) fail "backup file must be under /data/backups/kronos/prod and end with .dump" ;;
  esac
else
  if [[ -n "$BACKUP_FILE" || -n "$CONFIRMATION" ]]; then
    usage >&2
    exit 2
  fi
fi

set_deployed_compose_context "$TARGET_ENV"

LOCK_FILE="$BASE_DIR/deploy.lock"
BACKUP_DIR="/data/backups/kronos/prod"

if [[ "$ACTION" == "restore" ]]; then
  [[ -s "$BACKUP_FILE" ]] || fail "$BACKUP_FILE is missing or empty"
fi

exec 9>"$LOCK_FILE"
flock -n 9 || fail "another prod deployment, backup, or restore is already running"

wait_for_postgres() {
  compose up -d postgres
  for _ in {1..30}; do
    # shellcheck disable=SC2016
    if compose exec -T postgres sh -c \
      'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
      >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  # shellcheck disable=SC2016
  compose exec -T postgres sh -c \
    'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
    >/dev/null
}

backup_prod() {
  mkdir -p "$BACKUP_DIR"
  BACKUP_FILE="$BACKUP_DIR/manual-$(date -u +%Y%m%dT%H%M%SZ).dump"

  printf 'Environment: prod\n'
  printf 'Deployed commit: %s\n' "$COMMIT"
  printf 'Image tag: %s\n' "$IMAGE_TAG"
  printf 'Backup file: %s\n' "$BACKUP_FILE"

  printf '\nCommands:\n'
  printf '  '
  print_compose_prefix
  printf " exec -T postgres sh -c 'exec pg_dump -Fc -U \"\$POSTGRES_USER\" \"\$POSTGRES_DB\"' > "
  printf '%q\n' "$BACKUP_FILE"
  printf '  test -s %q\n' "$BACKUP_FILE"

  printf '\nCreating backup...\n'
  wait_for_postgres
  # shellcheck disable=SC2016
  compose exec -T postgres sh -c \
    'exec pg_dump -Fc -U "$POSTGRES_USER" "$POSTGRES_DB"' \
    >"$BACKUP_FILE"
  [[ -s "$BACKUP_FILE" ]] || fail "database backup is empty"

  printf 'Backup created: %s\n' "$BACKUP_FILE"
}

restore_prod() {
  printf 'Environment: prod\n'
  printf 'Deployed commit: %s\n' "$COMMIT"
  printf 'Image tag: %s\n' "$IMAGE_TAG"
  printf 'Backup file: %s\n' "$BACKUP_FILE"
  printf 'Health URL: %s\n' "$HEALTH_URL"

  printf '\nCommands:\n'
  printf '  '
  print_compose_command stop nginx backend
  printf '  '
  print_compose_prefix
  printf " exec -T postgres sh -c 'dropdb --force --if-exists -U \"\$POSTGRES_USER\" \"\$POSTGRES_DB\" && createdb -U \"\$POSTGRES_USER\" \"\$POSTGRES_DB\"'\n"
  printf '  '
  print_shell_words cat "$BACKUP_FILE"
  printf ' | '
  print_compose_prefix
  printf " exec -T postgres sh -c 'pg_restore -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\"'\n"
  printf '  '
  print_compose_command up -d --no-deps backend nginx
  printf '  '
  print_shell_command curl --fail --silent --show-error --max-time 3 "$HEALTH_URL"

  printf '\nRestoring database...\n'
  wait_for_postgres
  compose stop nginx backend
  # shellcheck disable=SC2016
  compose exec -T postgres sh -c \
    'dropdb --force --if-exists -U "$POSTGRES_USER" "$POSTGRES_DB" &&
     createdb -U "$POSTGRES_USER" "$POSTGRES_DB"'
  # shellcheck disable=SC2016
  compose_with_stdin exec -T postgres sh -c \
    'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
    <"$BACKUP_FILE"
  compose up -d --no-deps backend nginx

  healthy=false
  for _ in {1..30}; do
    if curl --fail --silent --show-error --max-time 3 "$HEALTH_URL" >/dev/null; then
      healthy=true
      break
    fi
    sleep 2
  done
  [[ "$healthy" == "true" ]] || fail "health check failed: $HEALTH_URL"

  printf 'Restore completed: %s\n' "$BACKUP_FILE"
}

case "$ACTION" in
  backup)
    backup_prod
    ;;
  restore)
    restore_prod
    ;;
esac
