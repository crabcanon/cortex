# Integration Tests

The default repository test suite covers integration behavior with SQLite and local fakes so the
developer loop stays fast.

For real dependency validation against PostgreSQL + MinIO + the local observability stack:

1. Start the stack:
   `powershell -ExecutionPolicy Bypass -File scripts\dev\stack.ps1 up`
2. Run the docker-backed integration slice:
   `powershell -ExecutionPolicy Bypass -File scripts\dev\check-runtime-stack.ps1`
3. Inspect the stack when needed:
   `powershell -ExecutionPolicy Bypass -File scripts\dev\stack.ps1 ps`
   `powershell -ExecutionPolicy Bypass -File scripts\dev\stack.ps1 logs -Follow`
4. Tear the stack down:
   `powershell -ExecutionPolicy Bypass -File scripts\dev\stack.ps1 down`

Useful local endpoints:

- PostgreSQL: `127.0.0.1:5432` (`cortex` / `cortex`, default database `cortex`)
- MinIO S3 API: `http://127.0.0.1:9000`
- MinIO Console: `http://127.0.0.1:9001`
- Jaeger: `http://127.0.0.1:16686`
- Prometheus: `http://127.0.0.1:9090`
- Grafana: `http://127.0.0.1:3000` (`admin` / `admin`)

The runtime-stack tests are marked with `@pytest.mark.runtime_stack` and stay skipped unless
`CORTEX_RUNTIME_STACK=1` is set.

`scripts/dev/check-runtime-stack.ps1` now executes both:

- `tests/integration/test_runtime_stack.py`
- `tests/integration/test_runtime_observability_stack.py`
