# Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
# This project is licensed under the Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
# http://license.coscl.org.cn/MulanPSL2

#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=deploy/scripts/lib/compose-context.sh
source "$SCRIPT_DIR/lib/compose-context.sh"
# shellcheck source=deploy/scripts/lib/storage-guard.sh
source "$SCRIPT_DIR/lib/storage-guard.sh"

TARGET_ENV="${1:-}"
SHOW_LOGS="${2:-}"
LOG_LINES="${LOG_LINES:-80}"

usage() {
  printf 'Usage: deploy/scripts/status.sh <dev|prod> [--logs]\n'
}

fail() {
  printf 'Error: %s\n' "$1" >&2
  exit 1
}

if [[ "$TARGET_ENV" != "dev" && "$TARGET_ENV" != "prod" ]]; then
  usage >&2
  exit 2
fi
if [[ -n "$SHOW_LOGS" && "$SHOW_LOGS" != "--logs" ]]; then
  usage >&2
  exit 2
fi

set_compose_context "$TARGET_ENV"

printf 'Environment: %s\n' "$TARGET_ENV"
printf 'Deployed commit: %s\n' "$COMMIT"
printf 'Image tag: %s\n' "$IMAGE_TAG"
printf 'Health URL: %s\n' "$HEALTH_URL"

printf '\nCommands:\n'
printf '  '
print_compose_command ps
printf '  '
print_shell_command curl --fail --silent --show-error --max-time 5 "$HEALTH_URL"
if [[ "$SHOW_LOGS" == "--logs" ]]; then
  printf '  '
  print_compose_command logs --tail="$LOG_LINES" backend worker beat bot nginx postgres redis
fi

printf '\nRecent deployments:\n'
tail -n 5 "$BASE_DIR/deployments.jsonl" 2>/dev/null || true

printf '\nContainers:\n'
compose ps

printf '\nHealth:\n'
curl --fail --silent --show-error --max-time 5 "$HEALTH_URL"
printf '\n'

storage_guard_report

printf '\nDatabase growth tables:\n'
# shellcheck disable=SC2016
compose exec -T postgres sh -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -P pager=off -c "
    select
      relname as table_name,
      n_live_tup as estimated_rows,
      pg_size_pretty(pg_total_relation_size(relid)) as total_size
    from pg_stat_user_tables
    where relname in ('\''audit_logs'\'','\''task_events'\'','\''idempotency_records'\'','\''notifications'\'')
    order by relname;
  "' || true

if [[ "$SHOW_LOGS" == "--logs" ]]; then
  printf '\nLogs:\n'
  compose logs --tail="$LOG_LINES" backend worker beat bot nginx postgres redis
fi
