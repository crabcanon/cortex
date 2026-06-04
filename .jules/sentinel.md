## 2024-06-04 - [Missing Security Headers in API]
**Vulnerability:** The API lacked basic security headers like `Strict-Transport-Security`, `X-Frame-Options`, `X-Content-Type-Options`, and `X-XSS-Protection`.
**Learning:** These headers are important for defense in depth, and their absence in `request_context.py` middleware leaves API responses more vulnerable.
**Prevention:** Always ensure standard security headers are applied to HTTP responses, either at the reverse proxy layer or within the application's middleware.