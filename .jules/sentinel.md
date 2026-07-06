
## 2024-05-18 - Missing Security Headers in FastAPI
**Vulnerability:** The API lacked important security headers (Strict-Transport-Security, X-Frame-Options, X-Content-Type-Options) in the responses.
**Learning:** Security headers should be managed centrally in the FastAPI response middleware (`request_context.py`) for the Cortex API to ensure they are applied to all responses.
**Prevention:** Always verify response headers include at least standard security headers (HSTS, X-Frame-Options, X-Content-Type-Options) during API development.
