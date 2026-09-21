# Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
# This project is licensed under the Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
# http://license.coscl.org.cn/MulanPSL2

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SHOW_LOGS="${1:-}"

usage() {
  printf 'Usage: scripts/status.sh [--logs]\n'
}

fail() {
  printf 'Error: %s\n' "$1" >&2
  exit 1
}

case "$ROOT_DIR" in
  /opt/kronos/dev/app)
    TARGET_ENV="dev"
    ;;
  /opt/kronos/prod/app)
    TARGET_ENV="prod"
    ;;
  *)
    fail "run this script from /opt/kronos/dev/app or /opt/kronos/prod/app"
    ;;
esac

[[ "$#" -le 1 ]] || {
  usage >&2
  exit 2
}
if [[ -n "$SHOW_LOGS" && "$SHOW_LOGS" != "--logs" ]]; then
  usage >&2
  exit 2
fi

if [[ "$SHOW_LOGS" == "--logs" ]]; then
  exec "$ROOT_DIR/deploy/scripts/status.sh" "$TARGET_ENV" "$SHOW_LOGS"
fi
exec "$ROOT_DIR/deploy/scripts/status.sh" "$TARGET_ENV"
