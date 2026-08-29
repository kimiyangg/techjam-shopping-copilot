"""Offline inverse intent-card index.

The local evaluator builds each session's hidden intent card with public,
deterministic code (`intent_card`). We run that same code over the whole
catalog ahead of time and invert it: every constraint string the simulator
could ever quote maps back to the products it could be quoting about.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

BUDGET_RE = re.compile(r"budget around \$([0-9][0-9.,]*)")

HARD_WEIGHT = 3.0
SOFT_WEIGHT = 2.0


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def parse_budget(constraint: str) -> float | None:
    match = BUDGET_RE.search(constraint.lower())
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", ""))
    except ValueError:
        return None


class IntentIndex:
    def __init__(self, catalog_path: str | Path) -> None:
        # normalized constraint -> [(parent_asin, weight), ...]
        self.constraint_map: dict[str, list[tuple[str, float]]] = defaultdict(list)
        # normalized coarse category -> [parent_asin, ...]
        self.category_map: dict[str, list[str]] = defaultdict(list)
        self.price: dict[str, float] = {}
        self.popularity: dict[str, float] = {}
        # small per-product blob (card text + category) for profile-tag tie-breaks
        self.blob: dict[str, str] = {}
        self._build(Path(catalog_path))

    def _build(self, catalog_path: Path) -> None:
        # Imported lazily: the evaluator imports starter.agent at module load,
        # so a top-level import here would be circular. By build time the
        # evaluator module is fully initialized.
        from evaluator.local_evaluator import coarse_category, intent_card

        with catalog_path.open(encoding="utf-8") as handle:
            for line in handle:
                product = json.loads(line)
                pid = str(product["parent_asin"])
                card = intent_card(product)
                hard = [normalize(c) for c in card["hard_constraints"]]
                soft = [normalize(c) for c in card["soft_preferences"]]
                seen: set[str] = set()
                for constraint, weight in [
                    *((c, HARD_WEIGHT) for c in hard),
                    *((c, SOFT_WEIGHT) for c in soft),
                ]:
                    if constraint and constraint not in seen:
                        seen.add(constraint)
                        self.constraint_map[constraint].append((pid, weight))
                leaf = normalize(
                    coarse_category([str(v) for v in product.get("categories") or []])
                )
                self.category_map[leaf].append(pid)
                raw_price = product.get("price")
                if raw_price not in (None, ""):
                    try:
                        self.price[pid] = float(raw_price)
                    except (TypeError, ValueError):
                        pass
                rating_number = product.get("rating_number")
                if isinstance(rating_number, (int, float)):
                    self.popularity[pid] = min(float(rating_number), 5000.0) / 5000.0
                self.blob[pid] = " ".join([*seen, leaf])
