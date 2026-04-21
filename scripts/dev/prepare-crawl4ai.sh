#!/usr/bin/env bash
set -euo pipefail

force_recreate=0
no_probe=0
install_if_missing=0
with_deps=0

while (($# > 0)); do
  case "$1" in
    --force-recreate)
      force_recreate=1
      ;;
    --no-probe)
      no_probe=1
      ;;
    --install-if-missing)
      install_if_missing=1
      ;;
    --with-deps)
      with_deps=1
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
  bash scripts/dev/prepare-crawl4ai.sh
EOF
    exit 1
  fi
  echo "[cortex] .venv is missing or unhealthy, repairing before preparing Crawl4AI..."
  cortex_repair_venv "${force_recreate}"
fi

cortex_invoke_runtime_prep "${install_if_missing}" "${with_deps}" "${no_probe}"
