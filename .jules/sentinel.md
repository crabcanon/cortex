## 2026-04-12 - [Critical] SQL Injection in Alembic Migrations
**Vulnerability:** SQL Injection in Alembic Migration
**Learning:** Alembic's `op.execute()` with string interpolation (e.g. `f"DROP TABLE IF EXISTS {table_name}"`) is vulnerable to SQL injection.
**Prevention:** Always use Alembic's built-in schema operations (e.g. `op.drop_table()`). When dropping a table conditionally, use `sa.inspect()` to get table names and conditionally drop it since `op.drop_table()` does not support `if_exists=True`.
