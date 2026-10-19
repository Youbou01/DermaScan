"""add product name_normalized with trigram index

Revision ID: 180c91c0c338
Revises: f72447111ba7
Create Date: 2026-10-19 18:16:19.283652

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "180c91c0c338"
down_revision: str | Sequence[str] | None = "e8a270eb4ee3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("product", sa.Column("name_normalized", sa.Text(), nullable=True))
    op.execute(
        r"""UPDATE product SET name_normalized = trim(regexp_replace(
            regexp_replace(lower(unaccent(name)), '[^\w\s]', ' ', 'g'), '\s+', ' ', 'g'))"""
    )
    op.alter_column("product", "name_normalized", nullable=False)
    op.create_index(
        "ix_product_name_normalized_trgm",
        "product",
        ["name_normalized"],
        postgresql_using="gin",
        postgresql_ops={"name_normalized": "gin_trgm_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_product_name_normalized_trgm", table_name="product")
    op.drop_column("product", "name_normalized")
