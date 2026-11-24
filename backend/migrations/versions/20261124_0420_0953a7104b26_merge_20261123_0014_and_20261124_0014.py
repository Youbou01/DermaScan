"""merge 20261123_0014 and 20261124_0014

Revision ID: 0953a7104b26
Revises: 20261123_0014, 20261124_0014
Create Date: 2026-11-24 04:20:15.406470

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "0953a7104b26"
down_revision: str | Sequence[str] | None = ("20261123_0014", "20261124_0014")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
