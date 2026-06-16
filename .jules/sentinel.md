## 2024-06-16 - Add API Security Headers
**Vulnerability:** Missing security headers on API responses (e.g., HSTS, X-Frame-Options, X-Content-Type-Options) leaves the application susceptible to man-in-the-middle attacks, clickjacking, and MIME-sniffing.
**Learning:** Adding `Content-Security-Policy` headers globally in FastAPI middleware can inadvertently break web-based API documentation (like Swagger UI or Redoc) which relies on inline scripts or external assets. For JSON APIs, it is often safer to omit CSP entirely while keeping HSTS, X-Frame-Options, and X-Content-Type-Options.
**Prevention:** Always implement standard security headers for APIs, but test the impact on auto-generated documentation endpoints. Use a centralized response middleware to enforce these headers consistently.
