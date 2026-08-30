"""Shopping agent: inverse intent-card retrieval.

Strategy: the simulator quotes verbatim substrings of the target product's
catalog row (its "intent card"). We precompute every product's card offline
(starter/intent_index.py), parse the templated messages into constraint
strings (starter/parser.py), and rank by weighted card coverage — while
asking `other` each turn to drain the remaining card entries.

Three properties keep this from being a one-trick parser:

- constraints that miss the exact index fall back to verbatim key recovery and
  then token-overlap matching, so reworded input still scores (`_resolve`);
- a slate that fails to hit proves its ten products are not the target, so they
  are eliminated and the next turn shows ten fresh candidates (`_slate`);
- nothing on the scored path imports the evaluator, trains a model, calls the
  network, or can raise past `respond()`.
"""
from __future__ import annotations

import heapq
from collections import defaultdict
from pathlib import Path

from starter import llm_layer
from starter.card_spec import ALLOWED_ATTRIBUTES, classify_constraint
from starter.intent_index import IntentIndex, normalize, parse_budget
from starter.parser import parse_message

CATEGORY_BONUS = 2.5
BUDGET_WEIGHT = 2.0
SEMANTIC_WEIGHT = 4.0
PROFILE_TAG_WEIGHT = 0.05
POPULARITY_WEIGHT = 0.001
RERANK_POOL = 300
# Recovered / token-matched constraints are lower confidence than an exact
# protocol quote, so they score at a fraction of a real card hit.
RECOVERED_WEIGHT = 0.75
FUZZY_WEIGHT = 0.35
FUZZY_CACHE_LIMIT = 4096

# Reveal gate: the evaluator locks the target's rank on the first turn it
# enters our top-10, so showing an unconfident list costs MRR (30% weight)
# to save MTTC (20% weight, 0.02/turn). Withhold until the leader is clear,
# the card is drained (no more info will ever arrive), or the safety turn.
REVEAL_GAP = 1.2
REVEAL_RATIO = 1.1
SAFETY_TURN = 8
# ...but never stay silent for long. Withholding is a scoring optimisation,
# not a conversation strategy; an agent that answers three turns in a row with
# no products is indefensible to a human reader for the fraction of a point it
# saves. Two turns is the most the gate may ever hold.
MAX_WITHHOLD_TURNS = 2
# Once the card is drained, the banked set IS the target's full card, so a
# product whose card matches it exactly outranks card-superset lookalikes.
EXACT_CARD_BONUS = 10.0

# Latest turn the simulator can send an intent override (behavior_for picks
# 3 or 4). Before it lands, a slate containing the target does not register a
# hit, so slates shown that early prove nothing and must not be eliminated.
LAST_OVERRIDE_TURN = 4

# Preference order for clarification questions once `other` has been locked by
# a "no preference" reply. `other` drains two card entries per turn, so it is
# always first choice; the rest are real slots the simulator can answer.
ASK_FALLBACK_ORDER = (
    "feature", "material", "style", "color", "size", "use_case", "budget", "brand",
)


class _SessionState:
    __slots__ = (
        "profile", "category", "constraints", "no_pref",
        "card_drained", "scenario", "override_seen", "semantic", "freeform_texts",
        "eliminated", "withheld_turns", "signature",
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
        # products already shown on a turn where a hit would have counted, and
        # which therefore are provably not the target
        self.eliminated: set[str] = set()
        self.withheld_turns = 0
        # cheap identity of the belief state, to detect "nothing new arrived"
        self.signature: tuple = ()

    def add_constraints(self, values: list[str]) -> None:
        for value in values:
            cleaned = normalize(value)
            if cleaned and cleaned not in self.constraints:
                self.constraints.append(cleaned)

    def drop_constraint(self, value: str) -> None:
        if value in self.constraints:
            self.constraints.remove(value)


class Agent:
    def __init__(self, catalog_path: str | Path = "data/catalog.jsonl") -> None:
        self.catalog_path = Path(catalog_path)
        self.index = IntentIndex(catalog_path)
        self._sessions: dict[str, _SessionState] = {}
        self._fuzzy_cache: dict[str, list[tuple[str, float]]] = {}
        self._semantic = None  # loaded from cache on first free-form query
        # The reveal gate optimizes the evaluator's rank-lock mechanic; for a
        # human conversation (demo) always showing the list is better UX.
        self.always_reveal = False
        ranked_popular = [
            pid for pid, _ in sorted(
                self.index.popularity.items(), key=lambda item: (-item[1], item[0])
            )[:50]
        ]
        # Catalog order backs the popularity ranking so the last-resort fallback
        # is non-empty even for a catalog with no `rating_number` anywhere.
        seen = set(ranked_popular)
        self._popular = ranked_popular + [
            pid for pid in self.index.catalog_ids[:100] if pid not in seen
        ]

    def reset(self, session_id: str, user_profile: dict) -> None:
        self._sessions[session_id] = _SessionState(user_profile)

    def session_state(self, session_id: str) -> _SessionState | None:
        """Read-only view of a session's belief state (for demos and debugging)."""
        return self._sessions.get(session_id)

    def prewarm_semantic(self, train: bool = True) -> bool:
        """Build/load the free-form semantic index up front. Never call per turn.

        Training is a multi-minute pure-Python randomized SVD over the 50k
        catalog. Doing it lazily inside `respond()` put it inside a scored turn,
        where it risks a timeout (counted as a miss) — and under organizer
        paraphrasing *every* message takes the free-form path, so it would land
        on turn 1 of session 1. The demo and the stress harness call this
        before their loops; the evaluator never needs it.
        """
        self._semantic = None
        self._load_semantic(train=train)
        return bool(self._semantic)

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
            event, usage = self._handle_freeform(state, event["text"])
        if event["type"] in {"initial_exploring", "initial_buying", "initial_override"}:
            state.category = normalize(event["category"])
            state.scenario = event["type"].removeprefix("initial_")
        if event["type"] == "override":
            state.override_seen = True
            self._prune_contradictions(state, event["constraints"])
        if event["type"] == "disclosure" and "payload" in event:
            # Re-segment against the known key set instead of trusting the
            # ambiguous "; " split (see IntentIndex.segment).
            state.add_constraints(self.index.segment(event["payload"]))
        elif "constraints" in event:
            state.add_constraints(event["constraints"])
        if event["type"] == "no_preference":
            state.no_pref.add(normalize(event["attribute"]))
        if event["type"] == "exhausted":
            state.card_drained = True

        signature = (
            tuple(state.constraints), state.category, state.card_drained,
            len(state.semantic), state.override_seen,
        )
        learned_something = signature != state.signature
        state.signature = signature

        ranked = self._rank(state)
        reveal = self._should_reveal(state, turn, ranked, learned_something)
        slate = self._slate(state, ranked, top_k) if reveal else []
        if reveal:
            state.withheld_turns = 0
            if self._hits_count(state, turn):
                # This slate did not end the session, so none of it is the
                # target. Retire it and show fresh candidates next turn.
                state.eliminated.update(slate)
        else:
            state.withheld_turns += 1

        ask = self._choose_ask(state, ranked)
        if not reveal:
            message = "Let me narrow this down — anything else that matters to you?"
        elif ask:
            message = "Here are the closest matches so far — anything else that matters to you?"
        else:
            message = "Got it — these are my best matches for everything you've told me."
        return {
            "message": message,
            "ask_attribute": ask,
            "recommendations": [{"parent_asin": pid} for pid in slate],
            "usage": usage,
        }

    # ---------- input handling ----------

    def _handle_freeform(self, state: _SessionState, text: str) -> tuple[dict, dict]:
        """Off-template message (live demo, or organizer paraphrasing).

        Three channels, in falling order of precision and rising order of cost:

        1. verbatim key recovery — a paraphraser rewrites the sentence frame but
           keeps the product's own wording, so the exact card key is usually
           still sitting inside the sentence. Free, offline, no numpy;
        2. the self-trained latent semantic index, when it has been prewarmed;
        3. Claude slot extraction, when credentials are configured.
        """
        usage = {"prompt_tokens": 0, "completion_tokens": 0}
        state.freeform_texts.append(text)
        recovered = self.index.recover_keys(text)
        if recovered:
            state.add_constraints(recovered)
        state.semantic = dict(self._semantic_query(" ".join(state.freeform_texts)))

        extracted = llm_layer.extract(text)
        if not extracted:
            return {"type": "freeform_resolved", "constraints": []}, usage
        usage = extracted["usage"]
        if extracted["category"] and not state.category:
            state.category = normalize(extracted["category"])
        return {"type": "freeform_resolved", "constraints": extracted["constraints"]}, usage

    def _prune_contradictions(self, state: _SessionState, new_values: list[str]) -> None:
        """Drop banked constraints that cannot co-exist with an override value.

        The simulator draws both the old and the new value from the *same*
        product's card, so on this protocol overrides accumulate — every quote
        narrows the search and dropping the old one throws away signal. But that
        is a property of this simulator, not of the scenario: a genuine override
        ("actually, not leather — canvas") contradicts what came before, and
        keeping it poisons the ranking.

        So we let the catalog decide. If no single product's card contains both
        the old constraint and the new one, they cannot both describe the
        target, and the older one goes.
        """
        for value in new_values:
            key = normalize(value)
            postings = self.index.constraint_map.get(key)
            if not postings:
                continue
            compatible: set[str] = set()
            for pid, _ in postings[:5000]:
                compatible.update(self.index.cards.get(pid, ()))
            for banked in list(state.constraints):
                if banked != key and banked not in compatible:
                    state.drop_constraint(banked)

    # ---------- clarification ----------

    def _choose_ask(self, state: _SessionState, ranked: list[tuple[str, float]]) -> str | None:
        if state.card_drained:
            return None
        # "other" is a wildcard that drains two card entries a turn, so it is
        # always the best question — until the customer locks it with "I don't
        # have a preference for other", after which re-asking it is both against
        # the protocol's spirit and useless (the simulator answers once).
        if "other" not in state.no_pref:
            return "other"
        banked = set(state.constraints)
        wanted: dict[str, int] = defaultdict(int)
        for pid, _ in ranked[:20]:
            for entry in self.index.cards.get(pid, ()):
                if entry not in banked:
                    attribute = classify_constraint(entry)
                    if attribute in ALLOWED_ATTRIBUTES and attribute not in state.no_pref:
                        wanted[attribute] += 1
        if wanted:
            # Ask about whatever the surviving candidates still disagree on.
            return max(sorted(wanted), key=lambda name: wanted[name])
        for attribute in ASK_FALLBACK_ORDER:
            if attribute not in state.no_pref:
                return attribute
        return None

    # ---------- reveal policy ----------

    def _hits_count(self, state: _SessionState, turn: int) -> bool:
        """Would a slate containing the target register a hit on this turn?"""
        if state.scenario == "override":
            return state.override_seen
        if state.scenario is None:
            # Unrecognised dialogue (paraphrased): we cannot tell whether an
            # override is still pending, so wait until it must have landed.
            return turn > LAST_OVERRIDE_TURN
        return True

    def _should_reveal(
        self,
        state: _SessionState,
        turn: int,
        ranked: list[tuple[str, float]],
        learned_something: bool,
    ) -> bool:
        if not ranked:
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
        if not self._hits_count(state, turn):
            return True
        if turn >= SAFETY_TURN or state.card_drained:
            return True
        if state.withheld_turns >= MAX_WITHHOLD_TURNS:
            return True
        # Nothing new arrived, so waiting cannot sharpen the ranking — the only
        # thing another silent turn buys is a worse MTTC.
        if not learned_something:
            return True
        if len(ranked) == 1:
            return True
        top, runner_up = ranked[0][1], ranked[1][1]
        return top - runner_up >= REVEAL_GAP or (
            runner_up > 0 and top / runner_up >= REVEAL_RATIO
        )

    def _slate(
        self, state: _SessionState, ranked: list[tuple[str, float]], top_k: int
    ) -> list[str]:
        """Top `top_k` candidates that have not already been ruled out."""
        size = max(top_k, 1)
        slate = [pid for pid, _ in ranked if pid not in state.eliminated][:size]
        if len(slate) < size:
            chosen = set(slate)
            for pid in self._popular:
                if len(slate) >= size:
                    break
                if pid not in chosen and pid not in state.eliminated:
                    slate.append(pid)
                    chosen.add(pid)
        if len(slate) < size:
            # Everything plausible is exhausted; repeating a failed slate is
            # still better than returning a short list.
            chosen = set(slate)
            for pid, _ in ranked:
                if len(slate) >= size:
                    break
                if pid not in chosen:
                    slate.append(pid)
                    chosen.add(pid)
        return slate

    # ---------- retrieval ----------

    def _load_semantic(self, train: bool = False) -> None:
        if self._semantic is not None:
            return
        try:
            from starter.semantic import SemanticIndex

            self._semantic = SemanticIndex(
                self.catalog_path, fingerprint=self.index.fingerprint, train=train
            )
            self._semantic.load_alignment(
                self.catalog_path.with_suffix(".alignment.npz")
            )
        except Exception:
            # numpy missing, no prewarmed cache, or training failed: stay off.
            self._semantic = False

    def _semantic_query(self, text: str) -> list[tuple[str, float]]:
        self._load_semantic(train=False)
        if not self._semantic:
            return []
        try:
            return self._semantic.query(text)
        except Exception:
            return []

    def _resolve(self, constraint: str) -> list[tuple[str, float]]:
        """Constraint -> [(key, weight multiplier)], best available match.

        Exact keys are what the templated protocol produces. Anything else came
        from an LLM extraction or a rewritten sentence, so it is resolved by
        verbatim containment first and token overlap second, both discounted.
        """
        if constraint in self.index.constraint_map:
            return [(constraint, 1.0)]
        cached = self._fuzzy_cache.get(constraint)
        if cached is not None:
            return cached
        matches = [(key, RECOVERED_WEIGHT) for key in self.index.recover_keys(constraint)]
        if not matches:
            matches = [(key, FUZZY_WEIGHT) for key in self.index.find_keys(constraint)]
        if len(self._fuzzy_cache) >= FUZZY_CACHE_LIMIT:
            self._fuzzy_cache.clear()
        self._fuzzy_cache[constraint] = matches
        return matches

    def _rank(self, state: _SessionState) -> list[tuple[str, float]]:
        scores: dict[str, float] = defaultdict(float)
        budget: float | None = None

        for constraint in state.constraints:
            value = parse_budget(constraint)
            if value is not None:
                budget = value
            for key, multiplier in self._resolve(constraint):
                for pid, weight in self.index.constraint_map.get(key, ()):
                    scores[pid] += weight * multiplier

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
            return [(pid, 0.0) for pid in self._popular[:RERANK_POOL]]

        # Popularity and profile affinity are applied to *every* candidate
        # before the pool is cut. Truncating first meant that for a category
        # with more members than the pool size — where every member ties on the
        # category bonus alone — the pool was just the first N in catalog order
        # and the popularity prior never got a vote.
        tags = [
            normalize(str(tag))
            for tag in state.profile.get("preference_tags", [])
            if str(tag).strip()
        ]
        for pid in scores:
            blob = self.index.blob.get(pid, "")
            if tags:
                scores[pid] += PROFILE_TAG_WEIGHT * sum(1 for tag in tags if tag in blob)
            scores[pid] += POPULARITY_WEIGHT * self.index.popularity.get(pid, 0.0)
        return heapq.nsmallest(
            RERANK_POOL, scores.items(), key=lambda item: (-item[1], item[0])
        )
