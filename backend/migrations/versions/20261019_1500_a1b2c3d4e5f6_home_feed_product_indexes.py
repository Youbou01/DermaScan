"""home feed product indexes

Revision ID: a1b2c3d4e5f6
Revises: 0afa97bfab24
Create Date: 2026-10-19 15:00:00.000000

Indexes for the home-feed shelves (top-rated by score, recently added by created_at).
D7 may add further shared keyset helpers on top of these.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "0afa97bfab24"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_product_score_desc_id",
        "product",
        ["score", "id"],
        unique=False,
        postgresql_ops={"score": "DESC"},
        postgresql_where="score IS NOT NULL AND score_band <> 'unknown'",
    )
    op.create_index(
        "ix_product_created_at_desc_id",
        "product",
        ["created_at", "id"],
        unique=False,
        postgresql_ops={"created_at": "DESC", "id": "DESC"},
    )


def downgrade() -> None:
    op.drop_index("ix_product_created_at_desc_id", table_name="product")
    op.drop_index(
        "ix_product_score_desc_id",
        table_name="product",
        postgresql_where="score IS NOT NULL AND score_band <> 'unknown'",
    )
