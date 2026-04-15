#!/usr/bin/env bash
set -euo pipefail

force_recreate=0
for arg in "$@"; do
  case "$arg" in
    --force-recreate)
      force_recreate=1
      ;;
    *)
      echo "[cortex] unknown argument: $arg" >&2
      exit 2
      ;;
  esac
done

source "$(dirname "$0")/_uv-env.sh"
cortex_repair_venv "${force_recreate}"
echo "[cortex] workspace environment is healthy at ${UV_PROJECT_ENVIRONMENT}"
