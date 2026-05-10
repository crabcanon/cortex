"""Baseline schema bootstrap from cortex-init.sql."""

from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "20260412_220800"
down_revision = None
branch_labels = None
depends_on = None

TABLE_DROP_ORDER = [
    "search_hits",
    "search_requests",
    "knowledge_runs",
    "parse_run_attempts",
    "parse_runs",
    "job_events",
    "jobs",
    "dataset_items",
    "datasets",
    "document_chunks",
    "document_tags",
    "document_artifacts",
    "documents",
    "crawl_sessions",
    "parser_profiles",
    "parser_engines",
    "object_versions",
    "objects",
    "storage_buckets",
    "authorization_decisions",
    "authorization_policies",
    "actor_role_bindings",
    "role_permissions",
    "roles",
    "permissions",
    "actors",
    "tenants",
]


def _load_sql_script() -> str:
    repo_root = Path(__file__).resolve().parents[4]
    return (repo_root / "specs" / "cortex-init.sql").read_text(encoding="utf-8")


def _iter_statements(script: str) -> list[str]:
    lines = []
    for raw_line in script.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("--"):
            continue
        if stripped.upper() in {"BEGIN TRANSACTION;", "COMMIT;"}:
            continue
        lines.append(raw_line)
    cleaned = "\n".join(lines)
    return [statement.strip() for statement in cleaned.split(";") if statement.strip()]


def upgrade() -> None:
    for statement in _iter_statements(_load_sql_script()):
        op.execute(sa.text(statement))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_tables = inspector.get_table_names()
    for table_name in TABLE_DROP_ORDER:
        if table_name in existing_tables:
            op.drop_table(table_name)
