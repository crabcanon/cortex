#!/usr/bin/env bash
set -euo pipefail

cortex_repo_root() {
  cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd
}

cortex_set_uv_environment() {
  local repo_root
  repo_root="$(cortex_repo_root)"
  export UV_PYTHON_INSTALL_DIR="${repo_root}/.uv-python"
  export UV_PROJECT_ENVIRONMENT="${repo_root}/.venv"
}

cortex_venv_bin_dir() {
  cortex_set_uv_environment
  if [[ -d "${UV_PROJECT_ENVIRONMENT}/Scripts" ]]; then
    printf '%s\n' "${UV_PROJECT_ENVIRONMENT}/Scripts"
  else
    printf '%s\n' "${UV_PROJECT_ENVIRONMENT}/bin"
  fi
}

cortex_venv_command_path() {
  local name="$1"
  local bin_dir
  bin_dir="$(cortex_venv_bin_dir)"

  if [[ -f "${bin_dir}/${name}.exe" ]]; then
    printf '%s\n' "${bin_dir}/${name}.exe"
    return
  fi

  printf '%s\n' "${bin_dir}/${name}"
}

cortex_test_venv_healthy() {
  cortex_set_uv_environment
  local python_path
  python_path="$(cortex_venv_command_path python)"

  if [[ ! -f "${python_path}" ]]; then
    return 1
  fi

  "${python_path}" -c "import sys; print(sys.executable)" >/dev/null 2>&1
}

cortex_invoke_uv() {
  local repo_root
  repo_root="$(cortex_repo_root)"
  cortex_set_uv_environment
  (
    cd "${repo_root}"
    uv "$@"
  )
}

cortex_repair_venv() {
  local force_recreate="${1:-0}"

  cortex_set_uv_environment
  if [[ "${force_recreate}" == "1" && -d "${UV_PROJECT_ENVIRONMENT}" ]]; then
    rm -rf "${UV_PROJECT_ENVIRONMENT}"
  fi

  if ! cortex_invoke_uv sync --all-packages --all-groups; then
    cat >&2 <<'EOF'
[cortex] uv sync failed while repairing the workspace environment.
Close any Python/uv/IDE processes holding `.venv`, then rerun:
  bash scripts/dev/repair-venv.sh --force-recreate
EOF
    return 1
  fi

  if ! cortex_test_venv_healthy; then
    cat >&2 <<'EOF'
[cortex] the workspace `.venv` is still unhealthy after sync.
Try:
  bash scripts/dev/repair-venv.sh --force-recreate
after closing any process that is using `.venv`.
EOF
    return 1
  fi
}
