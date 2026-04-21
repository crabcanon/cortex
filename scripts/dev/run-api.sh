#!/usr/bin/env bash
set -euo pipefail

force_recreate=0
skip_browser_bootstrap=0
no_browser_install=0

while (($# > 0)); do
  case "$1" in
    --force-recreate)
      force_recreate=1
      ;;
    --skip-browser-bootstrap)
      skip_browser_bootstrap=1
      ;;
    --no-browser-install)
      no_browser_install=1
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
  if cortex_is_project_venv_active; then
    cat >&2 <<'EOF'
[cortex] the project `.venv` is currently activated in this shell and cannot be repaired in place.
Run `deactivate` (or open a fresh terminal), then rerun:
  bash scripts/dev/repair-venv.sh --force-recreate
  bash scripts/dev/run-api.sh
EOF
    exit 1
  fi
  echo "[cortex] .venv is missing or unhealthy, repairing before launching API..."
  cortex_repair_venv "${force_recreate}"
fi

api_path="$(cortex_venv_command_path cortex-api)"
if [[ ! -f "${api_path}" ]]; then
  if cortex_is_project_venv_active; then
    cat >&2 <<'EOF'
[cortex] API entrypoint is missing from the currently activated project `.venv`.
Run `deactivate` (or open a fresh terminal), then rerun:
  bash scripts/dev/repair-venv.sh --force-recreate
  bash scripts/dev/run-api.sh
EOF
    exit 1
  fi
  echo "[cortex] API entrypoint is missing, syncing workspace first..."
  cortex_repair_venv "${force_recreate}"
  api_path="$(cortex_venv_command_path cortex-api)"
fi

if [[ ! -f "${api_path}" ]]; then
  echo "[cortex] API executable was not found after repair: ${api_path}" >&2
  exit 1
fi

if [[ "${skip_browser_bootstrap}" != "1" ]]; then
  install_if_missing=1
  if [[ "${no_browser_install}" == "1" ]]; then
    install_if_missing=0
  fi
  cortex_invoke_runtime_prep "${install_if_missing}" 0 0
fi

cd "$(cortex_repo_root)"
exec "${api_path}"
