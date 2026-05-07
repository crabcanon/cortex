## 2026-05-07 - Added security headers in API response
**Vulnerability:** Missing security headers in API responses
**Learning:** Security headers like Strict-Transport-Security, X-Frame-Options, and X-Content-Type-Options were not set in the FastAPI responses, making the API vulnerable to clickjacking, MIME sniffing, and MITM attacks.
**Prevention:** Ensured the API middleware adds standard security headers to all responses.
