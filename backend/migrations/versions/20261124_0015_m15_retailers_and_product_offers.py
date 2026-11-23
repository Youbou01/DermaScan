"""M15: retailers and per-retailer product offers.

Revision ID: 20261124_0015
Revises: 0953a7104b26
Create Date: 2026-11-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261124_0015"
down_revision: str | Sequence[str] | None = "0953a7104b26"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "retailer",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("logo_url", sa.Text(), nullable=True),
        sa.Column("is_affiliate", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("affiliate_label", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_retailer")),
        sa.UniqueConstraint("domain", name=op.f("uq_retailer_domain")),
    )

    op.create_table(
        "product_offer",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("retailer_id", sa.Uuid(), nullable=False),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("stock_state", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "stock_state IN ('in_stock', 'out_of_stock', 'unknown')",
            name=op.f("ck_product_offer_stock_state"),
        ),
        sa.CheckConstraint("price >= 0", name=op.f("ck_product_offer_price_non_negative")),
        sa.CheckConstraint("currency ~ '^[A-Z]{3}$'", name=op.f("ck_product_offer_currency_iso")),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["product.id"],
            name=op.f("fk_product_offer_product_id_product"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["retailer_id"],
            ["retailer.id"],
            name=op.f("fk_product_offer_retailer_id_retailer"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_product_offer")),
        sa.UniqueConstraint(
            "product_id", "retailer_id", name=op.f("uq_product_offer_product_retailer")
        ),
    )
    op.create_index(op.f("ix_product_offer_product_id"), "product_offer", ["product_id"])
    op.create_index(op.f("ix_product_offer_retailer_id"), "product_offer", ["retailer_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_product_offer_retailer_id"), table_name="product_offer")
    op.drop_index(op.f("ix_product_offer_product_id"), table_name="product_offer")
    op.drop_table("product_offer")
    op.drop_table("retailer")
