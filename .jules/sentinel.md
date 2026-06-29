
## 2024-06-29 - Centralized API Security Headers
**Vulnerability:** Missing default HTTP security headers (HSTS, X-Frame-Options, X-Content-Type-Options) in API responses, increasing risk of clickjacking and MITM attacks.
**Learning:** Rather than adding security headers to individual endpoints, they must be applied globally at the application level. FastAPI response middleware (`request_context.py` in this case) is the most robust place to inject these defense-in-depth headers to guarantee 100% coverage across all endpoints.
**Prevention:** Always implement base security headers in global middleware for API projects.
