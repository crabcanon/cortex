#!/usr/bin/env bash
set -euo pipefail

once=0
force_recreate=0
interval_seconds=1
skip_browser_bootstrap=0
no_browser_install=0
engine_keys="crawl4ai,jina_reader,llama_parse,markitdown"

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
    --skip-browser-bootstrap)
      skip_browser_bootstrap=1
      ;;
    --no-browser-install)
      no_browser_install=1
      ;;
    --engine-keys)
      shift
      engine_keys="${1:?missing engine keys value}"
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
  bash scripts/dev/run-parse-worker.sh
EOF
    exit 1
  fi
  echo "[cortex] .venv is missing or unhealthy, repairing before launching Parse Worker..."
  cortex_repair_venv "${force_recreate}"
fi

worker_path="$(cortex_venv_command_path cortex-parse-worker)"
if [[ ! -f "${worker_path}" ]]; then
  if cortex_is_project_venv_active; then
    cat >&2 <<'EOF'
[cortex] Parse Worker entrypoint is missing from the currently activated project `.venv`.
Run `deactivate` (or open a fresh terminal), then rerun:
  bash scripts/dev/repair-venv.sh --force-recreate
  bash scripts/dev/run-parse-worker.sh
EOF
    exit 1
  fi
  echo "[cortex] Parse Worker entrypoint is missing, syncing workspace first..."
  cortex_repair_venv "${force_recreate}"
  worker_path="$(cortex_venv_command_path cortex-parse-worker)"
fi

if [[ ! -f "${worker_path}" ]]; then
  echo "[cortex] Parse Worker executable was not found after repair: ${worker_path}" >&2
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

export CORTEX_PARSE_WORKER_ENGINE_KEYS="${engine_keys}"

if [[ "${once}" == "1" ]]; then
  export CORTEX_PARSE_WORKER_RUN_ONCE=1
  exec "${worker_path}"
fi

export CORTEX_PARSE_WORKER_LOOP_SLEEP_SECONDS="${interval_seconds}"
exec "${worker_path}"
