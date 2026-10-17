## 2024-05-18 - Missing Security Headers
**Vulnerability:** Missing basic API security headers like X-Content-Type-Options, X-Frame-Options, and Strict-Transport-Security.
**Learning:** Security headers are not present by default. We should proactively enforce basic API security headers on responses.
**Prevention:** Include standard headers such as X-Content-Type-Options, X-Frame-Options, and Strict-Transport-Security in global middleware.
