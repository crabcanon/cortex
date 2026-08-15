## YYYY-MM-DD - Missing Security Headers
**Vulnerability:** Fastapi middleware `request_context_middleware` is missing important HTTP security headers like `X-Content-Type-Options`, `X-Frame-Options`, and `Strict-Transport-Security`.
**Learning:** These headers defend against MIME sniffing, clickjacking, and man-in-the-middle attacks respectively. They should be applied universally at the edge or middleware layer.
**Prevention:** Add baseline security headers (X-Content-Type-Options: nosniff, X-Frame-Options: DENY, Strict-Transport-Security: max-age=31536000; includeSubDomains) to the primary request middleware.
