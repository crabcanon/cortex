# End-to-End Tests

The main API end-to-end path is currently covered by:

- `tests/integration/test_api_e2e.py`

It exercises the deterministic `upload -> parse -> add -> search` chain using the real FastAPI
routes, SQL persistence, and worker `run_once()` loops while keeping provider dependencies faked
for repeatability.
