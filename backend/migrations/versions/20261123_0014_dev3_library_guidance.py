"""Dev 3 personal library, curated guidance, and routine sharing.

Revision ID: 20261123_0014
Revises: 20261111_0013
Create Date: 2026-11-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261123_0014"
down_revision: str | Sequence[str] | None = "20261111_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DERMATOLOGIST_ID = "0194f024-6c67-7e21-9e16-a774b0d60001"
_AAD_DRY_SKIN_URL = (
    "https://www.aad.org/public/everyday-care/skin-care-basics/dry/"
    "dermatologists-tips-relieve-dry-skin"
)


def upgrade() -> None:
    op.create_table(
        "dermatologist",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("credentials", sa.String(length=80), nullable=False),
        sa.Column("specialty", sa.String(length=120), nullable=False),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("verification_source_url", sa.String(length=500), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dermatologist")),
    )
    op.create_table(
        "dermatologist_recommendation",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dermatologist_id", sa.Uuid(), nullable=True),
        sa.Column("skin_type", sa.String(length=32), nullable=True),
        sa.Column("title_en", sa.String(length=160), nullable=False),
        sa.Column("title_fr", sa.String(length=160), nullable=False),
        sa.Column("advice_en", sa.Text(), nullable=False),
        sa.Column("advice_fr", sa.Text(), nullable=False),
        sa.Column("source_title", sa.String(length=200), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.CheckConstraint(
            "skin_type IS NULL OR skin_type IN "
            "('normal', 'dry', 'oily', 'combination', 'sensitive')",
            name=op.f("ck_dermatologist_recommendation_skin_type_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["dermatologist_id"],
            ["dermatologist.id"],
            name=op.f("fk_dermatologist_recommendation_dermatologist_id_dermatologist"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dermatologist_recommendation")),
        sa.UniqueConstraint(
            "dermatologist_id",
            "skin_type",
            name=op.f("uq_dermatologist_recommendation_skin"),
        ),
    )
    op.create_index(
        "ix_dermatologist_recommendation_dermatologist_id",
        "dermatologist_recommendation",
        ["dermatologist_id"],
    )
    op.create_index(
        "ix_dermatologist_recommendation_skin_type",
        "dermatologist_recommendation",
        ["skin_type"],
    )
    op.create_index(
        "uq_dermatologist_recommendation_generic",
        "dermatologist_recommendation",
        ["dermatologist_id"],
        unique=True,
        postgresql_where=sa.text("skin_type IS NULL"),
    )
    op.create_table(
        "dermatologist_recommendation_product",
        sa.Column("recommendation_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.CheckConstraint(
            "position >= 1", name=op.f("ck_dermatologist_recommendation_product_position_positive")
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["product.id"],
            name=op.f("fk_dermatologist_recommendation_product_product_id_product"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["recommendation_id"],
            ["dermatologist_recommendation.id"],
            name=op.f(
                "fk_dermatologist_recommendation_product_recommendation_id_dermatologist_recommendation"
            ),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "recommendation_id", "product_id", name=op.f("pk_dermatologist_recommendation_product")
        ),
        sa.UniqueConstraint(
            "recommendation_id",
            "position",
            name=op.f("uq_recommendation_product_position"),
        ),
    )
    op.create_index(
        "ix_dermatologist_recommendation_product_product_id",
        "dermatologist_recommendation_product",
        ["product_id"],
    )
    op.create_table(
        "saved_product",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column(
            "saved_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["product.id"],
            name=op.f("fk_saved_product_product_id_product"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_account.id"],
            name=op.f("fk_saved_product_user_id_user_account"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "product_id", name=op.f("pk_saved_product")),
    )
    op.create_index(
        "ix_saved_product_user_saved_at_product",
        "saved_product",
        ["user_id", "saved_at", "product_id"],
    )
    op.create_table(
        "recently_viewed_product",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column(
            "viewed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["product.id"],
            name=op.f("fk_recently_viewed_product_product_id_product"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_account.id"],
            name=op.f("fk_recently_viewed_product_user_id_user_account"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "product_id", name=op.f("pk_recently_viewed_product")),
    )
    op.create_index(
        "ix_recently_viewed_user_viewed_at_product",
        "recently_viewed_product",
        ["user_id", "viewed_at", "product_id"],
    )
    op.create_table(
        "routine_share_link",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("routine_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("view_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "view_count >= 0", name=op.f("ck_routine_share_link_view_count_nonnegative")
        ),
        sa.ForeignKeyConstraint(
            ["routine_id"],
            ["routine.id"],
            name=op.f("fk_routine_share_link_routine_id_routine"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_routine_share_link")),
    )
    op.create_index("ix_routine_share_link_routine_id", "routine_share_link", ["routine_id"])
    op.create_index(
        "ix_routine_share_link_token_hash",
        "routine_share_link",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_routine_share_link_routine_created",
        "routine_share_link",
        ["routine_id", "created_at"],
    )
    _seed_demo_guidance()


def _seed_demo_guidance() -> None:
    op.bulk_insert(
        sa.table(
            "dermatologist",
            sa.column("id", postgresql.UUID(as_uuid=False)),
            sa.column("display_name", sa.String()),
            sa.column("credentials", sa.String()),
            sa.column("specialty", sa.String()),
            sa.column("is_verified", sa.Boolean()),
            sa.column("verification_source_url", sa.String()),
        ),
        [
            {
                "id": _DERMATOLOGIST_ID,
                "display_name": "Sandy Marchese Johnson",
                "credentials": "MD, FAAD",
                "specialty": "Dermatology",
                "is_verified": True,
                "verification_source_url": _AAD_DRY_SKIN_URL,
            }
        ],
    )

    content_table = sa.table(
        "dermatologist_recommendation",
        sa.column("id", postgresql.UUID(as_uuid=False)),
        sa.column("dermatologist_id", postgresql.UUID(as_uuid=False)),
        sa.column("skin_type", sa.String()),
        sa.column("title_en", sa.String()),
        sa.column("title_fr", sa.String()),
        sa.column("advice_en", sa.Text()),
        sa.column("advice_fr", sa.Text()),
        sa.column("source_title", sa.String()),
        sa.column("source_url", sa.String()),
    )
    common = {"dermatologist_id": None}
    op.bulk_insert(
        content_table,
        [
            {
                **common,
                "id": "0194f024-6c67-7e21-9e16-a774b0d60010",
                "skin_type": None,
                "title_en": "A simple daily routine",
                "title_fr": "Une routine quotidienne simple",
                "advice_en": (
                    "Use a gentle cleanser, apply any treatment, then moisturizer and/or "
                    "sunscreen. Adding many products at once may irritate skin."
                ),
                "advice_fr": (
                    "Utilisez un nettoyant doux, appliquez tout traitement, puis une crème "
                    "hydratante et/ou une protection solaire. Ajouter beaucoup de produits "
                    "à la fois peut irriter la peau."
                ),
                "source_title": "Should I apply my skin care products in a certain order?",
                "source_url": "https://www.aad.org/public/everyday-care/skin-care-basics/care/apply-skin-care-certain-order",
            },
            {
                **common,
                "id": "0194f024-6c67-7e21-9e16-a774b0d60011",
                "skin_type": "normal",
                "title_en": "Keep the routine simple",
                "title_fr": "Gardez une routine simple",
                "advice_en": (
                    "A gentle cleanser, moisturizer, and sunscreen can form a simple routine. "
                    "Introduce new ingredients gradually rather than all at once."
                ),
                "advice_fr": (
                    "Un nettoyant doux, une crème hydratante et une protection solaire peuvent "
                    "former une routine simple. Introduisez les nouveaux ingrédients "
                    "progressivement, pas tous à la fois."
                ),
                "source_title": "National Healthy Skin Month: six skin care tips",
                "source_url": "https://www.aad.org/public/public-health/awareness-campaigns/national-healthy-skin-month",
            },
            {
                **common,
                "id": "0194f024-6c67-7e21-9e16-a774b0d60012",
                "dermatologist_id": _DERMATOLOGIST_ID,
                "skin_type": "dry",
                "title_en": "Care for dry skin gently",
                "title_fr": "Prenez soin des peaux sèches en douceur",
                "advice_en": (
                    "Apply a fragrance-free cream or ointment while skin is still damp, and "
                    "choose a gentle cleanser. For sun protection, use broad-spectrum SPF 30 "
                    "or higher."
                ),
                "advice_fr": (
                    "Appliquez une crème ou une pommade sans parfum lorsque la peau est encore "
                    "humide et choisissez un nettoyant doux. Pour vous protéger du soleil, "
                    "utilisez une protection à large spectre SPF 30 ou plus."
                ),
                "source_title": "Dermatologists' top tips for relieving dry skin",
                "source_url": _AAD_DRY_SKIN_URL,
            },
            {
                **common,
                "id": "0194f024-6c67-7e21-9e16-a774b0d60013",
                "skin_type": "oily",
                "title_en": "Avoid over-cleansing oily skin",
                "title_fr": "Évitez de trop nettoyer les peaux grasses",
                "advice_en": (
                    "Choose a mild cleanser and avoid scrubbing. Oil-free, noncomedogenic "
                    "products may be a useful label to look for; moisturizer and sun protection "
                    "still matter."
                ),
                "advice_fr": (
                    "Choisissez un nettoyant doux et évitez de frotter. Les mentions « sans huile » "
                    "et « non comédogène » peuvent être utiles; l'hydratation et la protection "
                    "solaire restent importantes."
                ),
                "source_title": "How to control oily skin",
                "source_url": "https://www.aad.org/public/everyday-care/skin-care-basics/dry/oily-skin",
            },
            {
                **common,
                "id": "0194f024-6c67-7e21-9e16-a774b0d60014",
                "skin_type": "combination",
                "title_en": "Choose a gentle basic routine",
                "title_fr": "Choisissez une routine de base douce",
                "advice_en": (
                    "Keep the routine focused on cleansing, moisturizing, and sun protection. "
                    "New products can be introduced gradually so you can notice irritation."
                ),
                "advice_fr": (
                    "Concentrez la routine sur le nettoyage, l'hydratation et la protection solaire. "
                    "Introduisez progressivement les nouveaux produits afin de repérer toute irritation."
                ),
                "source_title": "Skin care on a budget",
                "source_url": "https://www.aad.org/public/everyday-care/skin-care-basics/care/skin-care-budget",
            },
            {
                **common,
                "id": "0194f024-6c67-7e21-9e16-a774b0d60015",
                "skin_type": "sensitive",
                "title_en": "Introduce products carefully",
                "title_fr": "Introduisez les produits avec prudence",
                "advice_en": (
                    "Test a new leave-on product on a small area twice daily for seven to ten days. "
                    "Stop using it if a reaction develops; ask a dermatologist about persistent "
                    "or severe symptoms."
                ),
                "advice_fr": (
                    "Testez un nouveau produit sans rinçage sur une petite zone deux fois par jour "
                    "pendant sept à dix jours. Arrêtez son utilisation en cas de réaction; consultez "
                    "un dermatologue si les symptômes persistent ou sont sévères."
                ),
                "source_title": "How to test skin care products",
                "source_url": "https://www.aad.org/public/everyday-care/skin-care-secrets/prevent-skin-problems/test-skin-care-products",
            },
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_routine_share_link_routine_created", table_name="routine_share_link")
    op.drop_index("ix_routine_share_link_token_hash", table_name="routine_share_link")
    op.drop_index("ix_routine_share_link_routine_id", table_name="routine_share_link")
    op.drop_table("routine_share_link")
    op.drop_index("ix_recently_viewed_user_viewed_at_product", table_name="recently_viewed_product")
    op.drop_table("recently_viewed_product")
    op.drop_index("ix_saved_product_user_saved_at_product", table_name="saved_product")
    op.drop_table("saved_product")
    op.drop_index(
        "ix_dermatologist_recommendation_product_product_id",
        table_name="dermatologist_recommendation_product",
    )
    op.drop_table("dermatologist_recommendation_product")
    op.drop_index(
        "uq_dermatologist_recommendation_generic",
        table_name="dermatologist_recommendation",
    )
    op.drop_index(
        "ix_dermatologist_recommendation_skin_type",
        table_name="dermatologist_recommendation",
    )
    op.drop_index(
        "ix_dermatologist_recommendation_dermatologist_id",
        table_name="dermatologist_recommendation",
    )
    op.drop_table("dermatologist_recommendation")
    op.drop_table("dermatologist")
