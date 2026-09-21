# Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
# This project is licensed under the Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
# http://license.coscl.org.cn/MulanPSL2

#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=deploy/scripts/lib/compose-context.sh
source "$SCRIPT_DIR/lib/compose-context.sh"

TARGET_ENV="${1:-}"

usage() {
  printf 'Usage: deploy/scripts/app-cli.sh <dev|prod> <app.cli command> [args...]\n'
}

fail() {
  printf 'Error: %s\n' "$1" >&2
  exit 1
}

if [[ "$TARGET_ENV" != "dev" && "$TARGET_ENV" != "prod" ]]; then
  usage >&2
  exit 2
fi
shift
if [[ "$#" -eq 0 ]]; then
  usage >&2
  exit 2
fi

set_deployed_compose_context "$TARGET_ENV"

RUN_ARGS=(run --rm --no-deps)
if [[ ! -t 0 ]]; then
  RUN_ARGS+=(-T)
fi

cd "$APP_DIR"

compose_with_stdin "${RUN_ARGS[@]}" backend python -m app.cli "$@"
