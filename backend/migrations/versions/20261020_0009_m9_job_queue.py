"""M9: add PostgreSQL job queue table

Revision ID: 20261020_0009
Revises: 20261020_0008
Create Date: 2026-10-20 00:09:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261020_0009"
down_revision: str | Sequence[str] | None = "20261020_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "job",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("queue", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("task_name", sa.String(length=128), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default="3", nullable=False),
        sa.Column(
            "scheduled_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job")),
    )
    op.create_index("ix_job_queue", "job", ["queue"], unique=False)
    op.create_index("ix_job_task_name", "job", ["task_name"], unique=False)
    op.create_index("ix_job_status", "job", ["status"], unique=False)
    op.create_index("ix_job_scheduled_at", "job", ["scheduled_at"], unique=False)
    op.create_index(
        "ix_job_queue_status_scheduled_at",
        "job",
        ["queue", "status", "scheduled_at"],
        unique=False,
    )
    op.execute(
        "ALTER TABLE job ADD CONSTRAINT ck_job_status "
        "CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled'))"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE job DROP CONSTRAINT IF EXISTS ck_job_status")
    op.drop_index("ix_job_queue_status_scheduled_at", table_name="job")
    op.drop_index("ix_job_scheduled_at", table_name="job")
    op.drop_index("ix_job_status", table_name="job")
    op.drop_index("ix_job_task_name", table_name="job")
    op.drop_index("ix_job_queue", table_name="job")
    op.drop_table("job")
