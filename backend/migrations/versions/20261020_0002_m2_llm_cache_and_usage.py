"""M2: add llm_cache and llm_usage tables

Revision ID: 20261020_0002
Revises: 20261020_0001
Create Date: 2026-10-20 00:02:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261020_0002"
down_revision: str | Sequence[str] | None = "20261020_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "llm_cache",
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("response_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_llm_cache")),
    )
    op.create_index("ix_llm_cache_provider", "llm_cache", ["provider"], unique=False)

    op.create_table(
        "llm_usage",
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("requests", sa.Integer(), server_default="0", nullable=False),
        sa.Column("tokens", sa.Integer(), server_default="0", nullable=False),
        sa.PrimaryKeyConstraint("provider", "date", name=op.f("pk_llm_usage")),
    )


def downgrade() -> None:
    op.drop_table("llm_usage")
    op.drop_index("ix_llm_cache_provider", table_name="llm_cache")
    op.drop_table("llm_cache")
