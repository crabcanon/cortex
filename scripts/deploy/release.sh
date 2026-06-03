#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/../.." && pwd)"

log() {
  printf '[cortex] %s\n' "$*"
}

die() {
  printf '[cortex] ERROR: %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'USAGE'
Usage:
  bash scripts/deploy/release.sh build [options]
  bash scripts/deploy/release.sh publish [options]
  bash scripts/deploy/release.sh deploy [options]
  bash scripts/deploy/release.sh build-publish-deploy [options]

Commands:
  build                 Build images locally with docker buildx --load.
  publish               Build and push images to the registry.
  deploy                Pull configured images, run migrations, start Compose, and wait for health.
  build-publish-deploy  Build, push, then deploy from the same host.

Common options:
  --tag <tag>                         Image tag. Defaults to git short SHA.
  --heavy                             Include Docling, Evaluation runtime, and Synthesis runtime.
  --registry <registry>               Default: ghcr.io.
  --namespace <namespace>             Default: crabcanon.
  --platform <platform>               Default: linux/amd64.
  --runtime-config-path <path>        Default: configs/cortex.runtime.prod.yaml.
  --no-latest                         Do not also tag images as latest during build/publish.

Deploy options:
  --env-file <path>                   Default: .env.prod.
  --project <name>                    Default: cortex-prod.
  --pull                              Pull images before deploying. Enabled automatically for deploy.
  --no-pull                           Do not pull images before deploying.
  --no-migrate                        Skip database migration.
  --health-url <url>                  Default: http://127.0.0.1:8080/v1/health/live.
  --timeout-seconds <seconds>         Default: 180.

Examples:
  bash scripts/deploy/release.sh build --tag local-heavy --heavy
  bash scripts/deploy/release.sh publish --tag 2026.05.12 --heavy
  bash scripts/deploy/release.sh deploy --env-file .env.prod --heavy
  bash scripts/deploy/release.sh build-publish-deploy --tag 2026.05.12 --heavy --env-file .env.prod
USAGE
}

if [[ $# -lt 1 ]]; then
  usage
  exit 2
fi

command_name="$1"
shift

registry="ghcr.io"
namespace="crabcanon"
tag=""
platform="linux/amd64"
runtime_config_path="configs/cortex.runtime.prod.yaml"
include_heavy="false"
tag_latest="true"

env_file=".env.prod"
project="cortex-prod"
pull_images="auto"
run_migration="true"
health_url="http://127.0.0.1:8080/v1/health/live"
timeout_seconds="180"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --registry) registry="$2"; shift 2 ;;
    --namespace) namespace="$2"; shift 2 ;;
    --tag) tag="$2"; shift 2 ;;
    --platform) platform="$2"; shift 2 ;;
    --runtime-config-path) runtime_config_path="$2"; shift 2 ;;
    --heavy) include_heavy="true"; shift ;;
    --no-latest) tag_latest="false"; shift ;;
    --env-file) env_file="$2"; shift 2 ;;
    --project) project="$2"; shift 2 ;;
    --pull) pull_images="true"; shift ;;
    --no-pull) pull_images="false"; shift ;;
    --no-migrate) run_migration="false"; shift ;;
    --health-url) health_url="$2"; shift 2 ;;
    --timeout-seconds) timeout_seconds="$2"; shift 2 ;;
    -h|--help)
      usage
      exit 0
      ;;
    *) die "Unknown option: $1" ;;
  esac
done

cd "$repo_root"

if [[ -z "$tag" ]]; then
  tag="$(git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M%S)"
fi

build_args=(
  --registry "$registry"
  --namespace "$namespace"
  --tag "$tag"
  --platform "$platform"
  --runtime-config-path "$runtime_config_path"
)
if [[ "$include_heavy" == "true" ]]; then
  build_args+=(--heavy)
fi
if [[ "$tag_latest" != "true" ]]; then
  build_args+=(--no-latest)
fi

deploy_args=(
  --env-file "$env_file"
  --project "$project"
  --health-url "$health_url"
  --timeout-seconds "$timeout_seconds"
)
if [[ "$include_heavy" == "true" ]]; then
  deploy_args+=(--heavy)
fi
if [[ "$run_migration" != "true" ]]; then
  deploy_args+=(--no-migrate)
fi

case "$command_name" in
  build)
    log "Release step: build"
    bash "${script_dir}/build-images.sh" "${build_args[@]}"
    ;;
  publish)
    log "Release step: publish"
    bash "${script_dir}/build-images.sh" "${build_args[@]}" --push
    ;;
  deploy)
    log "Release step: deploy"
    if [[ "$pull_images" != "false" ]]; then
      deploy_args+=(--pull)
    fi
    bash "${script_dir}/deploy-compose.sh" "${deploy_args[@]}"
    ;;
  build-publish-deploy)
    log "Release step: build and publish"
    bash "${script_dir}/build-images.sh" "${build_args[@]}" --push
    log "Release step: deploy"
    if [[ "$pull_images" != "false" ]]; then
      deploy_args+=(--pull)
    fi
    bash "${script_dir}/deploy-compose.sh" "${deploy_args[@]}"
    ;;
  *)
    usage
    die "Unknown command: ${command_name}"
    ;;
esac
