"""M7: add product enrichment, image, and score_dirty fields

Revision ID: 20261020_0007
Revises: 20261020_0006
Create Date: 2026-10-20 00:07:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261020_0007"
down_revision: str | Sequence[str] | None = "20261020_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("product", sa.Column("source_lang", sa.String(length=2), nullable=True))
    op.add_column(
        "product",
        sa.Column("name_i18n", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column("product", sa.Column("brand_source", sa.Text(), nullable=True))
    op.add_column("product", sa.Column("category_source", sa.Text(), nullable=True))
    op.add_column(
        "product",
        sa.Column("field_provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "product",
        sa.Column(
            "enrichment_status",
            sa.String(length=32),
            server_default="pending",
            nullable=False,
        ),
    )
    op.add_column(
        "product",
        sa.Column("enrichment_version", sa.SmallInteger(), server_default="1", nullable=False),
    )
    op.add_column("product", sa.Column("image_source_url", sa.Text(), nullable=True))
    op.add_column(
        "product",
        sa.Column(
            "image_status",
            sa.String(length=32),
            server_default="none",
            nullable=False,
        ),
    )
    op.add_column(
        "product", sa.Column("image_quality", sa.Numeric(precision=3, scale=2), nullable=True)
    )
    op.add_column(
        "product",
        sa.Column(
            "score_is_estimated",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "product",
        sa.Column(
            "score_dirty",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.add_column(
        "product", sa.Column("data_quality", sa.Numeric(precision=3, scale=2), nullable=True)
    )

    op.create_index("ix_product_enrichment_status", "product", ["enrichment_status"], unique=False)
    op.create_index("ix_product_image_status", "product", ["image_status"], unique=False)
    op.create_index(
        "ix_product_score_dirty_partial",
        "product",
        ["score_dirty"],
        unique=False,
        postgresql_where=sa.text("score_dirty = true"),
    )

    op.execute(
        "ALTER TABLE product ADD CONSTRAINT ck_product_enrichment_status "
        "CHECK (enrichment_status IN ('pending', 'done', 'quarantined', 'failed'))"
    )
    op.execute(
        "ALTER TABLE product ADD CONSTRAINT ck_product_image_status "
        "CHECK (image_status IN ('none', 'candidate', 'processed', 'failed'))"
    )

    # Update source check constraint to include new sources
    op.execute("ALTER TABLE product DROP CONSTRAINT IF EXISTS ck_product_source")
    op.execute(
        "ALTER TABLE product ADD CONSTRAINT ck_product_source "
        "CHECK (source IN ('open_beauty_facts', 'scrape', 'user_photo', 'manual'))"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE product DROP CONSTRAINT IF EXISTS ck_product_source")
    op.execute(
        "ALTER TABLE product ADD CONSTRAINT ck_product_source "
        "CHECK (source IN ('open_beauty_facts', 'manual'))"
    )
    op.execute("ALTER TABLE product DROP CONSTRAINT IF EXISTS ck_product_image_status")
    op.execute("ALTER TABLE product DROP CONSTRAINT IF EXISTS ck_product_enrichment_status")
    op.drop_index(
        "ix_product_score_dirty_partial",
        table_name="product",
        postgresql_where=sa.text("score_dirty = true"),
    )
    op.drop_index("ix_product_image_status", table_name="product")
    op.drop_index("ix_product_enrichment_status", table_name="product")
    op.drop_column("product", "data_quality")
    op.drop_column("product", "score_dirty")
    op.drop_column("product", "score_is_estimated")
    op.drop_column("product", "image_quality")
    op.drop_column("product", "image_status")
    op.drop_column("product", "image_source_url")
    op.drop_column("product", "enrichment_version")
    op.drop_column("product", "enrichment_status")
    op.drop_column("product", "field_provenance")
    op.drop_column("product", "category_source")
    op.drop_column("product", "brand_source")
    op.drop_column("product", "name_i18n")
    op.drop_column("product", "source_lang")
