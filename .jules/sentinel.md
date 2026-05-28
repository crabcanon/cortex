## 2025-02-27 - Centralized Security Headers in Middleware
**Vulnerability:** Missing security headers (Strict-Transport-Security, X-Content-Type-Options, X-Frame-Options) across API responses.
**Learning:** The FastAPI application was missing these crucial security headers out of the box. By adding them to the central request context middleware, we ensure that every response uniformly receives these protections against common web vulnerabilities (MIME sniffing, clickjacking, enforcing HTTPS).
**Prevention:** Always check global middlewares when auditing or improving application-wide headers to ensure consistent coverage rather than applying headers on a per-route basis.
