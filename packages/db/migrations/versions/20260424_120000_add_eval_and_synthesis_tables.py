"""Add evaluation and synthesis persistence tables."""

import sqlalchemy as sa
from alembic import op

revision = "20260424_120000"
down_revision = "20260421_191500"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_tables = set(inspector.get_table_names())
    if {"eval_engines", "eval_metric_definitions", "eval_runs", "eval_run_metrics"}.issubset(
        existing_tables
    ) and {"synthesis_engines", "synthesis_runs"}.issubset(existing_tables):
        return

    op.create_table(
        "eval_engines",
        sa.Column("engine_id", sa.String(length=36), primary_key=True),
        sa.Column("engine_key", sa.String(length=128), nullable=False, unique=True),
        sa.Column("display_name", sa.String(length=256), nullable=False),
        sa.Column("engine_kind", sa.String(length=64), nullable=False),
        sa.Column("capability_flags_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("metric_prefixes_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("supported_modes_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("runtime_config_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_table(
        "eval_metric_definitions",
        sa.Column("metric_key", sa.String(length=128), primary_key=True),
        sa.Column("display_name", sa.String(length=256), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("unit", sa.String(length=64), nullable=True),
        sa.Column("score_direction", sa.String(length=32), nullable=False),
        sa.Column("eval_types_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("engine_bindings_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("threshold_hint", sa.Numeric(12, 6), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_table(
        "synthesis_engines",
        sa.Column("engine_id", sa.String(length=36), primary_key=True),
        sa.Column("engine_key", sa.String(length=128), nullable=False, unique=True),
        sa.Column("display_name", sa.String(length=256), nullable=False),
        sa.Column("engine_kind", sa.String(length=64), nullable=False),
        sa.Column("capability_flags_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column(
            "supported_source_types_json",
            sa.Text(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("output_formats_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("runtime_config_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_table(
        "eval_runs",
        sa.Column("eval_run_id", sa.String(length=36), primary_key=True),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("dataset_id", sa.String(length=36), nullable=True),
        sa.Column("eval_type", sa.String(length=32), nullable=False),
        sa.Column("engine_id", sa.String(length=36), nullable=False),
        sa.Column("profile_key", sa.String(length=128), nullable=True),
        sa.Column("input_ref_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("target_ref_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("metrics_config_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("summary_results_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("sample_summary_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("report_object_id", sa.String(length=36), nullable=True),
        sa.Column("result_dataset_id", sa.String(length=36), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("span_id", sa.String(length=32), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.job_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.dataset_id"]),
        sa.ForeignKeyConstraint(["engine_id"], ["eval_engines.engine_id"]),
        sa.ForeignKeyConstraint(["report_object_id"], ["objects.object_id"]),
        sa.ForeignKeyConstraint(["result_dataset_id"], ["datasets.dataset_id"]),
        sa.ForeignKeyConstraint(["created_by"], ["actors.actor_id"]),
        sa.UniqueConstraint("job_id"),
    )
    op.create_index(
        "idx_eval_runs_tenant_created_at",
        "eval_runs",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "idx_eval_runs_engine_type",
        "eval_runs",
        ["engine_id", "eval_type"],
    )
    op.create_index(
        "idx_eval_runs_trace_id",
        "eval_runs",
        ["trace_id", "created_at"],
    )
    op.create_table(
        "eval_run_metrics",
        sa.Column("eval_run_id", sa.String(length=36), nullable=False),
        sa.Column("metric_index", sa.Integer(), nullable=False),
        sa.Column("metric_key", sa.String(length=128), nullable=False),
        sa.Column("engine_id", sa.String(length=36), nullable=False),
        sa.Column("native_metric_key", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("score", sa.Numeric(12, 6), nullable=True),
        sa.Column("threshold", sa.Numeric(12, 6), nullable=True),
        sa.Column("unit", sa.String(length=64), nullable=True),
        sa.Column("sample_size", sa.Integer(), nullable=True),
        sa.Column("details_json", sa.Text(), nullable=False, server_default="{}"),
        sa.ForeignKeyConstraint(["eval_run_id"], ["eval_runs.eval_run_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["engine_id"], ["eval_engines.engine_id"]),
        sa.PrimaryKeyConstraint("eval_run_id", "metric_index"),
    )
    op.create_index(
        "idx_eval_run_metrics_metric_key",
        "eval_run_metrics",
        ["metric_key", "status"],
    )
    op.create_table(
        "synthesis_runs",
        sa.Column("synthesis_run_id", sa.String(length=36), primary_key=True),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("dataset_id", sa.String(length=36), nullable=True),
        sa.Column("synthesis_type", sa.String(length=64), nullable=False),
        sa.Column("engine_id", sa.String(length=36), nullable=False),
        sa.Column("profile_key", sa.String(length=128), nullable=True),
        sa.Column("source_ref_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("config_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("quality_summary_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("output_summary_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("output_object_id", sa.String(length=36), nullable=True),
        sa.Column("output_dataset_id", sa.String(length=36), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("span_id", sa.String(length=32), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.job_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.dataset_id"]),
        sa.ForeignKeyConstraint(["engine_id"], ["synthesis_engines.engine_id"]),
        sa.ForeignKeyConstraint(["output_object_id"], ["objects.object_id"]),
        sa.ForeignKeyConstraint(["output_dataset_id"], ["datasets.dataset_id"]),
        sa.ForeignKeyConstraint(["created_by"], ["actors.actor_id"]),
        sa.UniqueConstraint("job_id"),
    )
    op.create_index(
        "idx_synthesis_runs_tenant_created_at",
        "synthesis_runs",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "idx_synthesis_runs_engine_type",
        "synthesis_runs",
        ["engine_id", "synthesis_type"],
    )
    op.create_index(
        "idx_synthesis_runs_trace_id",
        "synthesis_runs",
        ["trace_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_synthesis_runs_trace_id", table_name="synthesis_runs")
    op.drop_index("idx_synthesis_runs_engine_type", table_name="synthesis_runs")
    op.drop_index("idx_synthesis_runs_tenant_created_at", table_name="synthesis_runs")
    op.drop_table("synthesis_runs")
    op.drop_index("idx_eval_run_metrics_metric_key", table_name="eval_run_metrics")
    op.drop_table("eval_run_metrics")
    op.drop_index("idx_eval_runs_trace_id", table_name="eval_runs")
    op.drop_index("idx_eval_runs_engine_type", table_name="eval_runs")
    op.drop_index("idx_eval_runs_tenant_created_at", table_name="eval_runs")
    op.drop_table("eval_runs")
    op.drop_table("synthesis_engines")
    op.drop_table("eval_metric_definitions")
    op.drop_table("eval_engines")
