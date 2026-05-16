## 2025-02-14 - Fix S110 in Exception handling during enum lookup
**Vulnerability:** A broad `except Exception: pass` was used when attempting to map the `search_type_name` input to `search_type_enum` (Cognee's `SearchType`).
**Learning:** This masks potential errors (e.g., system issues or unexpected payloads like incorrect types instead of strings) by swallowing the exception and silently moving forward, violating the "fail securely" and proper auditing principles. It also ignores the ruff S110 code health rule.
**Prevention:** Always use specific exceptions (like `ValueError` for Enum creation) and ensure module-level loggers record such errors to enable tracking of anomalous payloads and debugging.
