## 2025-02-14 - Add baseline API security headers
**Vulnerability:** Missing security headers like `X-Content-Type-Options`, `X-Frame-Options`, and `Strict-Transport-Security` in global middleware.
**Learning:** For defense in depth, it is critical to configure global middleware (like `request_context_middleware`) to inject security headers in all API responses to protect against common attacks like clickjacking and MIME sniffing.
**Prevention:** Always add security headers explicitly when creating or modifying API middleware configurations, rather than relying solely on infrastructure level configurations (e.g., proxies).
