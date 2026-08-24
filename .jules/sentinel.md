## 2024-06-25 - Missing Security Headers in Request Context Middleware
**Vulnerability:** The application lacks baseline HTTP security headers (e.g., X-Content-Type-Options, X-Frame-Options, Strict-Transport-Security) on API responses.
**Learning:** Security headers are essential to mitigate common web vulnerabilities like MIME sniffing, clickjacking, and man-in-the-middle attacks. These should be applied centrally in the middleware.
**Prevention:** Always enforce standard security headers at the middleware layer for all incoming requests.
