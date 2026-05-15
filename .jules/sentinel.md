## 2026-05-15 - [CRITICAL] Prevent SQL Injection in Alembic Migrations
**Vulnerability:** Found string-interpolated SQL execution `op.execute(sa.text(f"DROP TABLE IF EXISTS {table_name}"))` in Alembic downgrade script.
**Learning:** Alembic's `op.drop_table` does not natively support `if_exists=True`. Developers might resort to unsafe string-interpolated `op.execute()` to conditionally drop tables, potentially introducing SQL injection vectors.
**Prevention:** To safely drop a table conditionally in Alembic without string concatenation, always retrieve existing tables using SQLAlchemy's inspector (`sa.inspect(op.get_bind()).get_table_names()`) and then invoke the secure `op.drop_table(table_name)` command if the table name is verified as existing.
