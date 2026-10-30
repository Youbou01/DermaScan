"""M4: add ingredient columns, constraints and backfill ratings

Revision ID: 20261020_0004
Revises: 20261020_0003
Create Date: 2026-10-20 00:04:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261020_0004"
down_revision: str | Sequence[str] | None = "20261020_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ingredient", sa.Column("rating", sa.Numeric(precision=3, scale=1), nullable=True)
    )
    op.add_column(
        "ingredient",
        sa.Column("rating_confidence", sa.Numeric(precision=3, scale=2), nullable=True),
    )
    op.add_column(
        "ingredient",
        sa.Column(
            "rating_source",
            sa.String(length=32),
            server_default="unrated",
            nullable=False,
        ),
    )
    op.add_column(
        "ingredient",
        sa.Column("rating_version", sa.SmallInteger(), server_default="1", nullable=False),
    )
    op.add_column("ingredient", sa.Column("rating_model", sa.Text(), nullable=True))
    op.add_column("ingredient", sa.Column("functions", postgresql.ARRAY(sa.Text()), nullable=True))
    op.add_column(
        "ingredient",
        sa.Column("is_prohibited", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "ingredient",
        sa.Column("is_restricted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "ingredient",
        sa.Column("is_allergen", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column("ingredient", sa.Column("cosing_id", sa.Text(), nullable=True))
    op.add_column("ingredient", sa.Column("cas", sa.Text(), nullable=True))
    op.add_column("ingredient", sa.Column("taxonomy_id", sa.Text(), nullable=True))
    op.add_column(
        "ingredient",
        sa.Column(
            "review_status",
            sa.String(length=32),
            server_default="auto",
            nullable=False,
        ),
    )

    op.create_index("ix_ingredient_cosing_id", "ingredient", ["cosing_id"], unique=False)
    op.create_index("ix_ingredient_taxonomy_id", "ingredient", ["taxonomy_id"], unique=False)

    op.execute(
        "ALTER TABLE ingredient ADD CONSTRAINT ck_ingredient_rating_source "
        "CHECK (rating_source IN ('regulatory', 'curated', 'ai', 'unrated'))"
    )
    op.execute(
        "ALTER TABLE ingredient ADD CONSTRAINT ck_ingredient_review_status "
        "CHECK (review_status IN ('auto', 'needs_review', 'approved'))"
    )
    op.execute(
        "ALTER TABLE ingredient ADD CONSTRAINT ck_ingredient_rating_range "
        "CHECK (rating IS NULL OR (rating >= 0 AND rating <= 10))"
    )

    # Backfill ratings for existing ingredients to satisfy rating_risk_level_sync
    op.execute(
        "UPDATE ingredient SET rating = 9.0, rating_source = 'curated' "
        "WHERE risk_level = 'low' AND rating IS NULL"
    )
    op.execute(
        "UPDATE ingredient SET rating = 5.5, rating_source = 'curated' "
        "WHERE risk_level = 'moderate' AND rating IS NULL"
    )
    op.execute(
        "UPDATE ingredient SET rating = 2.0, rating_source = 'curated' "
        "WHERE risk_level = 'high' AND rating IS NULL"
    )
    op.execute("UPDATE ingredient SET rating_source = 'unrated' WHERE rating IS NULL")

    op.execute(
        "ALTER TABLE ingredient ADD CONSTRAINT ck_ingredient_rating_risk_level_sync "
        "CHECK ((rating IS NULL AND risk_level = 'unknown') "
        "OR (rating >= 7.0 AND risk_level = 'low') "
        "OR (rating >= 4.0 AND rating < 7.0 AND risk_level = 'moderate') "
        "OR (rating < 4.0 AND risk_level = 'high'))"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE ingredient DROP CONSTRAINT IF EXISTS ck_ingredient_rating_risk_level_sync"
    )
    op.execute("ALTER TABLE ingredient DROP CONSTRAINT IF EXISTS ck_ingredient_rating_range")
    op.execute("ALTER TABLE ingredient DROP CONSTRAINT IF EXISTS ck_ingredient_review_status")
    op.execute("ALTER TABLE ingredient DROP CONSTRAINT IF EXISTS ck_ingredient_rating_source")
    op.drop_index("ix_ingredient_taxonomy_id", table_name="ingredient")
    op.drop_index("ix_ingredient_cosing_id", table_name="ingredient")
    op.drop_column("ingredient", "review_status")
    op.drop_column("ingredient", "taxonomy_id")
    op.drop_column("ingredient", "cas")
    op.drop_column("ingredient", "cosing_id")
    op.drop_column("ingredient", "is_allergen")
    op.drop_column("ingredient", "is_restricted")
    op.drop_column("ingredient", "is_prohibited")
    op.drop_column("ingredient", "functions")
    op.drop_column("ingredient", "rating_model")
    op.drop_column("ingredient", "rating_version")
    op.drop_column("ingredient", "rating_source")
    op.drop_column("ingredient", "rating_confidence")
    op.drop_column("ingredient", "rating")
