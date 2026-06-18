## 2024-05-18 - SQLAlchemy Alembic Injection Vulnerability
**Vulnerability:** Raw string interpolation with `op.execute(sa.text(f"DROP TABLE IF EXISTS {table_name}"))` in Alembic database migrations.
**Learning:** Manual SQL execution with string interpolation is an injection vulnerability, and `op.drop_table` doesn't natively support `if_exists=True`.
**Prevention:** Use standard Alembic operations like `op.drop_table()`. When conditional dropping is required, use `sa.inspect(op.get_bind()).get_table_names()` to check for the existence of the table prior to executing `op.drop_table()`.
