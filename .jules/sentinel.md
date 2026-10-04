## 2025-02-14 - Add baseline security headers
**Vulnerability:** Missing security headers (X-Content-Type-Options, X-Frame-Options, Strict-Transport-Security) in API responses
**Learning:** Security headers should be implemented globally via middleware to ensure all endpoints are protected, rather than piecemeal on individual routes.
**Prevention:** Always verify the presence of baseline security headers in new APIs to prevent basic web vulnerabilities like clickjacking and MIME-sniffing.
