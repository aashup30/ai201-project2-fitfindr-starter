from tools import search_listings, suggest_outfit, create_fit_card, compare_price
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

# ── search_listings ───────────────────────────────────────────────────────────

def test_search_returns_results():
    # "vintage graphic tee" matches lst_006 and lst_033 by title and style_tags
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0

def test_search_empty_results():
    # Nothing in the dataset is a ballgown, XXS, or under $5
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []

def test_search_price_filter():
    # "vintage" matches many items — all returned results must be under $20
    results = search_listings("vintage", size=None, max_price=20)
    assert len(results) > 0
    assert all(item["price"] <= 20 for item in results)

# ── suggest_outfit ────────────────────────────────────────────────────────────

def test_suggest_outfit_empty_wardrobe():
    item = search_listings("vintage graphic tee", size=None, max_price=50)[0]
    result = suggest_outfit(item, get_empty_wardrobe())
    assert isinstance(result, str)
    assert len(result) > 0

def test_suggest_outfit_with_wardrobe():
    item = search_listings("vintage graphic tee", size=None, max_price=50)[0]
    result = suggest_outfit(item, get_example_wardrobe())
    assert isinstance(result, str)
    assert len(result) > 0

# ── create_fit_card ───────────────────────────────────────────────────────────

def test_create_fit_card_empty_outfit():
    item = search_listings("vintage graphic tee", size=None, max_price=50)[0]
    result = create_fit_card("", item)
    assert isinstance(result, str)
    assert len(result) > 0

def test_create_fit_card_returns_caption():
    item = search_listings("vintage graphic tee", size=None, max_price=50)[0]
    outfit = suggest_outfit(item, get_example_wardrobe())
    result = create_fit_card(outfit, item)
    assert isinstance(result, str)
    assert len(result) > 0

# ── compare_price ─────────────────────────────────────────────────────────────

def test_compare_price_returns_verdict():
    # "vintage" tops are common in the dataset — should have enough comparables
    item = search_listings("vintage crewneck", size=None, max_price=100)[0]
    result = compare_price(item)
    assert isinstance(result, dict)
    assert "verdict" in result
    assert "avg_comparable_price" in result

def test_compare_price_not_enough_comparables():
    item = search_listings("vintage graphic tee", size=None, max_price=50)[0]
    item_copy = dict(item, category="nonexistent_category", style_tags=["zzz"])
    result = compare_price(item_copy)
    assert result["verdict"] is None
    assert "Not enough" in result["reasoning"]