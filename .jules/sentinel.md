## 2025-02-12 - Missing Security Headers in Global Middleware
**Vulnerability:** The API responses lacked basic security headers like Strict-Transport-Security (HSTS), X-Frame-Options, and X-Content-Type-Options.
**Learning:** These headers are crucial for basic web application security, even for APIs, and should be added globally at the middleware layer. Overly restrictive CSP should be avoided for API services to maintain documentation availability.
**Prevention:** Always include a foundational set of security headers for HTTP responses in FastAPI middleware during initial setup.
