## 2024-05-18 - [API Security Headers]
**Vulnerability:** Missing foundational security headers (HSTS, X-Frame-Options, X-Content-Type-Options) in the FastAPI responses.
**Learning:** Security headers were not being globally applied to all API endpoints, leaving the application susceptible to downgrade attacks, clickjacking, and MIME-type sniffing. Centralized middleware (`request_context.py`) is the correct place to enforce these policies across the entire API surface.
**Prevention:** Ensure that all new FastAPI applications or major route realignments verify the presence of a central security header middleware. When modifying the `request_context.py` middleware, verify that existing headers are preserved and not accidentally removed.
