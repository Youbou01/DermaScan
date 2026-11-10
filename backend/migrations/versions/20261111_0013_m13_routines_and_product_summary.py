"""M13: routines, adherence logs, and localized product summaries.

Revision ID: 20261111_0013
Revises: 20261110_0012
Create Date: 2026-11-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261111_0013"
down_revision: str | Sequence[str] | None = "20261110_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "product", sa.Column("summary_i18n", postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )

    op.create_table(
        "routine",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("slot", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.CheckConstraint("slot IN ('morning', 'evening')", name=op.f("ck_routine_slot")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_account.id"],
            name=op.f("fk_routine_user_id_user_account"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_routine")),
        sa.UniqueConstraint("user_id", "slot", name=op.f("uq_routine_user_slot")),
    )
    op.create_index(op.f("ix_routine_user_id"), "routine", ["user_id"], unique=False)

    op.create_table(
        "routine_step",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("routine_id", sa.Uuid(), nullable=False),
        sa.Column("step_order", sa.SmallInteger(), nullable=False),
        sa.Column("step_type", sa.String(length=32), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint("step_order >= 1", name=op.f("ck_routine_step_step_order_positive")),
        sa.CheckConstraint(
            "step_type IN ('cleanser', 'toner', 'serum', 'moisturizer', 'sunscreen', 'treatment')",
            name=op.f("ck_routine_step_step_type"),
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["product.id"],
            name=op.f("fk_routine_step_product_id_product"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["routine_id"],
            ["routine.id"],
            name=op.f("fk_routine_step_routine_id_routine"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_routine_step")),
        sa.UniqueConstraint("routine_id", "step_order", name=op.f("uq_routine_step_order")),
    )
    op.create_index(
        op.f("ix_routine_step_product_id"), "routine_step", ["product_id"], unique=False
    )
    op.create_index(
        op.f("ix_routine_step_routine_id"), "routine_step", ["routine_id"], unique=False
    )

    op.create_table(
        "routine_completion_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("routine_id", sa.Uuid(), nullable=False),
        sa.Column("completed_date", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(
            ["routine_id"],
            ["routine.id"],
            name=op.f("fk_routine_completion_log_routine_id_routine"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_routine_completion_log")),
        sa.UniqueConstraint("routine_id", "completed_date", name=op.f("uq_routine_completion_day")),
    )
    op.create_index(
        op.f("ix_routine_completion_log_routine_id"),
        "routine_completion_log",
        ["routine_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_routine_completion_log_routine_id"), table_name="routine_completion_log")
    op.drop_table("routine_completion_log")
    op.drop_index(op.f("ix_routine_step_routine_id"), table_name="routine_step")
    op.drop_index(op.f("ix_routine_step_product_id"), table_name="routine_step")
    op.drop_table("routine_step")
    op.drop_index(op.f("ix_routine_user_id"), table_name="routine")
    op.drop_table("routine")
    op.drop_column("product", "summary_i18n")
