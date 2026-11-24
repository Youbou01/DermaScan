"""M14: product reviews, external review source cache, and product rating aggregates.

Revision ID: 20261124_0014
Revises: 20261111_0013
Create Date: 2026-11-24 00:14:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261124_0014"
down_revision: str | Sequence[str] | None = "20261111_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "product", sa.Column("avg_rating", sa.Numeric(precision=3, scale=2), nullable=True)
    )
    op.add_column(
        "product", sa.Column("review_count", sa.Integer(), server_default="0", nullable=False)
    )
    op.create_check_constraint(
        "avg_rating_range",
        "product",
        "avg_rating IS NULL OR (avg_rating >= 1.0 AND avg_rating <= 5.0)",
    )
    op.create_check_constraint(
        "review_count_non_negative",
        "product",
        "review_count >= 0",
    )
    op.create_index(
        "ix_product_avg_rating_id",
        "product",
        ["avg_rating", "id"],
        unique=False,
        postgresql_where=sa.text("avg_rating IS NOT NULL"),
    )

    op.create_table(
        "review",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "source",
            sa.Enum("app", "reddit", name="reviewsource", native_enum=False, length=32),
            server_default="app",
            nullable=False,
        ),
        sa.Column("author_name", sa.String(length=120), nullable=False),
        sa.Column("rating", sa.SmallInteger(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=True),
        sa.Column("external_url", sa.Text(), nullable=True),
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
        sa.CheckConstraint("source IN ('app', 'reddit')", name=op.f("ck_review_source")),
        sa.CheckConstraint(
            "rating IS NULL OR rating BETWEEN 1 AND 5", name=op.f("ck_review_rating_range")
        ),
        sa.CheckConstraint(
            "source <> 'app' OR (user_id IS NOT NULL AND rating IS NOT NULL)",
            name=op.f("ck_review_app_review_requires_user_and_rating"),
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["product.id"],
            name=op.f("fk_review_product_id_product"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_account.id"],
            name=op.f("fk_review_user_id_user_account"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_review")),
    )
    op.create_index(op.f("ix_review_product_id"), "review", ["product_id"], unique=False)
    op.create_index(op.f("ix_review_user_id"), "review", ["user_id"], unique=False)
    op.create_index(
        "uq_review_app_user_product",
        "review",
        ["product_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("user_id IS NOT NULL AND source = 'app'"),
    )
    op.create_index(
        "uq_review_external_source_id",
        "review",
        ["product_id", "source", "external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )
    op.create_index(
        "ix_review_product_created_at_id",
        "review",
        ["product_id", sa.literal_column("created_at DESC"), sa.literal_column("id DESC")],
        unique=False,
    )
    op.create_index(
        "ix_review_user_created_at_id",
        "review",
        ["user_id", sa.literal_column("created_at DESC"), sa.literal_column("id DESC")],
        unique=False,
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )

    op.create_table(
        "review_source_cache",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column(
            "source",
            sa.Enum("app", "reddit", name="reviewsource", native_enum=False, length=32),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "fresh", "stale", "failed", name="reviewcachestatus", native_enum=False, length=32
            ),
            server_default="fresh",
            nullable=False,
        ),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "source IN ('app', 'reddit')", name=op.f("ck_review_source_cache_source")
        ),
        sa.CheckConstraint(
            "status IN ('fresh', 'stale', 'failed')", name=op.f("ck_review_source_cache_status")
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["product.id"],
            name=op.f("fk_review_source_cache_product_id_product"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_review_source_cache")),
        sa.UniqueConstraint("product_id", "source", name="uq_review_source_cache_product_source"),
    )
    op.create_index(
        op.f("ix_review_source_cache_product_id"),
        "review_source_cache",
        ["product_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_review_source_cache_product_id"), table_name="review_source_cache")
    op.drop_table("review_source_cache")

    op.drop_index(
        "ix_review_user_created_at_id",
        table_name="review",
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )
    op.drop_index("ix_review_product_created_at_id", table_name="review")
    op.drop_index(
        "uq_review_external_source_id",
        table_name="review",
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )
    op.drop_index(
        "uq_review_app_user_product",
        table_name="review",
        postgresql_where=sa.text("user_id IS NOT NULL AND source = 'app'"),
    )
    op.drop_index(op.f("ix_review_user_id"), table_name="review")
    op.drop_index(op.f("ix_review_product_id"), table_name="review")
    op.drop_table("review")

    op.drop_index(
        "ix_product_avg_rating_id",
        table_name="product",
        postgresql_where=sa.text("avg_rating IS NOT NULL"),
    )
    op.drop_constraint("review_count_non_negative", "product", type_="check")
    op.drop_constraint("avg_rating_range", "product", type_="check")
    op.drop_column("product", "review_count")
    op.drop_column("product", "avg_rating")
