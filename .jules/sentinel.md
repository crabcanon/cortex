## 2025-02-24 - SQL Injection in Alembic Migrations
**Vulnerability:** Found manual execution of string-interpolated SQL statements (`op.execute(sa.text(f"DROP TABLE IF EXISTS {table_name}"))`) in Alembic down-migrations.
**Learning:** Manual SQL queries using f-strings inside migration files bypass safe identifier quoting, posing a SQL injection risk even if inputs seemingly come from static arrays. `op.drop_table` does not natively support `IF EXISTS`.
**Prevention:** Use Alembic's built-in schema operations (`op.drop_table`). When an "if exists" check is required, first inspect the current schema tables via `sa.inspect(op.get_bind()).get_table_names()`, then safely drop if found.
