# Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
# This project is licensed under the Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
# http://license.coscl.org.cn/MulanPSL2

# shellcheck shell=bash

STORAGE_GUARD_MIN_AVAILABLE_GB="${STORAGE_GUARD_MIN_AVAILABLE_GB:-10}"
STORAGE_GUARD_MAX_USED_PERCENT="${STORAGE_GUARD_MAX_USED_PERCENT:-90}"
STORAGE_GUARD_BUILD_CACHE_WARN_GB="${STORAGE_GUARD_BUILD_CACHE_WARN_GB:-20}"

storage_guard_fail() {
  if declare -F fail >/dev/null 2>&1; then
    fail "$1"
  fi
  printf 'Error: %s\n' "$1" >&2
  exit 1
}

storage_guard_docker_root() {
  docker info --format '{{.DockerRootDir}}' 2>/dev/null || true
}

storage_guard_postgres_volume() {
  local volume_name="${PROJECT_NAME:-}_postgres_data"
  if [[ -z "${PROJECT_NAME:-}" ]]; then
    return 0
  fi
  docker volume inspect "$volume_name" --format '{{.Mountpoint}}' 2>/dev/null || true
}

storage_guard_unique_paths() {
  local seen=""
  local path

  for path in "$@"; do
    [[ -n "$path" && -e "$path" ]] || continue
    case ":$seen:" in
      *":$path:"*) ;;
      *)
        printf '%s\n' "$path"
        seen="$seen:$path"
        ;;
    esac
  done
}

storage_guard_size_to_gb() {
  local raw="$1"
  local number unit
  number="$(printf '%s' "$raw" | sed -E 's/^([0-9.]+).*/\1/')"
  unit="$(printf '%s' "$raw" | sed -E 's/^[0-9.]+[[:space:]]*//; s/i?B$//')"
  awk -v number="$number" -v unit="$unit" '
    BEGIN {
      if (unit == "T") print number * 1024;
      else if (unit == "G") print number;
      else if (unit == "M") print number / 1024;
      else if (unit == "k" || unit == "K") print number / 1024 / 1024;
      else print number / 1024 / 1024 / 1024;
    }
  '
}

storage_guard_build_cache_gb() {
  local line size
  line="$(docker system df --format '{{json .}}' 2>/dev/null | grep '"Type":"Build Cache"' || true)"
  [[ -n "$line" ]] || return 0
  size="$(printf '%s' "$line" | sed -E 's/.*"Size":"([^"]+)".*/\1/')"
  [[ -n "$size" ]] || return 0
  storage_guard_size_to_gb "$size"
}

storage_guard_warn_build_cache() {
  local cache_gb
  cache_gb="$(storage_guard_build_cache_gb)"
  [[ -n "$cache_gb" ]] || return 0
  awk \
    -v cache="$cache_gb" \
    -v threshold="$STORAGE_GUARD_BUILD_CACHE_WARN_GB" \
    'BEGIN { exit !(cache > threshold) }' ||
    return 0

  printf '\nWarning: Docker build cache is %.1fGB, above %sGB.\n' \
    "$cache_gb" \
    "$STORAGE_GUARD_BUILD_CACHE_WARN_GB"
  printf 'Suggested manual cleanup after confirming no build is running:\n'
  printf '  docker builder prune --filter until=720h\n'
  printf '  docker image prune --filter until=720h\n'
}

storage_guard_check_path() {
  local label="$1"
  local path="$2"
  local min_available_kb=$((STORAGE_GUARD_MIN_AVAILABLE_GB * 1024 * 1024))
  local available_kb used_percent

  [[ -e "$path" ]] || return 0
  available_kb="$(df -Pk "$path" | awk 'NR == 2 { print $4 }')"
  used_percent="$(df -Pk "$path" | awk 'NR == 2 { gsub("%", "", $5); print $5 }')"

  if [[ "$available_kb" -lt "$min_available_kb" ]]; then
    printf 'Storage guard failed: %s (%s) has less than %sGB available.\n' \
      "$label" \
      "$path" \
      "$STORAGE_GUARD_MIN_AVAILABLE_GB" \
      >&2
    return 1
  fi

  if [[ "$used_percent" -ge "$STORAGE_GUARD_MAX_USED_PERCENT" ]]; then
    printf 'Storage guard failed: %s (%s) is %s%% used; limit is %s%%.\n' \
      "$label" \
      "$path" \
      "$used_percent" \
      "$STORAGE_GUARD_MAX_USED_PERCENT" \
      >&2
    return 1
  fi
}

storage_guard_report() {
  local docker_root postgres_volume
  local -a paths
  docker_root="$(storage_guard_docker_root)"
  postgres_volume="$(storage_guard_postgres_volume)"

  printf '\nStorage:\n'
  printf 'DockerRootDir: %s\n' "${docker_root:-unknown}"

  mapfile -t paths < <(storage_guard_unique_paths / /data "$docker_root" "$postgres_volume")
  if [[ "${#paths[@]}" -gt 0 ]]; then
    df -h "${paths[@]}"
  fi

  printf '\nDocker usage:\n'
  docker system df || true
  storage_guard_warn_build_cache || true

  printf '\nSafe manual cleanup commands:\n'
  printf '  docker builder prune --filter until=720h\n'
  printf '  docker image prune --filter until=720h\n'
  printf 'Do not run docker volume prune for radiaTest.\n'
}

storage_guard_preflight() {
  local docker_root postgres_volume failed=0
  docker_root="$(storage_guard_docker_root)"
  postgres_volume="$(storage_guard_postgres_volume)"

  storage_guard_report

  storage_guard_check_path root / || failed=1
  if [[ -e /data ]]; then
    if mountpoint -q /data; then
      storage_guard_check_path data /data || failed=1
    else
      printf 'Storage guard failed: /data is not a mount point.\n' >&2
      failed=1
    fi
  else
    printf 'Storage guard failed: /data is missing.\n' >&2
    failed=1
  fi
  if [[ -n "$docker_root" ]]; then
    storage_guard_check_path DockerRootDir "$docker_root" || failed=1
  fi
  if [[ -n "$postgres_volume" ]]; then
    storage_guard_check_path "PostgreSQL volume" "$postgres_volume" || failed=1
  fi

  [[ "$failed" -eq 0 ]] || storage_guard_fail "storage preflight failed"
}
