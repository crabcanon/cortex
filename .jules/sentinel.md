## 2026-05-12 - Missing Security Headers in API Middleware
**Vulnerability:** The API response middleware (`apps/api/src/cortex_api/middleware/request_context.py`) was not setting basic security headers like `Strict-Transport-Security`, `X-Frame-Options`, and `X-Content-Type-Options`.
**Learning:** Security headers are crucial for basic defense in depth against common attacks like MIME sniffing, clickjacking, and man-in-the-middle attacks. It's a common oversight to forget them in custom FastAPI middlewares if they are not explicitly enforced.
**Prevention:** Ensure that global response middlewares always append standard security headers unless there is a specific reason not to.
