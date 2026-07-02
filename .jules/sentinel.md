## 2024-07-02 - API Security Headers Missing
**Vulnerability:** Missing fundamental security headers (HSTS, X-Frame-Options, X-Content-Type-Options) in FastAPI response middleware.
**Learning:** By default, FastAPI doesn't include these headers. They need to be explicitly set in a global middleware to ensure all endpoints are protected against clickjacking, MIME-sniffing, and downgrade attacks. As noted in the codebase memory, Content-Security-Policy should be omitted or configured carefully for API documentation.
**Prevention:** Always implement standard security headers in the global request/response middleware of the application.
