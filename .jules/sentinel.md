## YYYY-MM-DD - [Missing Security Headers in API]
**Vulnerability:** Missing standard security headers (X-Content-Type-Options, X-Frame-Options, Strict-Transport-Security) in API responses.
**Learning:** In FastAPI, these need to be explicitly set via middleware or response objects. Omitting them leaves the API vulnerable to MIME sniffing and clickjacking, and fails to enforce HTTPS.
**Prevention:** Ensure global middleware always injects baseline security headers.
