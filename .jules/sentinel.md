## 2024-05-24 - [Missing API Security Headers]
**Vulnerability:** Fast API implementation in `cortex_api` lacked basic security headers like `Strict-Transport-Security`, `X-Content-Type-Options`, and `X-Frame-Options` in HTTP responses, leaving it vulnerable to clickjacking and MIME-sniffing.
**Learning:** In FastAPI, these headers are not injected by default. It requires explicit addition either through response objects directly or via middleware, which is where we've added it (`apps/api/src/cortex_api/middleware/request_context.py`) so it applies globally to all responses.
**Prevention:** Consider configuring global HTTP middleware for secure defaults.
