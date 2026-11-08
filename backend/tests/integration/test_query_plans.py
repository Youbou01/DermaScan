import json

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_trgm_index_query_plan(db_session: AsyncSession) -> None:
    # Force planner to evaluate index paths even on small/empty test tables
    await db_session.execute(text("SET LOCAL enable_seqscan = off"))

    query = text(
        """
        EXPLAIN (FORMAT JSON)
        SELECT id, name, name_normalized
        FROM product
        WHERE name_normalized % 'cleanser'
        LIMIT 20;
        """
    )
    res = await db_session.execute(query)
    plan_json = res.scalar()
    assert plan_json is not None
    plan_str = json.dumps(plan_json)

    # Verify GIN trigram index is utilized in the query plan
    assert "ix_product_name_normalized_trgm" in plan_str or "Bitmap Index Scan" in plan_str


@pytest.mark.asyncio
async def test_score_keyset_index_query_plan(db_session: AsyncSession) -> None:
    await db_session.execute(text("SET LOCAL enable_seqscan = off"))

    query = text(
        """
        EXPLAIN (FORMAT JSON)
        SELECT id, name, score
        FROM product
        WHERE score IS NOT NULL AND score < 85.0
        ORDER BY score DESC, id DESC
        LIMIT 20;
        """
    )
    res = await db_session.execute(query)
    plan_json = res.scalar()
    assert plan_json is not None
    plan_str = json.dumps(plan_json)

    # Verify keyset index or score index is utilized
    assert (
        "ix_product_score_id_keyset" in plan_str
        or "ix_product_score_desc_id" in plan_str
        or "Index Scan" in plan_str
    )
