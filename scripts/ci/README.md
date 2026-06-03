# CI Scripts

This directory contains the portable validation entrypoints used by both local operators and
GitHub Actions.

## Validation entrypoints

- `python scripts/ci/check.py`
  Runs YAML/OpenAPI validation, Ruff, Pyright, and pytest in a cross-platform order.
- `python scripts/ci/validate_yaml.py`
  Parses and validates the published YAML assets:
  `specs/cortex-api.yaml`, `compose.local.yaml`, `otel-collector.yaml`,
  `scripts/dev/prometheus.local.yaml`, `scripts/dev/grafana/datasources/datasources.yaml`,
  and the default parse profile.
- `python scripts/ci/wait_for_runtime_stack.py`
  Waits for the docker-backed local stack to expose PostgreSQL, MinIO, Redis, OTel Collector,
  Jaeger, Prometheus, and Grafana before running runtime-stack tests.

## Typical local usage

1. Repository validation:
   `uv run --all-packages --all-groups python scripts/ci/check.py`
2. YAML/OpenAPI validation only:
   `uv run --all-packages --all-groups python scripts/ci/validate_yaml.py`
3. Optional docker-backed stack validation:
   `powershell -ExecutionPolicy Bypass -File scripts\dev\stack.ps1 up`
   `uv run --all-packages --all-groups python scripts/ci/wait_for_runtime_stack.py`
   `powershell -ExecutionPolicy Bypass -File scripts\dev\check-runtime-stack.ps1`
   `powershell -ExecutionPolicy Bypass -File scripts\dev\stack.ps1 down`
4. Optional live provider runtime sync before real parse/knowledge validation:
   `uv sync --all-packages --all-groups --extra runtime`

## GitHub Actions

`.github/workflows/ci.yaml` uses the same scripts:

- `quality` job: `uv sync --all-packages --all-groups --frozen` then `scripts/ci/check.py`
- `runtime-stack` job: manual `workflow_dispatch` opt-in, starts `compose.local.yaml`,
  waits for readiness with `scripts/ci/wait_for_runtime_stack.py`, runs
  `tests/integration/test_runtime_stack.py`, and always tears the stack down.

`scripts/dev/check-runtime-stack.ps1` currently runs both the infrastructure-backed
`tests/integration/test_runtime_stack.py` slice and the live observability probe in
`tests/integration/test_runtime_observability_stack.py`.

Additional release workflows:

- `.github/workflows/docker-publish.yaml`
  Builds Dockerfile targets for API, Parse Worker, Knowledge Worker, Evaluation Worker,
  Synthesis Worker, and the heavy Docling / runtime workers. It publishes images to GHCR
  on `main`, semver tags, or manual dispatch.
- `.github/workflows/docs-build.yaml`
  Runs the docs typecheck and production build for the `docs/` Next/Fumadocs site.

Portable deployment helpers live in `scripts/deploy/`:

- `release.sh`
  Standard Bash release entrypoint for production and CI/CD. It exposes `build`,
  `publish`, `deploy`, and `build-publish-deploy` commands.
- `build-images.ps1` / `build-images.sh`
  Build and optionally push all Cortex runtime images.
- `deploy-compose.ps1` / `deploy-compose.sh`
  Validate `compose.prod.yaml`, pull images, run database migrations, start services, and
  wait for `/v1/health/live`.
