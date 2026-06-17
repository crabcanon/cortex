## 2024-05-24 - Missing Security Headers Middleware
**Vulnerability:** API responses lacked security headers (HSTS, X-Frame-Options, X-Content-Type-Options) allowing clickjacking, MIME-type sniffing, and man-in-the-middle attacks over HTTP.
**Learning:** Fastapi does not add security headers by default. `request_context_middleware` is the centralized place to add headers to all responses.
**Prevention:** Implement security headers in the global response middleware for all APIs.
