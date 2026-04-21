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

cortex_normalize_path() {
  local path_value="$1"
  if command -v cygpath >/dev/null 2>&1; then
    cygpath -m "${path_value}"
  else
    printf '%s\n' "${path_value}"
  fi
}

cortex_is_project_venv_active() {
  cortex_set_uv_environment
  [[ -n "${VIRTUAL_ENV:-}" ]] || return 1

  local active_env target_env
  active_env="$(cortex_normalize_path "${VIRTUAL_ENV}" | tr '[:upper:]' '[:lower:]')"
  target_env="$(cortex_normalize_path "${UV_PROJECT_ENVIRONMENT}" | tr '[:upper:]' '[:lower:]')"
  [[ "${active_env}" == "${target_env}" ]]
}

cortex_test_venv_managed_by_repo() {
  cortex_set_uv_environment

  local config_path expected_root home_line home_root
  config_path="${UV_PROJECT_ENVIRONMENT}/pyvenv.cfg"
  [[ -f "${config_path}" ]] || return 1

  home_line="$(sed -n 's/^[[:space:]]*home[[:space:]]*=[[:space:]]*//p' "${config_path}" | head -n 1)"
  [[ -n "${home_line}" ]] || return 1

  expected_root="$(cortex_normalize_path "${UV_PYTHON_INSTALL_DIR}" | tr '[:upper:]' '[:lower:]')"
  home_root="$(cortex_normalize_path "${home_line}" | tr '[:upper:]' '[:lower:]')"
  [[ "${home_root}" == "${expected_root}"* ]]
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
  cortex_test_venv_managed_by_repo || return 1

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
  if cortex_is_project_venv_active; then
    cat >&2 <<'EOF'
[cortex] the target workspace `.venv` is currently activated in this shell.
Run `deactivate` (or open a fresh terminal) before repairing it, then rerun:
  bash scripts/dev/repair-venv.sh --force-recreate
EOF
    return 1
  fi

  if [[ "${force_recreate}" == "1" && -d "${UV_PROJECT_ENVIRONMENT}" ]]; then
    if ! rm -rf "${UV_PROJECT_ENVIRONMENT}"; then
      cat >&2 <<'EOF'
[cortex] failed to recreate the workspace `.venv` because a running `cortex-api` / worker / Python / uv process is still using it.
Stop those processes first, then rerun:
  bash scripts/dev/repair-venv.sh --force-recreate
EOF
      return 1
    fi
    if [[ -d "${UV_PROJECT_ENVIRONMENT}" ]]; then
      cat >&2 <<'EOF'
[cortex] failed to recreate the workspace `.venv` because a running `cortex-api` / worker / Python / uv process is still using it.
Stop those processes first, then rerun:
  bash scripts/dev/repair-venv.sh --force-recreate
EOF
      return 1
    fi
  fi

  if ! cortex_invoke_uv sync --all-packages --all-groups; then
    cat >&2 <<'EOF'
[cortex] uv sync failed while repairing the workspace environment.
Stop any running `cortex-api` / worker / Python / uv process that is still using `.venv`, then rerun:
  bash scripts/dev/repair-venv.sh --force-recreate
EOF
    return 1
  fi

  if ! cortex_test_venv_healthy; then
    cat >&2 <<'EOF'
[cortex] the workspace `.venv` is still unhealthy after sync.
Try:
  bash scripts/dev/repair-venv.sh --force-recreate
after stopping any `cortex-api` / worker / Python / uv process that is using `.venv`.
EOF
    return 1
  fi
}

cortex_invoke_runtime_prep() {
  local install_if_missing="${1:-0}"
  local with_deps="${2:-0}"
  local no_probe="${3:-0}"

  cortex_set_uv_environment
  local python_path script_path
  python_path="$(cortex_venv_command_path python)"
  script_path="$(cortex_repo_root)/scripts/runtime/prepare_crawl4ai_runtime.py"
  local args=("${script_path}")

  if [[ "${install_if_missing}" == "1" ]]; then
    args+=("--install-if-missing")
  fi
  if [[ "${with_deps}" == "1" ]]; then
    args+=("--with-deps")
  fi
  if [[ "${no_probe}" == "1" ]]; then
    args+=("--no-probe")
  fi

  (
    cd "$(cortex_repo_root)"
    "${python_path}" "${args[@]}"
  )
}
