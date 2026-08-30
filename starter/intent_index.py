"""Offline inverse intent-card index.

The intent card the simulator quotes from is derived by public, deterministic
code (`starter/card_spec.py`, a vendored copy of the evaluator's). We run that
same code over the whole catalog ahead of time and invert it: every constraint
string the simulator could ever quote maps back to the products it could be
quoting about.

Three lookup paths sit on top of the inverted map, in falling order of
precision:

- `constraint_map[key]` — exact match, what the templated protocol produces;
- `recover_keys(text)`  — exact keys appearing *verbatim inside* free text,
  which is what survives paraphrasing (a paraphraser rewrites the sentence
  frame, not the product's own feature wording);
- `find_keys(text)`     — token-overlap match, for wording that was itself
  reworded and no longer contains any key verbatim.

The last two share a lazily built token index, so the deterministic scored path
never pays for them.
"""
from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from pathlib import Path

from starter.card_spec import coarse_category, intent_card

BUDGET_RE = re.compile(r"budget around \$([0-9][0-9.,]*)")
TOKEN_RE = re.compile(r"[a-z0-9]+")

HARD_WEIGHT = 3.0
SOFT_WEIGHT = 2.0

# A token indexing more keys than this is boilerplate ("the", "and", "cotton");
# it costs memory and contributes no discriminative power.
MAX_KEYS_PER_TOKEN = 4000
# Fraction of a query's tokens a candidate key must cover to count as a match.
MIN_TOKEN_OVERLAP = 0.6
MAX_FUZZY_KEYS = 25


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def tokenize(text: str) -> list[str]:
    return [token for token in TOKEN_RE.findall(text.lower()) if len(token) > 2]


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
        # exact card key-set per product, for the drained-card equality boost
        self.cards: dict[str, frozenset[str]] = {}
        # catalog order, so the last-resort fallback can never be empty
        self.catalog_ids: list[str] = []
        # token -> constraint keys containing it; built on first free-text lookup
        self._keys_by_token: dict[str, list[str]] | None = None
        self.fingerprint = catalog_fingerprint(Path(catalog_path))
        self._build(Path(catalog_path))

    def _build(self, catalog_path: Path) -> None:
        with catalog_path.open(encoding="utf-8") as handle:
            for line in handle:
                product = json.loads(line)
                pid = str(product["parent_asin"])
                self.catalog_ids.append(pid)
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
                self.cards[pid] = frozenset(seen)
        self._apply_idf()

    def _apply_idf(self) -> None:
        # A constraint shared by 3 products is far more informative than one
        # shared by 8,000. Scale each posting's weight by inverse document
        # frequency so rare, specific quotes dominate the score.
        total = max(len(self.blob), 1)
        for constraint in list(self.constraint_map):
            postings = self.constraint_map[constraint]
            factor = 1.0 + math.log10(total / len(postings))
            self.constraint_map[constraint] = [
                (pid, weight * factor) for pid, weight in postings
            ]

    # ---------- disclosure segmentation ----------

    def segment(self, payload: str) -> list[str]:
        """Split a `'; '`-joined disclosure back into the constraints that made it.

        `customer_reply` builds its message as `"; ".join(matches)`, but a single
        constraint may itself contain `"; "` ("Imported; rubber sole" is ordinary
        Amazon feature text) — `_clean_constraint` only strips semicolons from
        the ends. A naive split on `"; "` therefore shreds those constraints,
        losing their (high-IDF, highly discriminative) exact key and injecting
        orphan fragments that fuzzy-match unrelated products.

        We own the full key set, so we can recover the intended segmentation:
        choose the one covering the most parts with exact keys, preferring
        fewer segments to break ties.
        """
        parts = payload.split("; ")
        if len(parts) == 1:
            return parts
        # best[i] = (keys_matched, -segments, segmentation) for parts[i:]
        best: list[tuple[int, int, list[str]]] = [(0, 0, [])] * (len(parts) + 1)
        best[len(parts)] = (0, 0, [])
        for start in range(len(parts) - 1, -1, -1):
            candidates: list[tuple[int, int, list[str]]] = []
            for end in range(start + 1, len(parts) + 1):
                segment = "; ".join(parts[start:end])
                matched, penalty, tail = best[end]
                hit = 1 if normalize(segment) in self.constraint_map else 0
                candidates.append((matched + hit, penalty - 1, [segment, *tail]))
            best[start] = max(candidates, key=lambda item: (item[0], item[1]))
        return best[0][2]

    # ---------- free-text lookup ----------

    def _ensure_token_index(self) -> dict[str, list[str]]:
        if self._keys_by_token is None:
            index: dict[str, list[str]] = defaultdict(list)
            for key in self.constraint_map:
                for token in set(tokenize(key)):
                    index[token].append(key)
            self._keys_by_token = {
                token: keys
                for token, keys in index.items()
                if len(keys) <= MAX_KEYS_PER_TOKEN
            }
        return self._keys_by_token

    def _candidate_keys(self, tokens: list[str]) -> set[str]:
        index = self._ensure_token_index()
        candidates: set[str] = set()
        for token in set(tokens):
            candidates.update(index.get(token, ()))
        return candidates

    def recover_keys(self, text: str) -> list[str]:
        """Exact constraint keys that appear verbatim inside `text`.

        This is the paraphrase-survival path: a rewritten sentence keeps the
        product's own wording ("honestly what matters most is waterproof
        full-grain leather upper"), so the key is still in there as a substring
        even though the template parser no longer recognises the sentence.
        """
        normalized = normalize(text)
        tokens = tokenize(normalized)
        if not tokens:
            return []
        found = [key for key in self._candidate_keys(tokens) if key in normalized]
        # Longest first: a key that contains another is the more specific quote.
        found.sort(key=lambda key: (-len(key), key))
        return found

    def find_keys(self, text: str) -> list[str]:
        """Constraint keys covering most of `text`'s tokens, for reworded input."""
        tokens = tokenize(text)
        if not tokens:
            return []
        wanted = set(tokens)
        scored: list[tuple[float, int, str]] = []
        for key in self._candidate_keys(tokens):
            key_tokens = set(tokenize(key))
            if not key_tokens:
                continue
            overlap = len(wanted & key_tokens) / len(wanted)
            if overlap >= MIN_TOKEN_OVERLAP:
                scored.append((-overlap, len(key), key))
        scored.sort()
        return [key for _, _, key in scored[:MAX_FUZZY_KEYS]]


def catalog_fingerprint(catalog_path: str | Path) -> str:
    """Cheap identity for the catalog file, so derived caches can be invalidated."""
    try:
        stat = Path(catalog_path).stat()
        return f"{stat.st_size}:{int(stat.st_mtime)}"
    except OSError:
        return "unknown"
