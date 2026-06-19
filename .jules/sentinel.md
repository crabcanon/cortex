## 2025-05-18 - Added Standard API Security Headers
**Vulnerability:** Missing security headers (HSTS, nosniff, frame-options).
**Learning:** The Cortex API middleware (`request_context_middleware`) handles response correlation headers, making it the perfect central location to apply standard security headers without modifying individual route handlers.
**Prevention:** Include API security headers explicitly in global middleware to ensure all endpoints have basic protections against clickjacking, MIME sniffing, and insecure connections.
