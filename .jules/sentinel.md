## YYYY-MM-DD - [Baseline Security Headers]
**Vulnerability:** Missing baseline API security headers (e.g. X-Content-Type-Options, X-Frame-Options, Strict-Transport-Security)
**Learning:** These basic security headers were not being globally set in the application middleware. This could expose users to MIME sniffing attacks, clickjacking, and man-in-the-middle attacks over insecure channels.
**Prevention:** These baseline security headers should always be added in the global request handling middleware to ensure all endpoints automatically receive them.
