#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

sleep_seconds="${CORTEX_KNOWLEDGE_WORKER_LOOP_SLEEP_SECONDS:-1}"

while true; do
  set +e
  "${repo_root}/.venv/bin/cortex-knowledge-worker"
  exit_code=$?
  set -e

  if [[ ${exit_code} -ne 0 ]]; then
    echo "[cortex] cortex-knowledge-worker exited with code ${exit_code}" >&2
    exit "${exit_code}"
  fi

  sleep "${sleep_seconds}"
done
