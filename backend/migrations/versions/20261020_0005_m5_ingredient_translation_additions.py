"""M5: add summary and concern_note to ingredient_translation

Revision ID: 20261020_0005
Revises: 20261020_0004
Create Date: 2026-10-20 00:05:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261020_0005"
down_revision: str | Sequence[str] | None = "20261020_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("ingredient_translation", sa.Column("summary", sa.Text(), nullable=True))
    op.add_column("ingredient_translation", sa.Column("concern_note", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("ingredient_translation", "concern_note")
    op.drop_column("ingredient_translation", "summary")
