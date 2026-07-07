## 2024-05-24 - Missing Security Headers in FastAPI Response Middleware
**Vulnerability:** The API was missing fundamental security headers (`Strict-Transport-Security`, `X-Frame-Options`, `X-Content-Type-Options`).
**Learning:** API security headers for the Cortex API should be managed centrally in the FastAPI response middleware (`apps/api/src/cortex_api/middleware/request_context.py`) to ensure all endpoints are protected consistently.
**Prevention:** Always verify that fundamental security headers are included in the baseline API response middleware during initial setup.
