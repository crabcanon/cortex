## 2024-05-30 - Added security headers in API response middleware
**Vulnerability:** Missing security headers in API responses, which can expose the application to clickjacking, MIME sniffing, and downgrade attacks.
**Learning:** Security headers should be handled centrally in the request lifecycle middleware (`apps/api/src/cortex_api/middleware/request_context.py`) rather than per-endpoint.
**Prevention:** Implement security headers in the global request context middleware to ensure all endpoints automatically inherit these protections.
