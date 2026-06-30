## 2025-06-30 - Added security headers globally via request middleware
**Vulnerability:** Missing strict security headers in API responses (HSTS, X-Frame-Options, X-Content-Type-Options), increasing risk of MITM attacks, clickjacking, and MIME sniffing.
**Learning:** Security headers should be set centrally via middleware in FastAPI rather than per-route to ensure uniform coverage. Overly strict CSP shouldn't be blindly added to JSON APIs, especially those with Swagger UI.
**Prevention:** Always enforce global response middleware with basic security headers across the entire API space.
