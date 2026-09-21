# Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
# This project is licensed under the Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
# http://license.coscl.org.cn/MulanPSL2

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BRANCH="${1:-main}"

usage() {
  printf 'Usage:\n'
  printf '  dev:  scripts/deploy.sh [branch]\n'
  printf '  prod: scripts/deploy.sh\n'
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
if [[ "$TARGET_ENV" == "prod" && "$#" -ne 0 ]]; then
  fail "prod always deploys main and does not accept a branch argument"
fi

command -v git >/dev/null || fail "required command not found: git"
git check-ref-format --branch "$BRANCH" >/dev/null 2>&1 ||
  fail "invalid branch name: $BRANCH"

cd "$ROOT_DIR"

[[ "$TARGET_ENV" != "prod" || "$BRANCH" == "main" ]] ||
  fail "prod can only deploy main"

if [[ -n "$(git status --short)" ]]; then
  fail "Git working tree must be clean"
fi

printf 'Fetching origin/%s...\n' "$BRANCH"
git fetch --quiet origin "$BRANCH"

COMMIT="$(git rev-parse "origin/$BRANCH")"

OPERATOR="$(git config user.name || true)"
if [[ -z "$OPERATOR" ]]; then
  OPERATOR="${USER:-unknown}"
fi
OPERATOR="$(printf '%s' "$OPERATOR" | tr -cd '[:alnum:]_.@-')"
OPERATOR="${OPERATOR:-unknown}"

CURRENT_COMMIT="$(cat "/opt/kronos/$TARGET_ENV/deployed-commit" 2>/dev/null || printf none)"

printf '\nTarget environment: %s\n' "$TARGET_ENV"
printf 'Branch:             %s\n' "$BRANCH"
printf 'Current commit:     %s\n' "$CURRENT_COMMIT"
printf 'Target commit:      %s\n' "$COMMIT"

if [[ "$TARGET_ENV" == "prod" ]]; then
  [[ -t 0 ]] || fail "prod deployment requires an interactive terminal"
  printf 'Type prod to continue: '
  read -r confirmation
  [[ "$confirmation" == "prod" ]] || fail "prod deployment cancelled"
fi

git checkout --quiet --detach "$COMMIT"
exec bash "$ROOT_DIR/deploy/scripts/deploy-release.sh" \
  "$TARGET_ENV" \
  "$BRANCH" \
  "$COMMIT" \
  "$OPERATOR"
