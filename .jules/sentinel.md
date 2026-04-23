## 2025-05-18 - Avoid String Interpolation in Alembic Migrations
**Vulnerability:** Raw SQL execution via `op.execute` with string interpolated arguments (`f"DROP TABLE IF EXISTS {table_name}"`) found in Alembic migrations.
**Learning:** Even when interpolating a hardcoded, trusted list of strings, passing a formatted string to `sa.text()` creates a poor security pattern that bypasses static analysis tools and risks SQL injection if lists are modified by external inputs.
**Prevention:** Always use Alembic's built-in schema operations (like `op.drop_table`) when modifying schema structures, as they safely handle identifier quoting and protect against injection vulnerabilities.
