## YYYY-MM-DD - Missing Security Headers
**Vulnerability:** The API responses are missing baseline security headers (HSTS, X-Frame-Options, X-Content-Type-Options).
**Learning:** By default, FastAPI does not include these standard security headers. They must be explicitly added to the response, typically via a global middleware, to provide defense-in-depth against clickjacking, MIME-sniffing, and downgrade attacks.
**Prevention:** Implement a global middleware (or update the existing `request_context_middleware`) that unconditionally injects these baseline security headers on every response. Avoid restrictive CSP for APIs with web docs like Swagger UI.
