## 2025-02-23 - Missing API Security Headers
**Vulnerability:** The API responses lacked basic security headers such as `Strict-Transport-Security`, `X-Frame-Options`, and `X-Content-Type-Options`.
**Learning:** Security headers should be managed centrally via middleware to ensure all endpoints have consistent security postures, rather than leaving them unconfigured or implementing them per route. However, we should also be careful about adding restrictive `Content-Security-Policy` to not break web-based API documentation.
**Prevention:** Include standard security headers in the foundational response middleware (e.g. `request_context_middleware.py`) during initial setup, while avoiding overly restrictive policies that conflict with the application's functionality.
