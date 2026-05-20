## 2026-04-24 - Missing Security Headers in FastAPI Response Middleware
**Vulnerability:** Missing security headers (Strict-Transport-Security, X-Frame-Options, X-Content-Type-Options) in Cortex API responses.
**Learning:** The FastAPI setup correctly centralized response tracking (X-Request-Id, X-Trace-Id) via middleware (`request_context_middleware`), but omitted crucial security headers leaving the app susceptible to clickjacking, MIME type sniffing, and lack of HSTS enforcement.
**Prevention:** Ensure any centralized HTTP response middleware or global server configuration enforces standard security headers.
