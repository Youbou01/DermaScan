"""M1: add raw_product table

Revision ID: 20261020_0001
Revises: 1053ba9300a2
Create Date: 2026-10-20 00:01:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261020_0001"
down_revision: str | Sequence[str] | None = "1053ba9300a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "raw_product",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "source IN ('open_beauty_facts', 'scrape', 'user_photo', 'manual')",
            name=op.f("ck_raw_product_source"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_raw_product")),
        sa.UniqueConstraint(
            "source", "source_id", "content_hash", name=op.f("uq_raw_product_source_source_id_hash")
        ),
    )
    op.create_index(
        "ix_raw_product_source_source_id", "raw_product", ["source", "source_id"], unique=False
    )
    op.create_index("ix_raw_product_content_hash", "raw_product", ["content_hash"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_raw_product_content_hash", table_name="raw_product")
    op.drop_index("ix_raw_product_source_source_id", table_name="raw_product")
    op.drop_table("raw_product")
