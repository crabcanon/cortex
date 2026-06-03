#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/../.." && pwd)"

registry="ghcr.io"
namespace="crabcanon"
tag=""
platform="linux/amd64"
runtime_config_path="configs/cortex.runtime.prod.yaml"
include_heavy="false"
push_images="false"
tag_latest="true"

log() {
  printf '[cortex] %s\n' "$*"
}

die() {
  printf '[cortex] ERROR: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --registry) registry="$2"; shift 2 ;;
    --namespace) namespace="$2"; shift 2 ;;
    --tag) tag="$2"; shift 2 ;;
    --platform) platform="$2"; shift 2 ;;
    --runtime-config-path) runtime_config_path="$2"; shift 2 ;;
    --heavy) include_heavy="true"; shift ;;
    --push) push_images="true"; shift ;;
    --no-latest) tag_latest="false"; shift ;;
    -h|--help)
      cat <<'USAGE'
Usage: scripts/deploy/build-images.sh [options]

Options:
  --registry ghcr.io                 Container registry.
  --namespace crabcanon              Registry namespace or organization.
  --tag <tag>                        Image tag. Defaults to git short SHA.
  --platform linux/amd64             Build platform.
  --runtime-config-path <path>       Runtime config path used by image build checks.
  --heavy                            Include docling/evaluation-runtime/synthesis-runtime images.
  --push                             Push images instead of loading them locally.
  --no-latest                        Do not also tag images as latest.
USAGE
      exit 0
      ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

cd "$repo_root"
require_command docker

if [[ -z "$tag" ]]; then
  tag="$(git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M%S)"
fi

targets=(
  "api:cortex-api:false"
  "parse-worker:cortex-parse-worker:false"
  "knowledge-worker:cortex-knowledge-worker:false"
  "evaluation-worker:cortex-evaluation-worker:false"
  "synthesis-worker:cortex-synthesis-worker:false"
  "parse-worker-docling:cortex-parse-worker-docling:true"
  "evaluation-worker-runtime:cortex-evaluation-worker-runtime:true"
  "synthesis-worker-runtime:cortex-synthesis-worker-runtime:true"
)

log "Building images for ${registry}/${namespace}:${tag}"
log "Runtime config path: ${runtime_config_path}"
if [[ "$include_heavy" != "true" ]]; then
  log "Heavy images are skipped. Pass --heavy to include Docling, Eval runtime, and Synthesis runtime images."
fi

for entry in "${targets[@]}"; do
  IFS=":" read -r target image heavy <<< "$entry"
  if [[ "$heavy" == "true" && "$include_heavy" != "true" ]]; then
    continue
  fi

  build_args=(
    buildx build
    --platform "$platform"
    --target "$target"
    --build-arg "CORTEX_RUNTIME_CONFIG_PATH=${runtime_config_path}"
    --build-arg "CORTEX_PREPARE_CRAWL4AI_RUNTIME=1"
    -t "${registry}/${namespace}/${image}:${tag}"
  )

  if [[ -n "${CORTEX_PYTHON_BASE_IMAGE:-}" ]]; then
    build_args+=(--build-arg "PYTHON_BASE_IMAGE=${CORTEX_PYTHON_BASE_IMAGE}")
  fi
  if [[ -n "${CORTEX_PLAYWRIGHT_PYTHON_BASE_IMAGE:-}" ]]; then
    build_args+=(--build-arg "PLAYWRIGHT_PYTHON_BASE_IMAGE=${CORTEX_PLAYWRIGHT_PYTHON_BASE_IMAGE}")
  fi
  if [[ -n "${CORTEX_UV_IMAGE:-}" ]]; then
    build_args+=(--build-arg "UV_IMAGE=${CORTEX_UV_IMAGE}")
  fi
  if [[ "$tag_latest" == "true" ]]; then
    build_args+=(-t "${registry}/${namespace}/${image}:latest")
  fi
  if [[ "$push_images" == "true" ]]; then
    build_args+=(--push)
  else
    build_args+=(--load)
  fi
  build_args+=(.)

  log "Building target ${target} -> ${registry}/${namespace}/${image}:${tag}"
  docker "${build_args[@]}"
done

log "Image build completed."
