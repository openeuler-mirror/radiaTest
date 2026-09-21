# Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
# This project is licensed under the Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
# http://license.coscl.org.cn/MulanPSL2

#!/usr/bin/env bash
set -Eeuo pipefail

MODE="${1:---dry-run}"
KEEP_COUNT=2
IMAGE_REPOS=(kronos-backend kronos-frontend)

usage() {
  cat <<'EOF'
Usage:
  deploy/scripts/docker-cleanup.sh [--dry-run|--run]

Default is --dry-run. --run removes old radiaTest backend/frontend image tags.
EOF
}

fail() {
  printf 'Error: %s\n' "$1" >&2
  exit 1
}

case "$MODE" in
  --dry-run | --run) ;;
  -h | --help | help)
    usage
    exit 0
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac

command -v docker >/dev/null || fail "required command not found: docker"

declare -A protected_refs=()
declare -A protected_ids=()
declare -A group_counts=()
delete_refs=()

protect_ref() {
  local ref="$1"
  [[ -n "$ref" ]] || return 0
  protected_refs["$ref"]=1
  local image_id
  image_id="$(docker image inspect --format '{{.Id}}' "$ref" 2>/dev/null || true)"
  [[ -n "$image_id" ]] && protected_ids["$image_id"]=1
}

protect_container_images() {
  local container_id image_ref image_id
  while IFS= read -r container_id; do
    [[ -n "$container_id" ]] || continue
    image_ref="$(docker inspect --format '{{.Config.Image}}' "$container_id" 2>/dev/null || true)"
    image_id="$(docker inspect --format '{{.Image}}' "$container_id" 2>/dev/null || true)"
    [[ -n "$image_ref" ]] && protected_refs["$image_ref"]=1
    [[ -n "$image_id" ]] && protected_ids["$image_id"]=1
  done < <(docker ps -aq)
}

protect_deployed_images() {
  local env commit short_commit
  for env in dev prod; do
    commit="$(cat "/opt/kronos/$env/deployed-commit" 2>/dev/null || true)"
    [[ -n "$commit" ]] || continue
    short_commit="${commit:0:12}"
    protect_ref "kronos-backend:$env-$short_commit"
    protect_ref "kronos-frontend:$env-$short_commit"
  done
}

list_kronos_images() {
  local repo repository tag ref created image_id
  for repo in "${IMAGE_REPOS[@]}"; do
    while IFS=$'\t' read -r repository tag; do
      [[ -n "$repository" && -n "$tag" && "$tag" != "<none>" ]] || continue
      case "$tag" in
        dev-* | prod-*) ;;
        *) continue ;;
      esac
      ref="$repository:$tag"
      created="$(docker image inspect --format '{{.Created}}' "$ref" 2>/dev/null || true)"
      image_id="$(docker image inspect --format '{{.Id}}' "$ref" 2>/dev/null || true)"
      [[ -n "$created" && -n "$image_id" ]] || continue
      printf '%s\t%s\t%s\t%s\t%s\n' "$created" "$repository" "$tag" "$ref" "$image_id"
    done < <(docker image ls "$repo" --format '{{.Repository}}\t{{.Tag}}')
  done | sort -r
}

is_protected() {
  local ref="$1"
  local image_id="$2"
  [[ -n "${protected_refs[$ref]:-}" || -n "${protected_ids[$image_id]:-}" ]]
}

protect_container_images
protect_deployed_images

printf 'Mode: %s\n' "$MODE"
printf 'Keep newest images per repository/environment: %s\n' "$KEEP_COUNT"
printf 'Scope: kronos-backend:dev-*, kronos-backend:prod-*, kronos-frontend:dev-*, kronos-frontend:prod-*\n'

printf '\nPlan:\n'
while IFS=$'\t' read -r _created repository tag ref image_id; do
  env="${tag%%-*}"
  group="$repository:$env"
  count="${group_counts[$group]:-0}"
  count=$((count + 1))
  group_counts["$group"]="$count"

  if is_protected "$ref" "$image_id"; then
    printf '  keep   %s (used by container or deployed)\n' "$ref"
  elif [[ "$count" -le "$KEEP_COUNT" ]]; then
    printf '  keep   %s (newest %s)\n' "$ref" "$KEEP_COUNT"
  else
    printf '  remove %s\n' "$ref"
    delete_refs+=("$ref")
  fi
done < <(list_kronos_images)

if [[ "${#delete_refs[@]}" -eq 0 ]]; then
  printf '\nNothing to remove.\n'
  exit 0
fi

if [[ "$MODE" != "--run" ]]; then
  printf '\nDry run only. Re-run with --run to remove %s image tag(s).\n' "${#delete_refs[@]}"
  exit 0
fi

printf '\nRemoving %s image tag(s)...\n' "${#delete_refs[@]}"
for ref in "${delete_refs[@]}"; do
  docker image rm "$ref"
done
printf 'Docker image cleanup completed.\n'
