"""M8: add scrape_staging and calibration_reference tables

Revision ID: 20261020_0008
Revises: 20261020_0007
Create Date: 2026-10-20 00:08:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261020_0008"
down_revision: str | Sequence[str] | None = "20261020_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scrape_staging",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("extracted_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["ingestion_run.id"],
            name=op.f("fk_scrape_staging_run_id_ingestion_run"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scrape_staging")),
    )
    op.create_index("ix_scrape_staging_url", "scrape_staging", ["url"], unique=False)
    op.create_index(
        "ix_scrape_staging_content_hash", "scrape_staging", ["content_hash"], unique=False
    )
    op.create_index("ix_scrape_staging_run_id", "scrape_staging", ["run_id"], unique=False)

    op.create_table(
        "calibration_reference",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=True),
        sa.Column("barcode", sa.String(length=13), nullable=False),
        sa.Column("reference_score", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column(
            "collected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["product.id"],
            name=op.f("fk_calibration_reference_product_id_product"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_calibration_reference")),
    )
    op.create_index(
        "ix_calibration_reference_barcode", "calibration_reference", ["barcode"], unique=False
    )
    op.create_index(
        "ix_calibration_reference_product_id",
        "calibration_reference",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        "ix_calibration_reference_source", "calibration_reference", ["source"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_calibration_reference_source", table_name="calibration_reference")
    op.drop_index("ix_calibration_reference_product_id", table_name="calibration_reference")
    op.drop_index("ix_calibration_reference_barcode", table_name="calibration_reference")
    op.drop_table("calibration_reference")
    op.drop_index("ix_scrape_staging_run_id", table_name="scrape_staging")
    op.drop_index("ix_scrape_staging_content_hash", table_name="scrape_staging")
    op.drop_index("ix_scrape_staging_url", table_name="scrape_staging")
    op.drop_table("scrape_staging")
