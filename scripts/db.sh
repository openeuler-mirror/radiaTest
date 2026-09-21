# Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
# This project is licensed under the Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
# http://license.coscl.org.cn/MulanPSL2

#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-}"
BACKUP_FILE="${2:-}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  cat <<'EOF'
Usage:
  scripts/db.sh backup
  scripts/db.sh restore /data/backups/kronos/prod/<backup>.dump
EOF
}

fail() {
  printf 'Error: %s\n' "$1" >&2
  exit 1
}

[[ "$ROOT_DIR" == "/opt/kronos/prod/app" ]] ||
  fail "run this script from /opt/kronos/prod/app"

if [[ "$ACTION" != "backup" && "$ACTION" != "restore" ]]; then
  usage >&2
  exit 2
fi
if [[ "$ACTION" == "restore" && "$#" -ne 2 ]]; then
  usage >&2
  exit 2
fi
if [[ "$ACTION" == "backup" && "$#" -ne 1 ]]; then
  usage >&2
  exit 2
fi

CONFIRMATION=""
if [[ "$ACTION" == "restore" ]]; then
  [[ -t 0 ]] || fail "restore requires an interactive terminal"
  printf 'This will overwrite the prod database with %s.\n' "$BACKUP_FILE"
  printf 'Type prod to continue: '
  read -r CONFIRMATION
  [[ "$CONFIRMATION" == "prod" ]] || fail "restore cancelled"
fi

exec "$ROOT_DIR/deploy/scripts/db.sh" \
  "$ACTION" \
  "prod" \
  "$BACKUP_FILE" \
  "$CONFIRMATION"
