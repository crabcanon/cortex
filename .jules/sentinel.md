## 2024-05-18 - Missing baseline security headers
**Vulnerability:** The API responses are missing baseline security headers such as `X-Content-Type-Options`, `X-Frame-Options`, and `Strict-Transport-Security`.
**Learning:** This application's global API middleware is configured in `apps/api/src/cortex_api/middleware/request_context.py`. Adding HTTP headers directly there correctly propagates them to all API endpoints.
**Prevention:** Always add a baseline set of security headers for APIs in FastAPI. For JSON APIs, `X-Content-Type-Options`, `X-Frame-Options` and `Strict-Transport-Security` are critical to protect against MIME-type sniffing, clickjacking, and MITM attacks.
