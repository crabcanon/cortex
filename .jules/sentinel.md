## 2025-05-08 - Missing Security Headers in FastAPI Response Middleware
**Vulnerability:** The API lacked essential security response headers (Strict-Transport-Security, X-Frame-Options, X-Content-Type-Options) in the request context middleware.
**Learning:** Even though the middleware sets standard trace headers, the critical security headers must be centrally managed and applied to all outgoing responses to prevent misconfigurations across endpoints and protect against common attacks like clickjacking and MIME sniffing.
**Prevention:** Always enforce global response security headers at the middleware layer.
