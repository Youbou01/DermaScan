"""Widen ingredient inci_name and alias to text

Revision ID: 20261020_0010
Revises: 20261020_0009
Create Date: 2026-10-20 00:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261020_0010"
down_revision: str | Sequence[str] | None = "20261020_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "ingredient",
        "inci_name",
        existing_type=sa.String(length=255),
        type_=sa.Text(),
        existing_nullable=False,
    )
    op.alter_column(
        "ingredient_alias",
        "alias",
        existing_type=sa.String(length=255),
        type_=sa.Text(),
        existing_nullable=False,
    )
    op.alter_column(
        "ingredient_alias",
        "normalized_alias",
        existing_type=sa.String(length=255),
        type_=sa.Text(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "ingredient_alias",
        "normalized_alias",
        existing_type=sa.Text(),
        type_=sa.String(length=255),
        existing_nullable=False,
    )
    op.alter_column(
        "ingredient_alias",
        "alias",
        existing_type=sa.Text(),
        type_=sa.String(length=255),
        existing_nullable=False,
    )
    op.alter_column(
        "ingredient",
        "inci_name",
        existing_type=sa.Text(),
        type_=sa.String(length=255),
        existing_nullable=False,
    )
