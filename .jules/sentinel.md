## 2025-02-09 - Missing Security Headers Middleware
**Vulnerability:** API responses lacked security headers (HSTS, Content-Type-Options, X-Frame-Options)
**Learning:** Default FastAPI apps do not include security headers by default. Global middleware is the best place to add these baseline defenses without affecting specific route logic.
**Prevention:** Always implement basic security headers early in API development, even for internal tools.
