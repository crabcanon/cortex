## 2024-05-16 - [Missing API Security Headers]
**Vulnerability:** The API responses are missing baseline security headers (X-Content-Type-Options, X-Frame-Options, Strict-Transport-Security).
**Learning:** These should be managed globally in the `request_context_middleware` in `apps/api/src/cortex_api/middleware/request_context.py`. Missing them exposes the API to MIME sniffing, clickjacking, and man-in-the-middle downgrade attacks.
**Prevention:** Always add security headers in global middleware.
