## 2025-02-26 - SQL Injection in Alembic Migrations
**Vulnerability:** String interpolation used with raw SQL execution (`op.execute(sa.text(f"DROP TABLE IF EXISTS {table_name}"))`) in Alembic migrations introduces potential SQL injection risks, even for internal tooling, because it fails to properly quote identifiers.
**Learning:** Alembic's built-in `op.drop_table` does not fully support `if_exists=True`. Developers resorted to raw SQL string interpolation to achieve "DROP TABLE IF EXISTS", exposing a vulnerability.
**Prevention:** Instead of string interpolation in raw SQL, use `sa.inspect(op.get_bind()).get_table_names()` to check for table existence, followed by a safe `op.drop_table(table_name)` if the table exists.
