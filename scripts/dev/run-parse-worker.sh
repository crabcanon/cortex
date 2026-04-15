#!/usr/bin/env bash
set -euo pipefail

once=0
force_recreate=0
interval_seconds=1

while (($# > 0)); do
  case "$1" in
    --once)
      once=1
      ;;
    --force-recreate)
      force_recreate=1
      ;;
    --interval)
      shift
      interval_seconds="${1:?missing interval value}"
      ;;
    *)
      echo "[cortex] unknown argument: $1" >&2
      exit 2
      ;;
  esac
  shift
done

source "$(dirname "$0")/_uv-env.sh"

if ! cortex_test_venv_healthy; then
  echo "[cortex] .venv is missing or unhealthy, repairing before launching Parse Worker..."
  cortex_repair_venv "${force_recreate}"
fi

worker_path="$(cortex_venv_command_path cortex-parse-worker)"
if [[ ! -f "${worker_path}" ]]; then
  echo "[cortex] Parse Worker entrypoint is missing, syncing workspace first..."
  cortex_repair_venv "${force_recreate}"
  worker_path="$(cortex_venv_command_path cortex-parse-worker)"
fi

if [[ ! -f "${worker_path}" ]]; then
  echo "[cortex] Parse Worker executable was not found after repair: ${worker_path}" >&2
  exit 1
fi

cd "$(cortex_repo_root)"

if [[ "${once}" == "1" ]]; then
  exec "${worker_path}"
fi

while true; do
  "${worker_path}"
  sleep "${interval_seconds}"
done
