## 2026-06-11 - [Centralized Security Headers in FastAPI Middleware]
**Vulnerability:** Missing fundamental security headers (Strict-Transport-Security, X-Frame-Options, X-Content-Type-Options) across API responses, exposing the application to clickjacking, MIME-sniffing, and downgrade attacks.
**Learning:** Security headers were not being consistently applied because there was no centralized mechanism. Adding them in the global `request_context_middleware` ensures all endpoints are protected by default without relying on individual route configurations.
**Prevention:** Always implement security headers in global middleware rather than at the route level to ensure defense-in-depth across the entire API surface area.
