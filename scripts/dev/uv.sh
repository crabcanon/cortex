#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/_uv-env.sh"
cortex_invoke_uv "$@"
