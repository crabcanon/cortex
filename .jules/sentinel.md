## 2024-06-25 - Missing Global API Security Headers
**Vulnerability:** The API lacked basic security headers (HSTS, X-Frame-Options, X-Content-Type-Options) in responses.
**Learning:** Security headers are easily forgotten but crucial for defense-in-depth against clickjacking, MIME sniffing, and enforcing HTTPS.
**Prevention:** Always ensure standard security headers are applied in a global middleware when setting up web application frameworks like FastAPI.