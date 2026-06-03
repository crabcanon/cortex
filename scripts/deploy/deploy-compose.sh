#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/../.." && pwd)"

env_file=".env.prod"
project="cortex-prod"
include_heavy="false"
pull_images="false"
run_migration="true"
health_url="http://127.0.0.1:8080/v1/health/live"
timeout_seconds="180"

log() {
  printf '[cortex] %s\n' "$*"
}

die() {
  printf '[cortex] ERROR: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file) env_file="$2"; shift 2 ;;
    --project) project="$2"; shift 2 ;;
    --heavy) include_heavy="true"; shift ;;
    --pull) pull_images="true"; shift ;;
    --no-migrate) run_migration="false"; shift ;;
    --health-url) health_url="$2"; shift 2 ;;
    --timeout-seconds) timeout_seconds="$2"; shift 2 ;;
    -h|--help)
      cat <<'USAGE'
Usage: scripts/deploy/deploy-compose.sh [options]

Options:
  --env-file .env.prod       Production env file.
  --project cortex-prod      Compose project name.
  --heavy                    Enable docling/eval-runtime/synthesis-runtime profiles.
  --pull                     Pull configured images before startup.
  --no-migrate               Skip database migration.
  --health-url <url>         Health endpoint to wait for. Empty string disables wait.
  --timeout-seconds 180      Health wait timeout.
USAGE
      exit 0
      ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

cd "$repo_root"
require_command docker
if [[ -n "$health_url" ]]; then
  require_command curl
fi

if [[ ! -f "$env_file" ]]; then
  die "Env file not found: ${env_file}. Copy .env.prod.example and fill production values first."
fi

compose=(--env-file "$env_file" -p "$project" -f compose.prod.yaml)
profiles=()
if [[ "$include_heavy" == "true" ]]; then
  profiles+=(--profile docling --profile eval-runtime --profile synthesis-runtime)
fi

log "Validating production Compose config..."
docker compose "${compose[@]}" "${profiles[@]}" config --quiet

if [[ "$pull_images" == "true" ]]; then
  log "Pulling images..."
  docker compose "${compose[@]}" "${profiles[@]}" pull
fi

if [[ "$run_migration" == "true" ]]; then
  log "Running database migration..."
  docker compose "${compose[@]}" --profile migrate run --rm cortex-migrate
fi

log "Starting production services..."
docker compose "${compose[@]}" "${profiles[@]}" up -d

if [[ -n "$health_url" ]]; then
  log "Waiting for health endpoint: ${health_url}"
  deadline=$((SECONDS + timeout_seconds))
  until curl -fsS "$health_url" >/dev/null 2>&1; do
    if (( SECONDS >= deadline )); then
      docker compose "${compose[@]}" "${profiles[@]}" ps
      die "Timed out waiting for Cortex API health endpoint: ${health_url}"
    fi
    sleep 3
  done
  log "API health check passed."
fi

docker compose "${compose[@]}" "${profiles[@]}" ps
