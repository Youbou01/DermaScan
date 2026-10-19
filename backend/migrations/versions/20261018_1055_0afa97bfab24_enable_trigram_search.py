"""enable trigram search

Revision ID: 0afa97bfab24
Revises: 89cbd8128782
Create Date: 2026-10-18 10:55:54.352130

Enables two PostgreSQL extensions and adds the trigram index used by ingredient suggestions.

HAND-WRITTEN PART: Alembic autogenerate does not know about extensions. Without the
CREATE EXTENSION below, the index creation fails on any fresh database.
Both extensions are "trusted" (PostgreSQL 13+), so the database owner may create them:
no superuser is needed.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0afa97bfab24"
down_revision: str | Sequence[str] | None = "89cbd8128782"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")  # similarity(), trigram indexes
    op.execute(
        "CREATE EXTENSION IF NOT EXISTS unaccent"
    )  # reserved for accent-insensitive full-text search
    op.create_index(
        "ix_ingredient_alias_normalized_alias_trgm",
        "ingredient_alias",
        ["normalized_alias"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"normalized_alias": "gin_trgm_ops"},
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ingredient_alias_normalized_alias_trgm",
        table_name="ingredient_alias",
        postgresql_using="gin",
        postgresql_ops={"normalized_alias": "gin_trgm_ops"},
    )
    op.execute("DROP EXTENSION IF EXISTS unaccent")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
