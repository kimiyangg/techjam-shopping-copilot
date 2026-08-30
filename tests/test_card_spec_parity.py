"""`starter/card_spec.py` must stay byte-identical in behaviour to the evaluator.

The agent inverts the evaluator's intent-card derivation. It keeps its own copy
so that `starter/` imports nothing from `evaluator/` (see
tests/test_submission_bundle.py), which means the two can silently drift apart
— and a drift would degrade retrieval with no error anywhere. These tests are
the tripwire: if the organizer changes `local_evaluator.intent_card`, this
fails instead of the score.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from evaluator import local_evaluator as official
from starter import card_spec as vendored

CATALOG = Path("data/catalog.jsonl")


def _generated_products() -> list[dict]:
    """Products exercising every branch of intent_card / coarse_category."""
    rng = random.Random(0)
    materials = ["cotton", "leather", "silk", "wool", None]
    colors = ["black", "blue", "brown", None]
    products: list[dict] = [
        # no features, no details, no price -> title fallback
        {"parent_asin": "EMPTY", "title": "Bare Product"},
        # nothing at all -> "product"
        {"parent_asin": "NOTHING"},
        # details as a dict, features as a list
        {"parent_asin": "DICT", "title": "Boot", "features": ["Imported; rubber sole"],
         "details": {"Closure type": "Lace-up", "Department": "Womens"}, "price": 75.99},
        # a single cleaned candidate -> soft_preferences falls back to cleaned[:1]
        {"parent_asin": "ONE", "title": "Tee", "features": ["100% cotton"], "details": {}},
        # values needing whitespace/punctuation cleaning and length truncation
        {"parent_asin": "MESSY", "title": "  Spaced   Out  ",
         "features": ["  ; leading and trailing ;  ", "x" * 400], "details": {},
         "price": "", "categories": []},
        # empty/None members that _flatten_values must drop
        {"parent_asin": "HOLES", "title": "Holey", "features": ["ok", "", None],
         "details": {"a": "", "b": None, "c": []}, "price": 0},
        # categories exercising the excluded-token filter
        {"parent_asin": "CATS", "title": "Scarf",
         "categories": ["Clothing, Shoes & Jewelry", "Women, Accessories", "Scarves"]},
        {"parent_asin": "CATS2", "title": "Thing", "categories": ["clothing"]},
        {"parent_asin": "CATS3", "title": "Thing", "categories": []},
    ]
    for i in range(200):
        material = rng.choice(materials)
        color = rng.choice(colors)
        features = [f"Feature {i} {material or ''}".strip()]
        if rng.random() < 0.4:
            features.append(f"Imported; part {i}")
        if color:
            features.append(f"Comes in {color}")
        products.append({
            "parent_asin": f"GEN{i}",
            "title": f"Product {i}",
            "features": features,
            "details": {"Department": rng.choice(["mens", "womens"]), "Fit": f"fit{i}"},
            "description": [f"desc {i}"],
            "categories": ["Clothing, Shoes & Jewelry", f"Cat{i % 7}", f"Leaf{i % 3}"],
            "store": f"Store{i}",
            "price": rng.choice([None, "", 9.99, 120.0, 1299]),
            "rating_number": rng.randint(0, 9000),
        })
    return products


def _catalog_products(limit: int = 3000) -> list[dict]:
    with CATALOG.open(encoding="utf-8") as handle:
        return [json.loads(line) for _, line in zip(range(limit), handle)]


def _products() -> list[dict]:
    generated = _generated_products()
    if CATALOG.exists():
        return generated + _catalog_products()
    return generated


PRODUCTS = _products()


@pytest.mark.parametrize("product", PRODUCTS, ids=lambda p: str(p.get("parent_asin")))
def test_intent_card_matches_evaluator(product):
    assert vendored.intent_card(product) == official.intent_card(product)


@pytest.mark.parametrize("product", PRODUCTS, ids=lambda p: str(p.get("parent_asin")))
def test_coarse_category_matches_evaluator(product):
    values = [str(v) for v in product.get("categories") or []]
    assert vendored.coarse_category(values) == official.coarse_category(values)


def test_classify_constraint_matches_evaluator():
    samples = [
        "budget around $75.99", "under 40", "<= 20", "100% cotton", "leather upper",
        "color: black", "blue and white", "size 10", "wide width", "narrow toe",
        "department: womens", "slim fit", "long sleeve", "crew neck",
        "hiking boots", "running shoe", "gym wear", "winter coat", "outdoor use",
        "work boot", "imported; rubber sole", "", "no idea what this is",
    ]
    for sample in samples:
        assert vendored.classify_constraint(sample) == official.classify_constraint(sample)


def test_constants_match_evaluator():
    assert vendored.ALLOWED_ATTRIBUTES == official.ALLOWED_ATTRIBUTES
    assert vendored.MATERIALS == official.MATERIALS
    assert vendored.SEARCH_FIELDS == official.SEARCH_FIELDS
    assert vendored.MATERIAL_RE.pattern == official.MATERIAL_RE.pattern
    assert vendored.COLOR_RE.pattern == official.COLOR_RE.pattern


@pytest.mark.skipif(not CATALOG.exists(), reason="catalog.jsonl not present")
def test_every_catalog_row_agrees():
    """Full-catalog parity — the check that actually matters before submitting."""
    with CATALOG.open(encoding="utf-8") as handle:
        for line in handle:
            product = json.loads(line)
            assert vendored.intent_card(product) == official.intent_card(product)
            values = [str(v) for v in product.get("categories") or []]
            assert vendored.coarse_category(values) == official.coarse_category(values)
