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
