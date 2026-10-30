"""M6: add language and source to ingredient_alias

Revision ID: 20261020_0006
Revises: 20261020_0005
Create Date: 2026-10-20 00:06:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261020_0006"
down_revision: str | Sequence[str] | None = "20261020_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ingredient_alias",
        sa.Column("language", sa.String(length=2), nullable=True),
    )
    op.add_column(
        "ingredient_alias",
        sa.Column(
            "source",
            sa.String(length=32),
            server_default="seed",
            nullable=False,
        ),
    )
    op.execute(
        "ALTER TABLE ingredient_alias ADD CONSTRAINT ck_ingredient_alias_source "
        "CHECK (source IN ('seed', 'cosing', 'taxonomy', 'ai', 'manual'))"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE ingredient_alias DROP CONSTRAINT IF EXISTS ck_ingredient_alias_source")
    op.drop_column("ingredient_alias", "source")
    op.drop_column("ingredient_alias", "language")
