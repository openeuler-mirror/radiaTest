# Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
# This project is licensed under the Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
# http://license.coscl.org.cn/MulanPSL2

#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

TARGET_ENV="${1:-}"
BRANCH="${2:-}"
COMMIT="${3:-}"
OPERATOR="${4:-unknown}"
HTTPS_REPOSITORY_URL="${KRONOS_REPOSITORY_URL:-https://gitcode.com/xu_yishen/kronos.git}"

fail() {
  printf 'Error: %s\n' "$1" >&2
  return 1
}

if [[ "$TARGET_ENV" != "dev" && "$TARGET_ENV" != "prod" ]]; then
  fail "target environment must be dev or prod"
fi
[[ "$BRANCH" =~ ^[A-Za-z0-9._/-]+$ ]] || fail "invalid branch name"
[[ "$COMMIT" =~ ^[0-9a-f]{40}$ ]] || fail "commit must be a full SHA-1"
[[ "$OPERATOR" =~ ^[[:alnum:]_.@-]+$ ]] || fail "invalid operator"

BASE_DIR="/opt/kronos/$TARGET_ENV"
APP_DIR="$BASE_DIR/app"
LOCK_FILE="$BASE_DIR/deploy.lock"
HISTORY_FILE="$BASE_DIR/deployments.jsonl"
DEPLOYED_COMMIT_FILE="$BASE_DIR/deployed-commit"
ENV_FILE="/etc/kronos/$TARGET_ENV.env"
BACKUP_FILE=""
STAGE="initialization"

mkdir -p "$BASE_DIR"
exec 9>"$LOCK_FILE"
flock -n 9 || fail "another $TARGET_ENV deployment is already running"

record_deployment() {
  local result="$1"
  local stage="$2"
  local timestamp
  timestamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf \
    '{"time":"%s","environment":"%s","branch":"%s","commit":"%s","operator":"%s","result":"%s","stage":"%s"}\n' \
    "$timestamp" \
    "$TARGET_ENV" \
    "$BRANCH" \
    "$COMMIT" \
    "$OPERATOR" \
    "$result" \
    "$stage" \
    >>"$HISTORY_FILE"
}

show_diagnostics() {
  set +e
  printf '\nDeployment failed during: %s\n' "$STAGE" >&2
  if [[ -n "$BACKUP_FILE" ]]; then
    printf 'Database backup: %s\n' "$BACKUP_FILE" >&2
  fi
  if declare -F compose >/dev/null 2>&1 &&
    [[ -f "${COMPOSE_FILE:-}" && -r "$ENV_FILE" ]]; then
    compose ps >&2
    if [[ "$STAGE" != "image build" ]]; then
      compose logs --tail=200 backend worker beat bot nginx postgres redis >&2
    fi
  fi
}

on_error() {
  local status=$?
  trap - ERR
  record_deployment failed "$STAGE"
  show_diagnostics
  exit "$status"
}
trap on_error ERR

STAGE="configuration validation"
[[ -d "$APP_DIR/.git" ]] || fail "$APP_DIR is not an initialized Git repository"
[[ -r "$ENV_FILE" ]] || fail "$ENV_FILE is missing or unreadable"

ENV_MODE="$(stat -c '%a' "$ENV_FILE")"
[[ "$ENV_MODE" == "600" || "$ENV_MODE" == "640" ]] ||
  fail "$ENV_FILE must have mode 600 or 640"

for variable in \
  APP_ENV \
  DATABASE_URL \
  JWT_SECRET_KEY \
  RESOURCE_SECRET_KEY \
  POSTGRES_DB \
  POSTGRES_PASSWORD \
  POSTGRES_USER \
  CELERY_WORKER_CONCURRENCY \
  WEB_PORT; do
  grep -Eq "^${variable}=.+$" "$ENV_FILE" ||
    fail "$ENV_FILE has an empty or missing $variable"
done

grep -Eq '^CELERY_WORKER_CONCURRENCY=[1-9][0-9]*$' "$ENV_FILE" ||
  fail "$ENV_FILE must set CELERY_WORKER_CONCURRENCY to a positive integer"

for secret_var in JWT_SECRET_KEY RESOURCE_SECRET_KEY POSTGRES_PASSWORD DATABASE_URL; do
  if grep -qiE "^${secret_var}=.*change-me" "$ENV_FILE"; then
    fail "$ENV_FILE: $secret_var must not use the change-me placeholder"
  fi
done

if [[ "$TARGET_ENV" == "dev" ]]; then
  grep -Eq '^APP_ENV=development$' "$ENV_FILE" ||
    fail "dev.env must set APP_ENV=development"
  grep -Eq '^POSTGRES_DB=kronos_dev$' "$ENV_FILE" ||
    fail "dev.env must set POSTGRES_DB=kronos_dev"
  grep -Eq '^WEB_PORT=8080$' "$ENV_FILE" ||
    fail "dev.env must set WEB_PORT=8080"
  grep -Eq '^CELERY_WORKER_CONCURRENCY=[1-9][0-9]*$' "$ENV_FILE" ||
    fail "dev.env must set CELERY_WORKER_CONCURRENCY to a positive integer"
else
  grep -Eq '^APP_ENV=production$' "$ENV_FILE" ||
    fail "prod.env must set APP_ENV=production"
  grep -Eq '^POSTGRES_DB=kronos_prod$' "$ENV_FILE" ||
    fail "prod.env must set POSTGRES_DB=kronos_prod"
  grep -Eq '^WEB_PORT=80$' "$ENV_FILE" ||
    fail "prod.env must set WEB_PORT=80"
  grep -Eq '^CELERY_WORKER_CONCURRENCY=[1-9][0-9]*$' "$ENV_FILE" ||
    fail "prod.env must set CELERY_WORKER_CONCURRENCY to a positive integer"
fi

cd "$APP_DIR"
ORIGIN_URL="$(git remote get-url origin)"
[[ "$ORIGIN_URL" == "$HTTPS_REPOSITORY_URL" ]] ||
  fail "origin must be $HTTPS_REPOSITORY_URL"

STAGE="Git checkout"
git fetch --quiet --prune origin "$BRANCH"
REMOTE_COMMIT="$(git rev-parse "origin/$BRANCH")"
[[ "$REMOTE_COMMIT" == "$COMMIT" ]] ||
  fail "target commit does not match origin/$BRANCH"
git checkout --quiet --detach "$COMMIT"

STAGE="deployment context"
# shellcheck source=deploy/scripts/lib/compose-context.sh
source "$APP_DIR/deploy/scripts/lib/compose-context.sh"
set_compose_context "$TARGET_ENV" "$COMMIT"
# shellcheck source=deploy/scripts/lib/storage-guard.sh
source "$APP_DIR/deploy/scripts/lib/storage-guard.sh"

STAGE="storage preflight"
storage_guard_preflight "$TARGET_ENV"
install -d -m 755 "$VM_ISO_UPLOAD_HOST_DIR"

STAGE="image build"
compose build backend nginx

STAGE="nginx configuration validation"
docker run --rm \
  --add-host backend:127.0.0.1 \
  "kronos-frontend:$IMAGE_TAG" \
  nginx -t

STAGE="PostgreSQL and Redis startup"
compose up -d postgres redis
for _ in {1..30}; do
  # shellcheck disable=SC2016
  if compose exec -T postgres sh -c \
    'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
    >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
# shellcheck disable=SC2016
compose exec -T postgres sh -c \
  'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  >/dev/null

STAGE="application stop"
compose stop nginx backend worker beat bot

if [[ "$TARGET_ENV" == "prod" ]]; then
  STAGE="database backup"
  BACKUP_DIR="/data/backups/kronos/prod"
  mkdir -p "$BACKUP_DIR"
  BACKUP_FILE="$BACKUP_DIR/$(date -u +%Y%m%dT%H%M%SZ)-${COMMIT:0:12}.dump"
  # shellcheck disable=SC2016
  compose exec -T postgres sh -c \
    'exec pg_dump -Fc -U "$POSTGRES_USER" "$POSTGRES_DB"' \
    >"$BACKUP_FILE"
  [[ -s "$BACKUP_FILE" ]] || fail "database backup is empty"
fi

STAGE="database migration"
compose run --rm --no-deps backend alembic upgrade head

STAGE="pipeline template seed"
compose run --rm --no-deps backend python -m app.cli seed-pipeline-templates

STAGE="admin seed"
compose run --rm --no-deps backend python -m app.cli seed-admin

STAGE="install images seed"
SEED_IMAGES_FILE="/etc/kronos/install-images.json"
if [[ -f "$SEED_IMAGES_FILE" ]]; then
  compose_with_stdin run --rm --no-deps -T backend \
    python -m app.cli seed-install-images --json-file - \
    <"$SEED_IMAGES_FILE"
else
  printf 'Skipping install images seed: %s not found\n' \
    "$SEED_IMAGES_FILE"
fi

STAGE="RC install images seed"
compose run --rm --no-deps backend python -m app.cli seed-rc-install-images

STAGE="task event cleanup"
compose run --rm --no-deps backend python -m app.cli cleanup-task-events --days 30

STAGE="idempotency record cleanup"
compose run --rm --no-deps backend python -m app.cli cleanup-idempotency-records --days 7

STAGE="application startup"
compose up -d --no-deps backend worker beat bot nginx

STAGE="health check"
healthy=false
for _ in {1..30}; do
  if curl --fail --silent --show-error --max-time 3 "$HEALTH_URL" >/dev/null; then
    healthy=true
    break
  fi
  sleep 2
done
[[ "$healthy" == "true" ]] || fail "health check failed: $HEALTH_URL"

STAGE="worker check"
compose ps worker | grep -Eq '(Up|running)' || fail "worker is not running"

STAGE="beat check"
compose ps beat | grep -Eq '(Up|running)' || fail "beat is not running"

STAGE="bot check"
compose ps bot | grep -Eq '(Up|running)' || fail "bot is not running"

STAGE="success recording"
DEPLOYED_COMMIT_TMP="$DEPLOYED_COMMIT_FILE.tmp.$$"
printf '%s\n' "$COMMIT" >"$DEPLOYED_COMMIT_TMP"
mv "$DEPLOYED_COMMIT_TMP" "$DEPLOYED_COMMIT_FILE"
record_deployment success completed

if [[ "$TARGET_ENV" == "prod" ]]; then
  find /data/backups/kronos/prod \
    -type f \
    -name '*.dump' \
    ! -name 'manual-*' \
    -mtime +30 \
    -delete
fi

trap - ERR
printf 'Deployment succeeded: %s %s\n' "$TARGET_ENV" "$COMMIT"
