
## 2024-05-28 - Missing API Security Headers
**Vulnerability:** Fast API application was missing standard security headers (Strict-Transport-Security, X-Frame-Options, X-Content-Type-Options).
**Learning:** Security headers are crucial for defense in depth. For JSON APIs, it is often safer to omit CSP entirely while keeping HSTS, X-Frame-Options, and X-Content-Type-Options to prevent breaking web-based API documentation.
**Prevention:** Implement security headers centrally in the response middleware to ensure all endpoints are protected automatically.
