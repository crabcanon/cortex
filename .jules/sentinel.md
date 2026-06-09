## 2026-06-09 - Fix silent error handling in Cognee search kwargs generation
**Vulnerability:** Silent error handling (broad `except Exception: pass`) in Cognee runtime adapter
**Learning:** Broad exception handling during optional runtime setup can hide misconfigurations or missing dependencies from users, making debugging impossible and allowing corrupted state propagation. The `cortex_knowledge/runtime.py` masked enum lookup errors.
**Prevention:** Avoid `except Exception: pass`. Catch specific exceptions (like `ValueError` for Enums) and log unexpected failures using `logger.exception` so traces are visible in logs but not leaked to HTTP responses.
