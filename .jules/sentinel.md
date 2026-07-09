## 2024-05-13 - Security Headers Missing
**Vulnerability:** API responses lacked basic security headers (HSTS, X-Frame-Options, X-Content-Type-Options).
**Learning:** The FastAPI application was missing basic security headers in the global response middleware.
**Prevention:** Implement a global middleware to inject security headers into all API responses, or use an established middleware like Secure.
