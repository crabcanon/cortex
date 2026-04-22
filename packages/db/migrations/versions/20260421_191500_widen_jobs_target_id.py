"""Widen jobs.target_id for URL and object locator targets."""

import sqlalchemy as sa
from alembic import op

revision = "20260421_191500"
down_revision = "20260412_220800"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("jobs") as batch_op:
        batch_op.alter_column(
            "target_id",
            existing_type=sa.String(length=36),
            type_=sa.String(length=2048),
            existing_nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("jobs") as batch_op:
        batch_op.alter_column(
            "target_id",
            existing_type=sa.String(length=2048),
            type_=sa.String(length=36),
            existing_nullable=True,
        )
