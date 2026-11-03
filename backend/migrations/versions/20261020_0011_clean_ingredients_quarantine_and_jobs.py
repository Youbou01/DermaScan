"""M11: safe ingredient case-dedup, baseline translations, >120 char purge,
enrichment_status in_progress, quarantine dedup, and singleton job partial index.

Revision ID: 20261020_0011
Revises: 20261020_0010
Create Date: 2026-11-03 22:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261020_0011"
down_revision: str | Sequence[str] | None = "20261020_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Build temp map of (loser_id, winner_id) for case-duplicate ingredients
    op.execute(
        """
        CREATE TEMP TABLE _ing_dedup_map ON COMMIT DROP AS
        WITH ranked AS (
            SELECT
                i.id,
                lower(trim(i.inci_name)) AS norm_key,
                ROW_NUMBER() OVER (
                    PARTITION BY lower(trim(i.inci_name))
                    ORDER BY
                        CASE i.rating_source
                            WHEN 'curated' THEN 1
                            WHEN 'regulatory' THEN 2
                            WHEN 'ai' THEN 3
                            ELSE 4
                        END ASC,
                        (SELECT count(*) FROM product_ingredient pi WHERE pi.ingredient_id = i.id) DESC,
                        (SELECT count(*) FROM ingredient_alias ia WHERE ia.ingredient_id = i.id) DESC,
                        i.id ASC
                ) AS rn
            FROM ingredient i
        )
        SELECT r_lose.id AS loser_id, r_win.id AS winner_id
        FROM ranked r_lose
        JOIN ranked r_win ON r_lose.norm_key = r_win.norm_key AND r_win.rn = 1
        WHERE r_lose.rn > 1;
        """
    )

    # 2. Merge metadata from loser onto winner where winner is missing it
    op.execute(
        """
        UPDATE ingredient AS w
        SET
            cosing_id = COALESCE(w.cosing_id, l_ing.cosing_id),
            cas = COALESCE(w.cas, l_ing.cas),
            taxonomy_id = COALESCE(w.taxonomy_id, l_ing.taxonomy_id),
            functions = COALESCE(w.functions, l_ing.functions),
            is_prohibited = w.is_prohibited OR l_ing.is_prohibited,
            is_restricted = w.is_restricted OR l_ing.is_restricted,
            is_allergen = w.is_allergen OR l_ing.is_allergen
        FROM _ing_dedup_map m
        JOIN ingredient l_ing ON l_ing.id = m.loser_id
        WHERE w.id = m.winner_id;
        """
    )

    # 3. Copy translations from loser onto winner before backfilling defaults
    op.execute(
        """
        INSERT INTO ingredient_translation (ingredient_id, locale, rationale, summary, concern_note)
        SELECT
            m.winner_id,
            t.locale,
            COALESCE(t.rationale, t.concern_note, t.summary, 'Standard cosmetic ingredient.'),
            t.summary,
            t.concern_note
        FROM ingredient_translation t
        JOIN _ing_dedup_map m ON t.ingredient_id = m.loser_id
        ON CONFLICT (ingredient_id, locale) DO UPDATE
        SET
            rationale = COALESCE(ingredient_translation.rationale, EXCLUDED.rationale),
            summary = COALESCE(ingredient_translation.summary, EXCLUDED.summary),
            concern_note = COALESCE(ingredient_translation.concern_note, EXCLUDED.concern_note);
        """
    )

    # 4. Re-point product_ingredient and ingredient_alias to winner_id, mark products dirty, delete losers
    op.execute(
        """
        UPDATE product
        SET score_dirty = true
        WHERE id IN (
            SELECT DISTINCT pi.product_id
            FROM product_ingredient pi
            JOIN _ing_dedup_map m ON pi.ingredient_id IN (m.loser_id, m.winner_id)
        );
        """
    )
    op.execute(
        """
        UPDATE product_ingredient pi
        SET ingredient_id = m.winner_id
        FROM _ing_dedup_map m
        WHERE pi.ingredient_id = m.loser_id;
        """
    )
    op.execute(
        """
        UPDATE ingredient_alias ia
        SET ingredient_id = m.winner_id
        FROM _ing_dedup_map m
        WHERE ia.ingredient_id = m.loser_id;
        """
    )
    op.execute("DELETE FROM ingredient WHERE id IN (SELECT loser_id FROM _ing_dedup_map);")

    # 5. Normalize inci_name to UPPERCASE and replace case-sensitive constraint with lower(inci_name) unique index
    op.execute("UPDATE ingredient SET inci_name = upper(trim(inci_name));")
    op.drop_constraint("uq_ingredient_inci_name", "ingredient", type_="unique")
    op.create_index(
        "uq_ingredient_inci_name_lower",
        "ingredient",
        [sa.literal_column("lower(inci_name)")],
        unique=True,
    )

    # 6. Backfill baseline EN/FR translations for any ingredient still missing translations
    op.execute(
        """
        INSERT INTO ingredient_translation (ingredient_id, locale, summary, concern_note, rationale)
        SELECT
            i.id,
            'en',
            CASE
                WHEN i.functions IS NOT NULL AND array_length(i.functions, 1) > 0
                THEN 'Cosmetic ingredient functioning as ' || array_to_string(i.functions, ', ') || '.'
                ELSE 'Standard cosmetic formulation ingredient (' || i.inci_name || ').'
            END,
            CASE
                WHEN i.is_prohibited THEN 'Prohibited substance under EU Cosmetic Regulation Annex II.'
                WHEN i.is_restricted THEN 'Restricted substance subject to concentration limits under EU Annex III.'
                WHEN i.is_allergen THEN 'Recognized fragrance allergen requiring label declaration.'
                ELSE 'Generally well-tolerated cosmetic ingredient at standard formulation levels.'
            END,
            CASE
                WHEN i.is_prohibited THEN 'Prohibited substance under EU Cosmetic Regulation Annex II.'
                WHEN i.is_restricted THEN 'Restricted substance subject to concentration limits under EU Annex III.'
                WHEN i.is_allergen THEN 'Recognized fragrance allergen requiring label declaration.'
                WHEN i.functions IS NOT NULL AND array_length(i.functions, 1) > 0
                THEN 'Cosmetic ingredient functioning as ' || array_to_string(i.functions, ', ') || '.'
                ELSE 'Standard cosmetic formulation ingredient (' || i.inci_name || ').'
            END
        FROM ingredient i
        ON CONFLICT (ingredient_id, locale) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO ingredient_translation (ingredient_id, locale, summary, concern_note, rationale)
        SELECT
            i.id,
            'fr',
            CASE
                WHEN i.functions IS NOT NULL AND array_length(i.functions, 1) > 0
                THEN 'Ingrédient cosmétique ayant pour fonction : ' || array_to_string(i.functions, ', ') || '.'
                ELSE 'Ingrédient de formulation cosmétique (' || i.inci_name || ').'
            END,
            CASE
                WHEN i.is_prohibited THEN 'Substance interdite selon l''Annexe II du règlement cosmétique européen.'
                WHEN i.is_restricted THEN 'Substance soumise à des restrictions selon l''Annexe III européenne.'
                WHEN i.is_allergen THEN 'Allergène parfumant soumis à déclaration obligatoire.'
                ELSE 'Ingrédient cosmétique généralement bien toléré aux concentrations usuelles.'
            END,
            CASE
                WHEN i.is_prohibited THEN 'Substance interdite selon l''Annexe II du règlement cosmétique européen.'
                WHEN i.is_restricted THEN 'Substance soumise à des restrictions selon l''Annexe III européenne.'
                WHEN i.is_allergen THEN 'Allergène parfumant soumis à déclaration obligatoire.'
                WHEN i.functions IS NOT NULL AND array_length(i.functions, 1) > 0
                THEN 'Ingrédient cosmétique ayant pour fonction : ' || array_to_string(i.functions, ', ') || '.'
                ELSE 'Ingrédient de formulation cosmétique (' || i.inci_name || ').'
            END
        FROM ingredient i
        ON CONFLICT (ingredient_id, locale) DO NOTHING;
        """
    )

    # 7. Update ck_product_enrichment_status to include 'in_progress'
    op.execute("ALTER TABLE product DROP CONSTRAINT IF EXISTS ck_product_enrichment_status;")
    op.execute(
        "ALTER TABLE product ADD CONSTRAINT ck_product_enrichment_status "
        "CHECK (enrichment_status IN ('pending', 'in_progress', 'done', 'quarantined', 'failed'));"
    )

    # 8. Flag products with >120 char ingredient blobs for re-enrichment and delete the >120 char blobs
    op.execute(
        """
        UPDATE product
        SET enrichment_status = 'pending', score_dirty = true
        WHERE id IN (
            SELECT DISTINCT product_id FROM product_ingredient WHERE length(raw_text) > 120
        );
        """
    )
    op.execute("DELETE FROM product_ingredient WHERE length(raw_text) > 120;")

    # 9. Mark products with scoring_version < 4 or unknown band as score_dirty
    op.execute(
        """
        UPDATE product
        SET score_dirty = true
        WHERE scoring_version IS NULL OR scoring_version < 4 OR score_band = 'unknown' OR score IS NULL;
        """
    )

    # 10. Deduplicate pending quarantine_item rows and create partial unique index
    op.execute(
        """
        DELETE FROM quarantine_item q1
        USING quarantine_item q2
        WHERE q1.raw_product_id IS NOT NULL
          AND q1.raw_product_id = q2.raw_product_id
          AND q1.stage = q2.stage
          AND q1.status = 'pending'
          AND q2.status = 'pending'
          AND q1.id < q2.id;
        """
    )
    op.create_index(
        "uq_quarantine_pending_raw_stage",
        "quarantine_item",
        ["raw_product_id", "stage"],
        unique=True,
        postgresql_where=sa.text("raw_product_id IS NOT NULL AND status = 'pending'"),
    )

    # 11. Deduplicate pending singleton jobs and create partial unique index
    op.execute(
        """
        DELETE FROM job j1
        USING job j2
        WHERE j1.task_name = j2.task_name
          AND j1.status = 'pending'
          AND j2.status = 'pending'
          AND j1.task_name IN ('recompute_dirty_scores', 'backfill_pending_products', 'rate_ingredients')
          AND j1.id < j2.id;
        """
    )
    op.create_index(
        "uq_job_pending_singleton_tasks",
        "job",
        ["task_name"],
        unique=True,
        postgresql_where=sa.text(
            "status = 'pending' AND task_name IN ('recompute_dirty_scores', 'backfill_pending_products', 'rate_ingredients')"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_job_pending_singleton_tasks",
        table_name="job",
        postgresql_where=sa.text(
            "status = 'pending' AND task_name IN ('recompute_dirty_scores', 'backfill_pending_products', 'rate_ingredients')"
        ),
    )
    op.drop_index(
        "uq_quarantine_pending_raw_stage",
        table_name="quarantine_item",
        postgresql_where=sa.text("raw_product_id IS NOT NULL AND status = 'pending'"),
    )
    op.execute(
        "UPDATE product SET enrichment_status = 'pending' WHERE enrichment_status = 'in_progress';"
    )
    op.execute("ALTER TABLE product DROP CONSTRAINT IF EXISTS ck_product_enrichment_status;")
    op.execute(
        "ALTER TABLE product ADD CONSTRAINT ck_product_enrichment_status "
        "CHECK (enrichment_status IN ('pending', 'done', 'quarantined', 'failed'));"
    )
    op.drop_index("uq_ingredient_inci_name_lower", table_name="ingredient")
    op.create_unique_constraint("uq_ingredient_inci_name", "ingredient", ["inci_name"])
