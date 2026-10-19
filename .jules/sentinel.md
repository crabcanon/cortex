## 2024-05-18 - [Add Security Headers]
**Vulnerability:** Missing baseline security headers like X-Content-Type-Options, X-Frame-Options, Strict-Transport-Security in HTTP responses.
**Learning:** These headers defend against basic web vulnerabilities (MIME-sniffing, Clickjacking, MITM). Middlewares are the best place to add them globally.
**Prevention:** Ensure global API middleware includes necessary security headers for all endpoints.
