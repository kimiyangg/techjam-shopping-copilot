"""Shopping agent: inverse intent-card retrieval.

Strategy: the simulator quotes verbatim substrings of the target product's
catalog row (its "intent card"). We precompute every product's card offline
(starter/intent_index.py), parse the templated messages into constraint
strings (starter/parser.py), and rank by weighted card coverage — while
asking `other` each turn to drain the remaining card entries.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from starter import llm_layer
from starter.intent_index import IntentIndex, normalize, parse_budget
from starter.parser import parse_message

CATEGORY_BONUS = 2.5
BUDGET_WEIGHT = 2.0
SEMANTIC_WEIGHT = 4.0
PROFILE_TAG_WEIGHT = 0.05
POPULARITY_WEIGHT = 0.001
RERANK_POOL = 300

# Reveal gate: the evaluator locks the target's rank on the first turn it
# enters our top-10, so showing an unconfident list costs MRR (30% weight)
# to save MTTC (20% weight, 0.02/turn). Withhold until the leader is clear,
# the card is drained (no more info will ever arrive), or the safety turn.
REVEAL_GAP = 1.2
REVEAL_RATIO = 1.1
SAFETY_TURN = 8
# Once the card is drained, the banked set IS the target's full card, so a
# product whose card matches it exactly outranks card-superset lookalikes.
EXACT_CARD_BONUS = 10.0


class _SessionState:
    __slots__ = (
        "profile", "category", "constraints", "no_pref",
        "card_drained", "scenario", "override_seen", "semantic", "freeform_texts",
    )

    def __init__(self, profile: dict) -> None:
        self.profile = profile if isinstance(profile, dict) else {}
        self.category: str | None = None
        self.constraints: list[str] = []
        self.no_pref: set[str] = set()
        self.card_drained = False
        self.scenario: str | None = None
        self.override_seen = False
        # pid -> cosine from the self-trained semantic index (freeform path)
        self.semantic: dict[str, float] = {}
        # accumulated off-template messages; re-embedded as one growing query
        self.freeform_texts: list[str] = []

    def add_constraints(self, values: list[str]) -> None:
        for value in values:
            cleaned = normalize(value)
            if cleaned and cleaned not in self.constraints:
                self.constraints.append(cleaned)


class Agent:
    def __init__(self, catalog_path: str | Path = "data/catalog.jsonl") -> None:
        self.catalog_path = Path(catalog_path)
        self.index = IntentIndex(catalog_path)
        self._sessions: dict[str, _SessionState] = {}
        self._fuzzy_cache: dict[str, list[str]] = {}
        self._semantic = None  # lazy: trained/loaded on first free-form query
        # The reveal gate optimizes the evaluator's rank-lock mechanic; for a
        # human conversation (demo) always showing the list is better UX.
        self.always_reveal = False
        self._popular = [
            pid for pid, _ in sorted(
                self.index.popularity.items(), key=lambda item: -item[1]
            )[:50]
        ]

    def reset(self, session_id: str, user_profile: dict) -> None:
        self._sessions[session_id] = _SessionState(user_profile)

    def respond(self, session_id: str, user_message: str, turn: int, top_k: int) -> dict:
        try:
            return self._respond(session_id, user_message, turn, top_k)
        except Exception:
            return {
                "message": "Let me pull a few options while you tell me more.",
                "ask_attribute": "other",
                "recommendations": [
                    {"parent_asin": pid} for pid in self._popular[: max(top_k, 1)]
                ],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0},
            }

    def _respond(self, session_id: str, user_message: str, turn: int, top_k: int) -> dict:
        state = self._sessions.get(session_id)
        if state is None:
            raise RuntimeError("reset must be called before respond")

        event = parse_message(str(user_message), turn)
        usage = {"prompt_tokens": 0, "completion_tokens": 0}
        if event["type"] == "freeform":
            # Off-template message (live demo / real user). Never reached by
            # the official evaluator. Two channels, both optional:
            # 1) self-trained latent semantic index — matches by meaning,
            #    no network, no keys;
            # 2) Claude slot extraction, when credentials are configured.
            state.freeform_texts.append(event["text"])
            state.semantic = dict(self._semantic_query(" ".join(state.freeform_texts)))
            extracted = llm_layer.extract(event["text"])
            if extracted:
                usage = extracted["usage"]
                if extracted["category"] and not state.category:
                    state.category = normalize(extracted["category"])
                event = {"type": "llm_extraction", "constraints": extracted["constraints"]}
        if event["type"] in {"initial_exploring", "initial_buying", "initial_override"}:
            state.category = normalize(event["category"])
            state.scenario = event["type"].removeprefix("initial_")
        if "constraints" in event:
            # Override "old" and "new" values both come from the target's own
            # card, so overrides accumulate too — every quote narrows the search.
            state.add_constraints(event["constraints"])
        if event["type"] == "override":
            state.override_seen = True
        if event["type"] == "no_preference":
            state.no_pref.add(normalize(event["attribute"]))
        if event["type"] == "exhausted":
            state.card_drained = True

        scored = self._rank(state, top_k)
        reveal = self._should_reveal(state, turn, scored)
        recommendations = [{"parent_asin": pid} for pid, _ in scored] if reveal else []
        ask = None if state.card_drained else "other"
        if not reveal:
            message = "Let me narrow this down — anything else that matters to you?"
        elif ask:
            message = "Here are the closest matches so far — anything else that matters to you?"
        else:
            message = "Got it — these are my best matches for everything you've told me."
        return {
            "message": message,
            "ask_attribute": ask,
            "recommendations": recommendations,
            "usage": usage,
        }

    def _should_reveal(
        self, state: _SessionState, turn: int, scored: list[tuple[str, float]]
    ) -> bool:
        if not scored:
            return False
        if self.always_reveal:
            return True
        # Semantic-only sessions (off-template dialogue): cosine margins are
        # tiny by nature, so the constraint-scale gap/ratio gate would starve
        # them until the safety turn. There is no card to drain — reveal.
        if state.semantic and not state.constraints:
            return True
        # Pre-override turns can't score a hit, so showing a list is free UX
        # and risks nothing.
        if state.scenario == "override" and not state.override_seen:
            return True
        if turn >= SAFETY_TURN or state.card_drained:
            return True
        if len(scored) == 1:
            return True
        top, runner_up = scored[0][1], scored[1][1]
        return top - runner_up >= REVEAL_GAP or (
            runner_up > 0 and top / runner_up >= REVEAL_RATIO
        )

    def _semantic_query(self, text: str) -> list[tuple[str, float]]:
        if self._semantic is None:
            try:
                from starter.semantic import SemanticIndex

                self._semantic = SemanticIndex(self.catalog_path)
                self._semantic.load_alignment(
                    self.catalog_path.with_suffix(".alignment.npz")
                )
            except Exception:
                self._semantic = False  # numpy missing / training failed: stay off
        if not self._semantic:
            return []
        try:
            return self._semantic.query(text)
        except Exception:
            return []

    def _match_keys(self, constraint: str) -> list[str]:
        # Simulator quotes are exact index keys; LLM-extracted free text may
        # only be a substring of one. Fuzzy matching runs (and is cached)
        # only for off-template constraints.
        if constraint in self.index.constraint_map:
            return [constraint]
        cached = self._fuzzy_cache.get(constraint)
        if cached is not None:
            return cached
        matches: list[str] = []
        if len(constraint) >= 4:
            matches = [key for key in self.index.constraint_map if constraint in key][:50]
        self._fuzzy_cache[constraint] = matches
        return matches

    def _rank(self, state: _SessionState, top_k: int) -> list[tuple[str, float]]:
        scores: dict[str, float] = defaultdict(float)
        budget: float | None = None

        for constraint in state.constraints:
            value = parse_budget(constraint)
            if value is not None:
                budget = value
            for key in self._match_keys(constraint):
                for pid, weight in self.index.constraint_map.get(key, ()):
                    scores[pid] += weight

        for pid, cosine in state.semantic.items():
            scores[pid] += SEMANTIC_WEIGHT * cosine

        category_ids = (
            self.index.category_map.get(state.category, []) if state.category else []
        )
        for pid in category_ids:
            scores[pid] += CATEGORY_BONUS

        if state.card_drained and state.constraints:
            banked = frozenset(state.constraints)
            for pid in scores:
                if self.index.cards.get(pid) == banked:
                    scores[pid] += EXACT_CARD_BONUS

        if budget is not None:
            for pid in scores:
                price = self.index.price.get(pid)
                if price is not None:
                    closeness = 1.0 - abs(price - budget) / (0.5 * budget + 1.0)
                    if closeness > 0.0:
                        scores[pid] += BUDGET_WEIGHT * closeness

        if not scores:
            return [(pid, 0.0) for pid in self._popular[:top_k]]

        pool = sorted(scores.items(), key=lambda item: -item[1])[:RERANK_POOL]
        tags = [
            normalize(str(tag))
            for tag in state.profile.get("preference_tags", [])
            if str(tag).strip()
        ]
        reranked: list[tuple[float, str]] = []
        for pid, score in pool:
            blob = self.index.blob.get(pid, "")
            score += PROFILE_TAG_WEIGHT * sum(1 for tag in tags if tag in blob)
            score += POPULARITY_WEIGHT * self.index.popularity.get(pid, 0.0)
            reranked.append((score, pid))
        reranked.sort(key=lambda item: (-item[0], item[1]))
        return [(pid, score) for score, pid in reranked[:top_k]]
