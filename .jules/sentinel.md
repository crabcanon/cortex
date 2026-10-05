## 2025-02-14 - Add Baseline API Security Headers
**Vulnerability:** Missing baseline security headers on API responses (X-Content-Type-Options, X-Frame-Options, Strict-Transport-Security).
**Learning:** The application lacked defense-in-depth protection against MIME sniffing, clickjacking, and HTTPS downgrade attacks.
**Prevention:** Ensured security headers are applied globally in the FastAPI `request_context_middleware` to protect all endpoints uniformly.
