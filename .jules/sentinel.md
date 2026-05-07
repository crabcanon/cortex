## 2026-05-07 - Add security headers in API response
**Vulnerability:** Missing security headers in API responses
**Learning:** Security headers like Strict-Transport-Security, X-Frame-Options, and X-Content-Type-Options were not set in the FastAPI responses, making the API vulnerable to clickjacking, MIME sniffing, and MITM attacks.
**Prevention:** Ensured the API middleware adds standard security headers to all responses.

## 2026-05-07 - Fix AttributeError in type checking for evaluation models
**Vulnerability:** Application error (Unhandled exception) leading to crashes
**Learning:** Calling `rstrip()` on `None` when an API URL was optionally provided led to an `AttributeError`. DeepEval adapters were passing this potentially `None` `provider_config.api_url` parameter without validating its existence or conditionally calling string methods.
**Prevention:** Implement safe type guarding (e.g. `val if val else None` or `val or ""`) before executing string manipulation methods on configuration fields that may return `None`.
