## YYYY-MM-DD - [Missing Security Headers]
**Vulnerability:** Missing base security headers (like X-Content-Type-Options, Strict-Transport-Security, X-Frame-Options) in global FastAPI middleware.
**Learning:** These headers weren't included in the custom request context middleware in `apps/api/src/cortex_api/middleware/request_context.py` allowing for various potential attacks.
**Prevention:** Always ensure security headers are configured at the middleware level of any web API framework.
