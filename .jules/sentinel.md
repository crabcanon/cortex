## 2024-05-08 - Added Security Headers to Global Middleware
**Vulnerability:** Missing baseline security headers (X-Content-Type-Options, X-Frame-Options, Strict-Transport-Security) in the global FastAPI request context middleware.
**Learning:** Security headers must be explicitly set on the Response object within the middleware to ensure they are applied globally to all endpoints.
**Prevention:** Implement a standard suite of security headers in the global middleware during initial project setup to ensure defense-in-depth across the API.
