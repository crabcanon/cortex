## 2024-10-01 - Add security headers to API responses
**Vulnerability:** Missing standard security headers (HSTS, X-Frame-Options, X-Content-Type-Options) in API responses.
**Learning:** These headers are foundational defense-in-depth measures against common web vulnerabilities like MIME-sniffing, clickjacking, and man-in-the-middle attacks, but were omitted from the global middleware.
**Prevention:** Include baseline security headers in global middleware for all new web applications by default.
