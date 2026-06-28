## 2024-06-28 - [Added Security Headers Middleware]
**Vulnerability:** Missing default HTTP security headers (HSTS, X-Frame-Options, X-Content-Type-Options) in API responses.
**Learning:** Security headers should be configured globally at the middleware level so that no response inadvertently skips security measures.
**Prevention:** Ensure security headers are included in global middleware configurations on all projects by default.
