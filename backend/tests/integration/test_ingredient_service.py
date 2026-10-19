import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import RiskLevel
from app.modules.ingredients import IngredientService, MatchType
from tests.factories import make_ingredient

pytestmark = pytest.mark.usefixtures("migrated_database")


@pytest.fixture
async def service(db_session: AsyncSession) -> IngredientService:
    return IngredientService(db_session)


# --------------------------------------------------------------------------- match()
async def test_exact_match_ignores_case_accents_and_punctuation(
    db_session: AsyncSession, service: IngredientService
) -> None:
    glycerin = make_ingredient(inci_name="GLYCERIN", aliases=["Glycérine", "E422"])
    db_session.add(glycerin)
    await db_session.flush()

    results = await service.match(["Glycerin", "GLYCÉRINE", "glycerine.", "E422", "e422"])

    assert [m.ingredient_id for m in results] == [glycerin.id] * 5
    assert {m.match_type for m in results} == {MatchType.EXACT}


async def test_spacing_variants_of_a_code_need_their_own_alias(
    db_session: AsyncSession, service: IngredientService
) -> None:
    """Known limitation (documented in ADR-0009): "E422" and "E 422" are different keys
    ("e422" vs "e 422"). Curators add both spellings as aliases."""
    glycerin = make_ingredient(inci_name="GLYCERIN", aliases=["E422"])
    db_session.add(glycerin)
    await db_session.flush()

    [compact, spaced] = await service.match(["E422", "E 422"])

    assert compact.ingredient_id == glycerin.id
    assert spaced.ingredient_id is None


async def test_one_ingredient_is_found_under_different_names(
    db_session: AsyncSession, service: IngredientService
) -> None:
    """Story 7: 'Aqua', 'Water' and 'Eau' on three labels are the same ingredient."""
    aqua = make_ingredient(inci_name="AQUA", aliases=["Water", "Eau"])
    db_session.add(aqua)
    await db_session.flush()

    results = await service.match(["Aqua", "Water", "Eau"])

    assert {m.ingredient_id for m in results} == {aqua.id}


async def test_results_keep_input_order_and_length(
    db_session: AsyncSession, service: IngredientService
) -> None:
    aqua = make_ingredient(inci_name="AQUA")
    glycerin = make_ingredient(inci_name="GLYCERIN")
    db_session.add_all([aqua, glycerin])
    await db_session.flush()

    results = await service.match(["Glycerin", "Mystery Extract", "Aqua", "Glycerin"])

    assert [m.raw_text for m in results] == ["Glycerin", "Mystery Extract", "Aqua", "Glycerin"]
    assert [m.ingredient_id for m in results] == [glycerin.id, None, aqua.id, glycerin.id]


async def test_unknown_names_are_not_guessed(
    db_session: AsyncSession, service: IngredientService
) -> None:
    db_session.add(make_ingredient(inci_name="SODIUM LAURYL SULFATE"))
    await db_session.flush()

    # 72% similar to a known name, but a different chemical: must NOT match (ADR-0009).
    [result] = await service.match(["Sodium Laureth Sulfate"])

    assert result.match_type is MatchType.NONE
    assert result.ingredient_id is None


async def test_bracketed_translation_matches_through_its_components(
    db_session: AsyncSession, service: IngredientService
) -> None:
    aqua = make_ingredient(inci_name="AQUA", aliases=["Water"])
    db_session.add(aqua)
    await db_session.flush()

    [with_brackets, with_slash] = await service.match(["Aqua (Eau)", "Aqua/Water/Eau"])

    # "Aqua (Eau)" is not itself a known name, but its known part ("aqua") is unambiguous.
    assert (with_brackets.match_type, with_brackets.ingredient_id) == (MatchType.COMPONENT, aqua.id)
    assert (with_slash.match_type, with_slash.ingredient_id) == (MatchType.COMPONENT, aqua.id)


async def test_a_known_whole_item_wins_over_its_components(
    db_session: AsyncSession, service: IngredientService
) -> None:
    fragrance = make_ingredient(inci_name="PARFUM", aliases=["Parfum (Fragrance)"])
    db_session.add(fragrance)
    await db_session.flush()

    [result] = await service.match(["Parfum (Fragrance)"])

    assert result.match_type is MatchType.EXACT


async def test_parts_pointing_to_different_ingredients_are_ambiguous(
    db_session: AsyncSession, service: IngredientService
) -> None:
    retinol = make_ingredient(inci_name="RETINOL")
    palmitate = make_ingredient(inci_name="RETINYL PALMITATE")
    db_session.add_all([retinol, palmitate])
    await db_session.flush()

    [result] = await service.match(["Retinol (Retinyl Palmitate)"])

    assert result.match_type is MatchType.NONE  # two different ingredients: a human must decide
    assert result.ingredient_id is None


async def test_unknown_extra_words_in_brackets_do_not_prevent_a_match(
    db_session: AsyncSession, service: IngredientService
) -> None:
    citric = make_ingredient(inci_name="CITRIC ACID")
    db_session.add(citric)
    await db_session.flush()

    [result] = await service.match(["Citric Acid (pH adjuster)"])

    assert (result.match_type, result.ingredient_id) == (MatchType.COMPONENT, citric.id)


async def test_blank_items_and_empty_input(service: IngredientService) -> None:
    assert await service.match([]) == []
    [blank, punctuation] = await service.match(["", " - "])
    assert blank.match_type is MatchType.NONE
    assert punctuation.match_type is MatchType.NONE


async def test_many_items_use_a_single_lookup(
    db_session: AsyncSession, service: IngredientService
) -> None:
    ingredients = [make_ingredient() for _ in range(40)]
    db_session.add_all(ingredients)
    await db_session.flush()

    results = await service.match([i.inci_name for i in ingredients])

    assert [m.ingredient_id for m in results] == [i.id for i in ingredients]


# ------------------------------------------------------------------------- get_many()
async def test_get_many_returns_details_with_localized_rationale(
    db_session: AsyncSession, service: IngredientService
) -> None:
    paraben = make_ingredient(
        inci_name="PROPYLPARABEN",
        risk_level=RiskLevel.HIGH,
        source_ref="EU 1223/2009 Annex V",
        rationale={"en": "Restricted preservative.", "fr": "Conservateur restreint."},
    )
    db_session.add(paraben)
    await db_session.flush()

    english = await service.get_many([paraben.id], "en")
    french = await service.get_many([paraben.id], "fr")

    assert english[paraben.id].rationale == "Restricted preservative."
    assert french[paraben.id].rationale == "Conservateur restreint."
    assert french[paraben.id].risk_level is RiskLevel.HIGH
    assert french[paraben.id].source_ref == "EU 1223/2009 Annex V"
    assert french[paraben.id].inci_name == "PROPYLPARABEN"


async def test_missing_translation_falls_back_to_english_then_to_none(
    db_session: AsyncSession, service: IngredientService
) -> None:
    english_only = make_ingredient(rationale={"en": "English only."})
    no_text = make_ingredient()
    db_session.add_all([english_only, no_text])
    await db_session.flush()

    infos = await service.get_many([english_only.id, no_text.id], "fr")

    assert infos[english_only.id].rationale == "English only."
    assert infos[no_text.id].rationale is None


async def test_get_many_ignores_unknown_ids_and_empty_input(service: IngredientService) -> None:
    assert await service.get_many([], "en") == {}
    assert await service.get_many([uuid.uuid4()], "en") == {}


# --------------------------------------------------------------------------- suggest()
async def test_suggest_finds_similar_names_best_first_one_per_ingredient(
    db_session: AsyncSession, service: IngredientService
) -> None:
    glycerin = make_ingredient(inci_name="GLYCERIN", aliases=["Glycerine", "Glycérol"])
    other = make_ingredient(inci_name="GLYCOL")
    db_session.add_all([glycerin, other])
    await db_session.flush()

    suggestions = await service.suggest("glycerinn", min_similarity=0.3)

    assert suggestions[0].ingredient_id == glycerin.id
    ids = [s.ingredient_id for s in suggestions]
    assert len(ids) == len(set(ids))  # glycerin appears once even though 3 of its names match
    assert all(0 < s.similarity <= 1 for s in suggestions)
    similarities = [s.similarity for s in suggestions]
    assert similarities == sorted(similarities, reverse=True)


async def test_suggest_respects_limit_and_threshold(
    db_session: AsyncSession, service: IngredientService
) -> None:
    db_session.add_all([make_ingredient(inci_name=f"SODIUM SOMETHING {i}") for i in range(8)])
    await db_session.flush()

    assert len(await service.suggest("sodium something", limit=3, min_similarity=0.3)) == 3
    assert await service.suggest("zzzzqqqq", min_similarity=0.4) == []
    assert await service.suggest("   ") == []


async def test_a_suggestion_is_not_a_match(
    db_session: AsyncSession, service: IngredientService
) -> None:
    """The service may SUGGEST a close name but must still refuse to MATCH it."""
    db_session.add(make_ingredient(inci_name="SODIUM LAURYL SULFATE"))
    await db_session.flush()

    suggestions = await service.suggest("Sodium Laureth Sulfate")
    [match] = await service.match(["Sodium Laureth Sulfate"])

    assert suggestions
    assert suggestions[0].inci_name == "SODIUM LAURYL SULFATE"
    assert match.match_type is MatchType.NONE
