"""M12: identity, health profile and blacklist

Revision ID: 20261110_0012
Revises: 20261020_0011
Create Date: 2026-11-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261110_0012"
down_revision: str | Sequence[str] | None = "20261020_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_account",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_account")),
    )
    op.create_index(
        "uq_user_account_email_lower",
        "user_account",
        [sa.literal_column("lower(email)")],
        unique=True,
    )

    op.create_table(
        "user_profile",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("skin_type", sa.String(length=32), nullable=True),
        sa.Column(
            "is_pregnant_or_nursing", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "health_conditions",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_account.id"],
            name=op.f("fk_user_profile_user_id_user_account"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_user_profile")),
    )
    op.execute(
        "ALTER TABLE user_profile ADD CONSTRAINT ck_user_profile_skin_type "
        "CHECK (skin_type IN ('normal', 'dry', 'oily', 'combination', 'sensitive'))"
    )

    op.create_table(
        "user_allergy",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("ingredient_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_account.id"],
            name=op.f("fk_user_allergy_user_id_user_account"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["ingredient_id"],
            ["ingredient.id"],
            name=op.f("fk_user_allergy_ingredient_id_ingredient"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("user_id", "ingredient_id", name=op.f("pk_user_allergy")),
    )

    op.create_table(
        "user_blacklist_product",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_account.id"],
            name=op.f("fk_user_blacklist_product_user_id_user_account"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["product.id"],
            name=op.f("fk_user_blacklist_product_product_id_product"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("user_id", "product_id", name=op.f("pk_user_blacklist_product")),
    )

    op.create_table(
        "user_blacklist_ingredient",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("ingredient_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_account.id"],
            name=op.f("fk_user_blacklist_ingredient_user_id_user_account"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["ingredient_id"],
            ["ingredient.id"],
            name=op.f("fk_user_blacklist_ingredient_ingredient_id_ingredient"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "user_id", "ingredient_id", name=op.f("pk_user_blacklist_ingredient")
        ),
    )


def downgrade() -> None:
    op.drop_table("user_blacklist_ingredient")
    op.drop_table("user_blacklist_product")
    op.drop_table("user_allergy")
    op.execute("ALTER TABLE user_profile DROP CONSTRAINT IF EXISTS ck_user_profile_skin_type")
    op.drop_table("user_profile")
    op.drop_index("uq_user_account_email_lower", table_name="user_account")
    op.drop_table("user_account")
