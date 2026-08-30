"""Vendored copy of the evaluator's public intent-card derivation.

`starter/` must be importable on its own: the submission bundle is
`agent.py` + local helper modules (docs/submission_rules.md), and the
organizer's harness is not guaranteed to expose `evaluator.local_evaluator`
on the import path. Importing the evaluator from the agent made
`Agent.__init__` raise `ModuleNotFoundError` in any such bundle — an
unrecoverable failure, since only `respond()` is wrapped in a fallback.

So the card-derivation code lives here instead. These functions are a
byte-for-byte copy of `evaluator/local_evaluator.py`; the evaluator itself is
never modified. `tests/test_card_spec_parity.py` asserts the two
implementations agree on every product of the real catalog (and on generated
edge cases when the catalog is absent), so organizer drift fails a test rather
than silently degrading retrieval.
"""
from __future__ import annotations

import re

ALLOWED_ATTRIBUTES = {
    "category", "material", "color", "size", "style", "brand",
    "budget", "feature", "use_case", "other",
}
MATERIALS = ("cotton", "polyester", "nylon", "leather", "wool", "spandex", "silk", "rayon", "fabric")
SEARCH_FIELDS = ("title", "features", "details", "description", "categories", "store")
MATERIAL_RE = re.compile(r"\b(cotton|polyester|nylon|leather|wool|spandex|silk|rayon|fabric)\b", re.I)
COLOR_RE = re.compile(r"\b(black|white|blue|red|pink|green|brown|gray|grey|purple|yellow|orange)\b", re.I)


def searchable_text(product: dict) -> str:
    parts: list[str] = []
    for field in SEARCH_FIELDS:
        value = product.get(field)
        if isinstance(value, dict):
            parts.extend(f"{key} {item}" for key, item in value.items())
        elif isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif value is not None:
            parts.append(str(value))
    return " ".join(parts).strip()


def _flatten_values(value: object) -> list[str]:
    if isinstance(value, dict):
        return [f"{key}: {item}" for key, item in value.items() if item not in (None, "", [])]
    if isinstance(value, list):
        return [str(item) for item in value if item not in (None, "")]
    return [str(value)] if value not in (None, "") else []


def _clean_constraint(value: str, limit: int) -> str:
    return re.sub(r"\s+", " ", value).strip(" -;,.\t\n")[:limit].rstrip()


def intent_card(product: dict, limit: int = 180) -> dict:
    title = _clean_constraint(str(product.get("title") or "product"), limit)
    candidates = [*_flatten_values(product.get("features")), *_flatten_values(product.get("details"))]
    corpus = searchable_text(product)
    material = MATERIAL_RE.search(corpus)
    color = COLOR_RE.search(corpus)
    if material:
        candidates.insert(0, material.group(1).lower())
    if color:
        candidates.insert(1, f"color: {color.group(1).lower()}")
    if product.get("price") not in (None, ""):
        candidates.append(f"budget around ${product['price']}")
    cleaned = list(dict.fromkeys(_clean_constraint(item, limit) for item in candidates if _clean_constraint(item, limit)))
    if not cleaned:
        cleaned = [title]
    return {
        "target_category": title,
        "hard_constraints": cleaned[:2],
        "soft_preferences": cleaned[2:4] or cleaned[:1],
    }


def coarse_category(values: list[str]) -> str:
    excluded = {"clothing", "clothing shoes & jewelry", "clothing, shoes & jewelry"}
    cleaned: list[str] = []
    for value in values:
        for part in value.split(","):
            part = part.strip()
            if part and part.lower() not in excluded:
                cleaned.append(part)
    return " ".join(cleaned[-2:]) if cleaned else "clothing item"


def classify_constraint(value: str) -> str:
    lowered = value.lower()
    if "budget" in lowered or re.search(r"(?:\$|<=|under)\s*\d", lowered):
        return "budget"
    if any(material in lowered for material in MATERIALS):
        return "material"
    if any(word in lowered for word in ("color", "black", "white", "blue", "red", "pink", "green")):
        return "color"
    if any(word in lowered for word in ("size", "sizing", "width", "wide", "narrow")):
        return "size"
    if any(word in lowered for word in ("department", "style", "fit", "sleeve", "neck")):
        return "style"
    if any(word in lowered for word in ("hiking", "running", "gym", "winter", "outdoor", "work")):
        return "use_case"
    return "feature"
