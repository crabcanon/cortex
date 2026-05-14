## 2025-02-28 - Missing Security Headers in FastAPI Response Middleware
**Vulnerability:** The application was missing standard security headers (`Strict-Transport-Security`, `X-Frame-Options`, `X-Content-Type-Options`) in its HTTP responses.
**Learning:** Security headers are not automatically included by default in the FastAPI `Request`/`Response` cycle in this codebase. They needed to be explicitly injected via the centralized `request_context_middleware`.
**Prevention:** Ensure new middleware or changes to existing response-handling middleware preserve or include necessary security headers. Review any future routes that might bypass this core middleware to ensure headers are still applied.
