## 2024-10-23 - Baseline API Security Headers
**Vulnerability:** Missing standard API security headers (X-Content-Type-Options, X-Frame-Options, Strict-Transport-Security) in the global middleware.
**Learning:** These headers weren't explicitly required by any test and were omitted in the initial design. This is common when setting up internal/dev APIs first before considering production security constraints. Adding them to `request_context.py` ensures all routes, including unauthenticated ones, benefit from the protection.
**Prevention:** Always verify security headers in the global response interceptor/middleware in new API architectures from the start.
