# Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
# This project is licensed under the Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
# http://license.coscl.org.cn/MulanPSL2

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-all}"
export UV_CACHE_DIR="${UV_CACHE_DIR:-${TMPDIR:-/tmp}/kronos-uv-cache}"

log() {
  printf '\n==> %s\n' "$1"
}

check_backend() {
  log "backend"
  cd "$ROOT_DIR/backend"
  uv run ruff check app tests alembic
  uv run python -m compileall -q app alembic
  uv run pytest
}

check_frontend() {
  log "frontend"
  if [[ ! -f "$ROOT_DIR/frontend/package.json" ]]; then
    printf 'frontend/package.json not found; skipping frontend checks.\n'
    return 0
  fi

  cd "$ROOT_DIR/frontend"
  local corepack_shim_dir
  corepack_shim_dir="${TMPDIR:-/tmp}/kronos-corepack-shims"
  mkdir -p "$corepack_shim_dir"
  corepack enable --install-directory "$corepack_shim_dir"
  export PATH="$corepack_shim_dir:$PATH"

  if [[ "${FRONTEND_INSTALL:-auto}" == "1" || ! -x node_modules/.bin/vue-tsc ]]; then
    CI=true pnpm install --frozen-lockfile
  else
    printf 'frontend dependencies found; skipping pnpm install.\n'
    printf 'Set FRONTEND_INSTALL=1 to reinstall dependencies.\n'
  fi
  pnpm typecheck
  pnpm lint
  pnpm vitest run apps/web-antd/src
  pnpm build
}

check_docs() {
  log "docs"
  cd "$ROOT_DIR"

  if find . -type f -name '*.md' \
    -not -path './.git/*' \
    -not -path './backend/.venv/*' \
    -not -path './frontend/node_modules/*' \
    -print0 \
    | xargs -0 grep -nE '今天|昨天|刚刚|最近|上周|today|yesterday|recently'; then
    printf 'Relative time wording found in docs. Use absolute dates or stable wording.\n' >&2
    return 1
  fi

  if git ls-files | grep -E '(^|/)\.env($|\.)' | grep -v '\.env.example$'; then
    printf 'Tracked .env file found. Commit .env.example only.\n' >&2
    return 1
  fi

  if git ls-files | grep -E '(^|/)(package-lock.json|yarn.lock|bun.lock)$'; then
    printf 'Unexpected frontend lockfile found. Use pnpm-lock.yaml only.\n' >&2
    return 1
  fi
}

check_scripts() {
  log "scripts"
  cd "$ROOT_DIR"

  local shell_scripts=(
    scripts/*.sh
    deploy/scripts/*.sh
  )
  if [[ -d deploy/scripts/lib ]]; then
    shell_scripts+=(deploy/scripts/lib/*.sh)
  fi
  if [[ -d backend/app/modules/vms/host_scripts ]]; then
    shell_scripts+=(backend/app/modules/vms/host_scripts/*.sh)
  fi

  bash -n "${shell_scripts[@]}"
  if command -v shellcheck >/dev/null; then
    shellcheck -x "${shell_scripts[@]}"
  else
    printf 'shellcheck not found; syntax checks completed.\n'
  fi
}

check_all() {
  check_docs
  check_scripts
  check_backend
  check_frontend
}

usage() {
  cat <<'EOF'
Usage: scripts/check.sh [all|backend|frontend|docs|scripts|quick]

Modes:
  all       Run every available check. Default.
  backend   Run backend lint, syntax, and tests.
  frontend  Run frontend checks when frontend exists.
  docs      Run documentation hygiene checks.
  scripts   Run shell script syntax and ShellCheck when available.
  quick     Run fast pre-commit-friendly checks.
EOF
}

case "$MODE" in
  all)
    check_all
    ;;
  backend)
    check_backend
    ;;
  frontend)
    check_frontend
    ;;
  docs)
    check_docs
    ;;
  scripts)
    check_scripts
    ;;
  quick)
    check_docs
    check_scripts
    check_backend
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
