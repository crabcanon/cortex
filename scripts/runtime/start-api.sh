#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

install_if_missing="${CORTEX_CRAWL4AI_INSTALL_IF_MISSING:-0}"
with_deps="${CORTEX_CRAWL4AI_WITH_DEPS:-0}"
skip_probe="${CORTEX_CRAWL4AI_SKIP_PROBE:-0}"

args=("scripts/runtime/prepare_crawl4ai_runtime.py")
if [[ "${install_if_missing}" == "1" ]]; then
  args+=("--install-if-missing")
fi
if [[ "${with_deps}" == "1" ]]; then
  args+=("--with-deps")
fi
if [[ "${skip_probe}" == "1" ]]; then
  args+=("--no-probe")
fi

"${repo_root}/.venv/bin/python" "${args[@]}"
exec "${repo_root}/.venv/bin/cortex-api"
