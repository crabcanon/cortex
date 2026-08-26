## YYYY-MM-DD - [Baseline Security Headers and CSP Constraints]
**Vulnerability:** Missing security headers (X-Content-Type-Options, X-Frame-Options, Strict-Transport-Security) across all API responses.
**Learning:** Adding `Content-Security-Policy` globally can inadvertently break web-based API documentation (such as Swagger UI or Redoc) which rely on inline scripts or external assets from CDNs. It is safer to omit CSP for JSON APIs while keeping other baseline headers.
**Prevention:** Always implement HSTS, X-Frame-Options, and X-Content-Type-Options via global middleware (like `request_context.py`), but carefully scope or omit CSP to prevent breaking web interfaces.
