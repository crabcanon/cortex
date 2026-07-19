## 2025-02-27 - Centralized Security Headers
**Vulnerability:** Missing default HTTP security headers (HSTS, X-Frame-Options, X-Content-Type-Options) in Cortex API responses.
**Learning:** Security headers should be injected globally via FastAPI middleware rather than on individual routes to ensure comprehensive coverage. The `request_context.py` middleware is the ideal centralized location for this. Care must be taken not to blindly add `Content-Security-Policy` with `default-src 'self'` as it may break API documentation UIs (Swagger/Redoc).
**Prevention:** Establish a pattern of checking for basic security headers during the initial setup of API gateway or edge middleware.
