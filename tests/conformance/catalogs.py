"""Catalog builders for the conformance corpus.

Every builder controls what `intent_card` will derive, which is what makes the
assertions decisive rather than incidental. Two rules are followed throughout:

- **No accidental material or color words.** `intent_card` scans the whole
  searchable text and, if it finds one, *prepends* the material and inserts
  `color: <x>` at position 1 -- silently displacing the candidates we care
  about. `NEUTRAL_WORDS` is vetted against both regexes.
- **At most four candidates.** `hard_constraints` is `cleaned[:2]` and
  `soft_preferences` is `cleaned[2:4]`, so anything past the fourth candidate
  is invisible to the simulator and cannot be asserted on.
"""
from __future__ import annotations

import re

from evaluator.local_evaluator import COLOR_RE, MATERIAL_RE

# Deliberately free of every material and color token the evaluator matches.
NEUTRAL_WORDS = (
    "quartz", "meridian", "harbor", "lantern", "summit", "drift", "ember",
    "pivot", "canyon", "atlas", "vertex", "onyx", "cascade", "prairie",
    "juniper", "cobalt", "zenith", "tundra", "willow", "beacon",
)
CATEGORY_PAIRS = (
    ("Gear", "Daypacks"), ("Gear", "Duffels"), ("Outerwear", "Shells"),
    ("Footwear", "Trail Runners"), ("Accessories", "Straps"),
    ("Accessories", "Pouches"), ("Outerwear", "Vests"), ("Gear", "Slings"),
)


def assert_neutral(*texts: str) -> None:
    """Guard the invariant the whole corpus depends on."""
    blob = " ".join(texts)
    material = MATERIAL_RE.search(blob)
    color = COLOR_RE.search(blob)
    assert not material, f"material token {material.group(0)!r} leaked into {blob!r}"
    assert not color, f"color token {color.group(0)!r} leaked into {blob!r}"


def product(
    pid: str,
    *,
    features: list[str],
    detail: str | None = None,
    category: tuple[str, str] = ("Gear", "Daypacks"),
    price: float | None = 30.0,
    rating_number: int | None = 500,
    title: str | None = None,
) -> dict:
    """One catalog row whose intent card is exactly what you passed in.

    Candidate order is features, then details, then `budget around $price`,
    so `features[:2]` become the hard constraints when a detail and a price
    are present.
    """
    title = title or f"Item {pid}"
    row: dict = {
        "parent_asin": pid,
        "title": title,
        "categories": ["Clothing, Shoes & Jewelry", *category],
        "features": list(features),
        "details": {"Spec": detail} if detail else {},
        "description": [f"Listing for {title}."],
        "store": "Neutral Supply",
    }
    if price is not None:
        row["price"] = price
    if rating_number is not None:
        row["rating_number"] = rating_number
        row["average_rating"] = 4.2
    assert_neutral(title, *features, detail or "", " ".join(category))
    return row


def word(index: int) -> str:
    return NEUTRAL_WORDS[index % len(NEUTRAL_WORDS)]


def category(index: int) -> tuple[str, str]:
    return CATEGORY_PAIRS[index % len(CATEGORY_PAIRS)]


def separator_family(seed: int) -> tuple[list[dict], str]:
    """Target's discriminator contains the simulator's own join separator.

    Two decoys are keyed on the *fragments* of that constraint, so a naive
    split on `"; "` hands the target's only distinguishing evidence to them
    and leaves the target with nothing but the shared filler.
    """
    left, right = f"{word(seed)}{seed}", f"{word(seed + 7)}{seed}"
    shared_one, shared_two = f"shared trait {seed} one", f"shared trait {seed} two"
    cat = category(seed)
    products = [
        product("TARGET", features=[f"{left}; {right}", shared_one],
                detail=shared_two, category=cat, rating_number=400),
        product("DECOYL", features=[left, shared_one], detail=shared_two,
                category=cat, price=31.0, rating_number=4800),
        product("DECOYR", features=[right, shared_one], detail=shared_two,
                category=cat, price=32.0, rating_number=4900),
    ]
    for i in range(seed % 5 + 4):
        products.append(product(f"FILL{i:02d}", features=[f"filler {seed} {i}", shared_one],
                                detail=shared_two, category=cat,
                                price=40.0 + i, rating_number=3000 + i))
    return products, "TARGET"


def lookalike_family(size: int, target_at: int) -> tuple[list[dict], str]:
    """`size` products with byte-identical intent cards.

    Nothing the protocol can say separates them, so the only way to reach the
    target is to keep showing different candidates. The target is given the
    lowest rating in the pool, which puts it last in any popularity ordering.
    """
    products = []
    for i in range(size):
        is_target = i == target_at
        products.append(product(
            f"L{i:03d}",
            features=["identical trait one", "identical trait two"],
            detail="identical spec",
            price=25.0,
            rating_number=1 if is_target else 1000 + i,
        ))
    return products, f"L{target_at:03d}"


def boundary_family(seed: int) -> tuple[list[dict], str]:
    """A customer who answers every question with "no preference"."""
    cat = category(seed)
    products = [product("TARGET", features=[f"{word(seed)} panel {seed}", "common trait"],
                        detail="common spec", category=cat, rating_number=10)]
    for i in range(seed % 6 + 6):
        products.append(product(f"O{i:02d}", features=[f"other panel {seed} {i}", "common trait"],
                                detail="common spec", category=cat,
                                price=30.0 + i, rating_number=2000 + i))
    return products, "TARGET"


def wide_category_family(size: int, popular_at: int) -> tuple[list[dict], str]:
    """One category far larger than the rerank pool, with a single popular row.

    Every member ties on the category bonus alone, so the popularity prior is
    the only signal -- and it only gets a vote if it is applied before the
    candidate pool is truncated.
    """
    products = []
    for i in range(size):
        products.append(product(
            f"W{i:04d}",
            features=["uniform trait", "uniform trait two"],
            detail="uniform spec",
            price=20.0,
            rating_number=5000 if i == popular_at else 1,
        ))
    return products, f"W{popular_at:04d}"


def paraphrase_family(seed: int) -> tuple[list[dict], str]:
    """Distinctive verbatim wording, surrounded by same-category distractors."""
    phrase = f"{word(seed)} {word(seed + 3)} reinforced panel {seed}"
    cat = category(seed)
    products = [product("TARGET", features=[phrase, "generic trait"],
                        detail="generic spec", category=cat, rating_number=5)]
    for i in range(18):
        products.append(product(
            f"D{i:02d}",
            features=[f"{word(seed + i + 11)} plain panel {seed} {i}", "generic trait"],
            detail="generic spec", category=cat, price=30.0 + i, rating_number=4000 + i,
        ))
    return products, "TARGET"


def override_family(seed: int, contradictory: bool) -> tuple[list[dict], str]:
    """Intent-override catalogs.

    `contradictory=False` mirrors the official simulator, where the old and new
    values both come from the target's own card. `contradictory=True` is a
    genuine override: the abandoned preference belongs to a *different*
    product, so carrying it forward can only mislead.
    """
    cat = category(seed)
    keep = f"{word(seed)} required trait {seed}"
    drop = f"{word(seed + 5)} abandoned trait {seed}"
    products = [
        product("TARGET", features=[keep, "shared base"], detail="shared spec",
                category=cat, rating_number=20),
        product("OLDPICK", features=[drop, "shared base"], detail="shared spec",
                category=cat, price=55.0, rating_number=4500),
    ]
    for i in range(10):
        products.append(product(f"N{i:02d}", features=[f"neutral trait {seed} {i}", "shared base"],
                                detail="shared spec", category=cat,
                                price=33.0 + i, rating_number=2500 + i))
    if not contradictory:
        # Official shape: the abandoned value is the target's own soft
        # preference, so it stays true of the target.
        products[0] = product("TARGET", features=[keep, "shared base"],
                              detail=drop, category=cat, rating_number=20)
    return products, "TARGET"


def degenerate_catalog(kind: str, seed: int) -> tuple[list[dict], str]:
    """Catalogs that violate the shape the agent expects."""
    if kind == "no_ratings":
        rows = [product(f"R{i:02d}", features=[f"trait {seed} {i}"], rating_number=None)
                for i in range(12)]
        return rows, "R00"
    if kind == "no_prices":
        rows = [product(f"P{i:02d}", features=[f"trait {seed} {i}"], price=None)
                for i in range(12)]
        return rows, "P00"
    if kind == "single":
        return [product("ONLY", features=[f"lonely trait {seed}"])], "ONLY"
    if kind == "no_features":
        rows = [{"parent_asin": f"E{i:02d}", "title": f"Sparse Item {seed} {i}",
                 "categories": ["Clothing, Shoes & Jewelry", "Gear", "Slings"]}
                for i in range(12)]
        return rows, "E00"
    if kind == "empty_strings":
        rows = [{"parent_asin": f"S{i:02d}", "title": "", "features": ["", None],
                 "details": {"a": "", "b": None}, "categories": [], "price": "",
                 "description": []} for i in range(12)]
        return rows, "S00"
    if kind == "unicode":
        rows = [product(f"U{i:02d}", features=[f"trait {seed} {i}"],
                        title=f"Ünïcødé Ítem {i} — éèê 中文 \U0001f9f5")
                for i in range(12)]
        return rows, "U00"
    if kind == "long_text":
        filler = re.sub(r"\s+", " ", ("quartz meridian " * 200)).strip()
        rows = [product(f"G{i:02d}", features=[f"trait {seed} {i} {filler}"])
                for i in range(12)]
        return rows, "G00"
    if kind == "duplicate_ids":
        rows = [product("DUP", features=[f"trait {seed} {i}"], price=20.0 + i)
                for i in range(6)]
        rows += [product(f"Q{i:02d}", features=[f"other {seed} {i}"]) for i in range(6)]
        return rows, "Q00"
    raise ValueError(kind)
