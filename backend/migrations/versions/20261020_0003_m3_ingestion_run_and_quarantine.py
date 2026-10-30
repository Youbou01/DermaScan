"""M3: add ingestion_run and quarantine_item tables

Revision ID: 20261020_0003
Revises: 20261020_0002
Create Date: 2026-10-20 00:03:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261020_0003"
down_revision: str | Sequence[str] | None = "20261020_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ingestion_run",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "counters",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ingestion_run")),
    )
    op.create_index("ix_ingestion_run_source", "ingestion_run", ["source"], unique=False)

    op.create_table(
        "quarantine_item",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("raw_product_id", sa.Uuid(), nullable=True),
        sa.Column("stage", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.String(length=128), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("reviewed_by", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name=op.f("ck_quarantine_item_status"),
        ),
        sa.ForeignKeyConstraint(
            ["raw_product_id"],
            ["raw_product.id"],
            name=op.f("fk_quarantine_item_raw_product_id_raw_product"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quarantine_item")),
    )
    op.create_index(
        "ix_quarantine_item_raw_product_id", "quarantine_item", ["raw_product_id"], unique=False
    )
    op.create_index("ix_quarantine_item_reason", "quarantine_item", ["reason"], unique=False)
    op.create_index("ix_quarantine_item_status", "quarantine_item", ["status"], unique=False)
    op.create_index(
        "ix_quarantine_item_status_created_at",
        "quarantine_item",
        ["status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_quarantine_item_status_created_at", table_name="quarantine_item")
    op.drop_index("ix_quarantine_item_status", table_name="quarantine_item")
    op.drop_index("ix_quarantine_item_reason", table_name="quarantine_item")
    op.drop_index("ix_quarantine_item_raw_product_id", table_name="quarantine_item")
    op.drop_table("quarantine_item")
    op.drop_index("ix_ingestion_run_source", table_name="ingestion_run")
    op.drop_table("ingestion_run")
