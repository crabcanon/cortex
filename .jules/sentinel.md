## 2024-10-24 - Missing Baseline API Security Headers
**Vulnerability:** The API responses lacked basic security headers (HSTS, X-Content-Type-Options, X-Frame-Options), leaving the application vulnerable to clickjacking and MIME-type sniffing.
**Learning:** Security headers should be applied globally via middleware to ensure all endpoints, including automatically generated documentation routes, inherit the baseline protections without requiring per-route configuration.
**Prevention:** Integrate standard security headers directly into the global request context middleware during initial project setup.
