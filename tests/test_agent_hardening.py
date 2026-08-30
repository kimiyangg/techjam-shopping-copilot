"""Regression tests for the robustness fixes.

Each test pins a defect that was previously silent: the agent still produced a
well-formed response, it just quietly lost signal, wasted turns, or degraded to
a category prior.
"""
from __future__ import annotations

import json

import pytest

from evaluator.local_evaluator import (
    coarse_category,
    customer_reply,
    initial_message,
    intent_card,
    normalize_recommendations,
)
from starter.agent import MAX_WITHHOLD_TURNS, RERANK_POOL, Agent
from starter.intent_index import IntentIndex, normalize
from starter.parser import parse_message


def write_catalog(tmp_path, products, name="catalog.jsonl"):
    path = tmp_path / name
    path.write_text("\n".join(json.dumps(p) for p in products) + "\n", encoding="utf-8")
    return path


def boot(pid, **overrides):
    product = {
        "parent_asin": pid,
        "title": f"Trail Boot {pid}",
        "categories": ["Clothing, Shoes & Jewelry", "Women", "Hiking Boots"],
        "features": ["Waterproof leather upper", "Rubber outsole"],
        "details": {"Closure type": "Lace-up"},
        "price": 75.99,
        "rating_number": 500,
    }
    product.update(overrides)
    return product


def run_session(agent, sample, categories, catalog_ids, target, turns=10):
    """Replay the evaluator's loop; return (hit_turn, rank, slates)."""
    disclosed: set[str] = set()
    boundary_used = False
    override_applied = sample["scenario_type"] != "intent_override"
    message = initial_message(sample, coarse_category(categories[target]), disclosed)
    slates = []
    for turn in range(1, turns + 1):
        response = agent.respond("s", message, turn, 10)
        ranked = normalize_recommendations(response["recommendations"], catalog_ids)
        slates.append(tuple(ranked))
        if override_applied and target in ranked:
            return turn, ranked.index(target) + 1, slates
        override = sample.get("behavior", {}).get("override") or {}
        if not override_applied and turn + 1 == int(override.get("turn", 3)):
            override_applied = True
            disclosed.add(str(override["new_value"]))
            message = str(override["message"])
        else:
            message, boundary_used = customer_reply(
                sample, response["ask_attribute"], disclosed, boundary_used
            )
    return None, None, slates


# --------------------------------------------------------------------------
# C3 — the "; " disclosure split is ambiguous
# --------------------------------------------------------------------------

class TestDisclosureSegmentation:
    @pytest.fixture()
    def index(self, tmp_path):
        return IntentIndex(write_catalog(tmp_path, [
            boot("A1", features=["Imported; rubber sole", "Waterproof full-grain leather upper"]),
        ]))

    def test_segment_keeps_a_constraint_that_contains_the_separator(self, index):
        # The simulator emits "; ".join(["leather", "Imported; rubber sole"]).
        assert index.segment("leather; Imported; rubber sole") == [
            "leather", "Imported; rubber sole",
        ]

    def test_segment_leaves_unambiguous_payloads_alone(self, index):
        assert index.segment("leather; color: brown") == ["leather", "color: brown"]
        assert index.segment("leather") == ["leather"]

    def test_parser_hands_the_raw_payload_through(self):
        event = parse_message("For that, what matters is: a; b; c.", 3)
        assert event["payload"] == "a; b; c"

    def test_banked_constraints_reconstruct_the_card_exactly(self, tmp_path):
        """The drained-card equality bonus can only fire if segmentation is right."""
        catalog = write_catalog(tmp_path, [
            boot("A1", features=["Imported; rubber sole", "Waterproof full-grain leather upper"]),
        ])
        agent = Agent(catalog)
        agent.always_reveal = True
        agent.reset("s", {"preference_tags": []})
        card = intent_card(json.loads(catalog.read_text(encoding="utf-8").splitlines()[0]))
        sample = {"scenario_type": "buying", "intent_card": card}
        disclosed: set[str] = set()
        message = initial_message(sample, "women hiking boots", disclosed)
        for turn in range(1, 6):
            response = agent.respond("s", message, turn, 10)
            message, _ = customer_reply(sample, response["ask_attribute"], disclosed, False)
        state = agent.session_state("s")
        assert frozenset(state.constraints) == agent.index.cards["A1"]

    def test_orphan_fragments_never_enter_the_constraint_state(self, tmp_path):
        """'imported' alone used to fuzzy-expand to 50 unrelated products.

        A browsing session, so the whole card arrives through the ambiguous
        disclosure channel rather than being seeded by the opening message.
        """
        products = [boot("TARGET", features=["Imported; rubber sole", "Waterproof full-grain leather upper"])]
        products += [
            {"parent_asin": f"NOISE{i:02d}", "title": f"Silk Scarf {i}",
             "categories": ["Clothing, Shoes & Jewelry", "Women", "Scarves"],
             "features": [f"Imported silk variant {i}", "Hand rolled edges"],
             "details": {}, "price": 20.0, "rating_number": 4000}
            for i in range(60)
        ]
        catalog = write_catalog(tmp_path, products)
        agent = Agent(catalog)
        agent.reset("s", {"preference_tags": []})
        card = intent_card(products[0])
        sample = {"scenario_type": "browsing", "intent_card": card}
        disclosed: set[str] = set()
        message = initial_message(sample, "women scarves", disclosed)
        for turn in range(1, 4):
            response = agent.respond("s", message, turn, 10)
            message, _ = customer_reply(sample, response["ask_attribute"], disclosed, False)
        banked = agent.session_state("s").constraints
        assert "imported; rubber sole" in banked
        assert "imported" not in banked and "rubber sole" not in banked, banked
        # The mis-split used to pull 50 arbitrary keys in behind one fragment.
        assert agent._resolve("imported; rubber sole") == [("imported; rubber sole", 1.0)]


# --------------------------------------------------------------------------
# C2 — a failed slate proves its ten products are not the target
# --------------------------------------------------------------------------

class TestSlateElimination:
    @pytest.fixture()
    def lookalikes(self, tmp_path):
        products = [boot(f"B{i:02d}", price=70.0 + i, rating_number=100 + i) for i in range(40)]
        return write_catalog(tmp_path, products), products

    def test_ten_turns_examine_more_than_ten_candidates(self, lookalikes):
        catalog, products = lookalikes
        agent = Agent(catalog)
        agent.reset("s", {"preference_tags": []})
        categories = {p["parent_asin"]: p["categories"] for p in products}
        catalog_ids = {p["parent_asin"] for p in products}
        target = "B07"
        sample = {"scenario_type": "buying", "intent_card": intent_card(products[7])}
        hit_turn, rank, slates = run_session(agent, sample, categories, catalog_ids, target)
        shown = {pid for slate in slates for pid in slate}
        assert len(shown) > 10, "the agent must not re-show one frozen slate for seven turns"
        assert hit_turn is not None, "40 indistinguishable candidates fit inside 10 slates"

    def test_a_shown_slate_is_not_repeated(self, lookalikes):
        catalog, products = lookalikes
        agent = Agent(catalog)
        agent.reset("s", {"preference_tags": []})
        categories = {p["parent_asin"]: p["categories"] for p in products}
        catalog_ids = {p["parent_asin"] for p in products}
        _, _, slates = run_session(agent, sample_for(products, 7), categories, catalog_ids, "B07")
        nonempty = [s for s in slates if s]
        assert len(set(nonempty)) == len(nonempty), "every revealed slate must be new"

    def test_pre_override_slates_are_never_eliminated(self, tmp_path):
        """A hit before the override turn does not register, so it proves nothing."""
        products = [boot(f"B{i:02d}", price=70.0 + i, rating_number=100 + i) for i in range(40)]
        catalog = write_catalog(tmp_path, products)
        agent = Agent(catalog)
        agent.reset("s", {"preference_tags": []})
        card = intent_card(products[7])
        sample = {
            "scenario_type": "intent_override",
            "intent_card": card,
            "behavior": {"override": {
                "turn": 3,
                "old_value": card["soft_preferences"][-1],
                "new_value": card["hard_constraints"][0],
                "message": f"Actually, ignore my earlier preference. What I need is: {card['hard_constraints'][0]}.",
            }},
        }
        state = agent.session_state("s")
        message = initial_message(sample, "women hiking boots", set())
        for turn in (1, 2):
            agent.respond("s", message, turn, 10)
            assert state.eliminated == set(), (
                "a pre-override slate does not register a hit, so it rules nothing out"
            )
        agent.respond("s", sample["behavior"]["override"]["message"], 3, 10)
        assert state.override_seen
        agent.respond("s", "Those options are not quite right yet.", 4, 10)
        assert state.eliminated, "after the override lands, failed slates are informative"

    def test_unrecognised_dialogue_defers_elimination_past_the_override_window(self, lookalikes):
        catalog, _ = lookalikes
        agent = Agent(catalog)
        agent.always_reveal = True
        agent.reset("s", {"preference_tags": []})
        for turn in (1, 2, 3, 4):
            agent.respond("s", "hey, got any rugged boots?", turn, 10)
            assert agent.session_state("s").eliminated == set(), (
                "cannot rule anything out while an override may still be pending"
            )
        agent.respond("s", "hey, got any rugged boots?", 5, 10)
        assert agent.session_state("s").eliminated


def sample_for(products, i):
    return {"scenario_type": "buying", "intent_card": intent_card(products[i])}


# --------------------------------------------------------------------------
# H2 — paraphrased input still carries the product's own wording
# --------------------------------------------------------------------------

class TestParaphraseRecovery:
    @pytest.fixture()
    def catalog(self, tmp_path):
        return write_catalog(tmp_path, [
            boot("A1", features=["Waterproof full-grain leather upper", "Rubber outsole"]),
            {"parent_asin": "A2", "title": "Cotton Tee",
             "categories": ["Clothing, Shoes & Jewelry", "Men", "T-Shirts"],
             "features": ["100% cotton jersey knit"], "details": {}, "price": 12.0,
             "rating_number": 40},
        ])

    def test_verbatim_keys_are_recovered_from_free_text(self, catalog, monkeypatch):
        from starter import agent as agent_mod

        monkeypatch.setattr(agent_mod.llm_layer, "extract", lambda m: None)
        agent = Agent(catalog)
        agent.always_reveal = True
        agent.reset("s", {"preference_tags": []})
        response = agent.respond(
            "s", "honestly what matters most is waterproof full-grain leather upper.", 1, 10
        )
        state = agent.session_state("s")
        assert "waterproof full-grain leather upper" in state.constraints
        assert response["recommendations"][0]["parent_asin"] == "A1"

    def test_paraphrased_disclosure_survives_without_an_llm(self, catalog, monkeypatch):
        from starter import agent as agent_mod
        from stress.paraphraser import Paraphraser

        monkeypatch.setattr(agent_mod.llm_layer, "extract", lambda m: None)
        event = parse_message(
            "For that, what matters is: Waterproof full-grain leather upper.", 3
        )
        paraphrased = Paraphraser(seed=1).render(event)
        assert "waterproof full-grain leather upper" in paraphrased.lower()
        agent = Agent(catalog)
        agent.always_reveal = True
        agent.reset("s", {"preference_tags": []})
        response = agent.respond("s", paraphrased, 1, 10)
        assert response["recommendations"][0]["parent_asin"] == "A1"

    def test_reworded_input_falls_back_to_token_overlap(self, catalog):
        index = IntentIndex(catalog)
        keys = index.find_keys("full-grain waterproof leather uppers")
        assert "waterproof full-grain leather upper" in keys


# --------------------------------------------------------------------------
# H4 — the reveal gate must not go silent for long
# --------------------------------------------------------------------------

class TestRevealPolicy:
    def test_withholding_is_bounded(self, tmp_path):
        products = [boot(f"B{i:02d}", price=70.0 + i, rating_number=100 + i) for i in range(40)]
        catalog = write_catalog(tmp_path, products)
        agent = Agent(catalog)
        agent.reset("s", {"preference_tags": []})
        categories = {p["parent_asin"]: p["categories"] for p in products}
        catalog_ids = {p["parent_asin"] for p in products}
        _, _, slates = run_session(agent, sample_for(products, 7), categories, catalog_ids, "B07")
        streak = longest = 0
        for slate in slates:
            streak = streak + 1 if not slate else 0
            longest = max(longest, streak)
        assert longest <= MAX_WITHHOLD_TURNS

    def test_a_turn_that_taught_us_nothing_reveals(self, tmp_path):
        catalog = write_catalog(tmp_path, [boot(f"B{i:02d}") for i in range(20)])
        agent = Agent(catalog)
        agent.reset("s", {"preference_tags": []})
        agent.respond("s", "I'm looking for Women Hiking Boots, but I'm still exploring.", 1, 10)
        # A nudge carries no information; holding the list back buys nothing.
        second = agent.respond("s", "Those options are not quite right yet.", 2, 10)
        assert second["recommendations"]


# --------------------------------------------------------------------------
# "no preference" locks an attribute
# --------------------------------------------------------------------------

class TestNoPreferenceLock:
    def test_locked_attribute_is_never_asked_again(self, tmp_path):
        products = [boot(f"B{i:02d}", price=70.0 + i) for i in range(20)]
        catalog = write_catalog(tmp_path, products)
        agent = Agent(catalog)
        agent.reset("s", {"preference_tags": []})
        first = agent.respond(
            "s", "I'm looking for Women Hiking Boots, but I'm still exploring.", 1, 10
        )
        assert first["ask_attribute"] == "other"
        asked = []
        message = "I don't have a preference for other; please use your judgment."
        for turn in range(2, 8):
            response = agent.respond("s", message, turn, 10)
            asked.append(response["ask_attribute"])
            message = f"I don't have a preference for {response['ask_attribute']}; please use your judgment."
        assert "other" not in asked, asked
        assert len(asked) == len(set(asked)), f"re-asked a locked attribute: {asked}"

    def test_lock_is_recorded_in_state(self, tmp_path):
        catalog = write_catalog(tmp_path, [boot("B01")])
        agent = Agent(catalog)
        agent.reset("s", {})
        agent.respond("s", "I don't have a preference for color; please use your judgment.", 2, 10)
        assert "color" in agent.session_state("s").no_pref


# --------------------------------------------------------------------------
# intent override: replace what the catalog says cannot co-exist
# --------------------------------------------------------------------------

class TestOverridePruning:
    def test_compatible_old_value_is_kept(self, tmp_path):
        """On this simulator both values come from one card, so both are signal."""
        catalog = write_catalog(tmp_path, [boot("A1")])
        agent = Agent(catalog)
        agent.reset("s", {})
        card = agent.index.cards["A1"]
        old, new = sorted(card)[0], sorted(card)[1]
        agent.respond("s", f"I'm looking for Women Hiking Boots. {old}", 1, 10)
        agent.respond("s", f"Actually, ignore my earlier preference. What I need is: {new}.", 3, 10)
        state = agent.session_state("s")
        assert normalize(old) in state.constraints
        assert normalize(new) in state.constraints

    def test_contradictory_old_value_is_dropped(self, tmp_path):
        """A genuine override: nothing in the catalog is both leather and cotton."""
        catalog = write_catalog(tmp_path, [
            boot("A1", features=["Waterproof full-grain leather upper"]),
            {"parent_asin": "A2", "title": "Cotton Tee",
             "categories": ["Clothing, Shoes & Jewelry", "Men", "T-Shirts"],
             "features": ["100% cotton jersey knit"], "details": {}, "price": 12.0,
             "rating_number": 40},
        ])
        agent = Agent(catalog)
        agent.reset("s", {})
        agent.respond(
            "s", "I'm looking for Women Hiking Boots. Waterproof full-grain leather upper", 1, 10
        )
        assert "waterproof full-grain leather upper" in agent.session_state("s").constraints
        agent.respond(
            "s",
            "Actually, ignore my earlier preference. What I need is: 100% cotton jersey knit.",
            3, 10,
        )
        state = agent.session_state("s")
        assert "waterproof full-grain leather upper" not in state.constraints
        assert "100% cotton jersey knit" in state.constraints


# --------------------------------------------------------------------------
# ranking hygiene
# --------------------------------------------------------------------------

class TestRankingHygiene:
    def test_popularity_survives_the_pool_cut(self, tmp_path):
        """With a category larger than the pool, the popularity prior must still vote.

        Every member ties on the category bonus alone, so truncating before the
        rerank left the pool as "the first RERANK_POOL rows in catalog order".
        """
        size = RERANK_POOL + 100
        products = [boot(f"P{i:04d}", rating_number=i) for i in range(size)]
        catalog = write_catalog(tmp_path, products)
        agent = Agent(catalog)
        agent.always_reveal = True
        agent.reset("s", {"preference_tags": []})
        response = agent.respond(
            "s", "I'm looking for Women Hiking Boots, but I'm still exploring.", 1, 10
        )
        assert response["recommendations"][0]["parent_asin"] == f"P{size - 1:04d}"

    def test_ranking_is_deterministic_across_instances(self, tmp_path):
        products = [boot(f"P{i:03d}", rating_number=7) for i in range(50)]
        catalog = write_catalog(tmp_path, products)
        slates = []
        for _ in range(2):
            agent = Agent(catalog)
            agent.always_reveal = True
            agent.reset("s", {"preference_tags": []})
            response = agent.respond(
                "s", "I'm looking for Women Hiking Boots, but I'm still exploring.", 1, 10
            )
            slates.append([r["parent_asin"] for r in response["recommendations"]])
        assert slates[0] == slates[1]

    def test_fallback_list_is_never_empty_without_ratings(self, tmp_path):
        catalog = write_catalog(tmp_path, [
            {"parent_asin": f"N{i}", "title": f"Thing {i}", "categories": ["Misc"],
             "features": [f"feature {i}"], "details": {}}
            for i in range(15)
        ])
        agent = Agent(catalog)
        assert agent.index.popularity == {}
        # No reset -> internal error -> the fallback path must still return ten.
        response = agent.respond("ghost", "hello", 1, 10)
        assert len(response["recommendations"]) == 10

    def test_response_shape_matches_the_contract(self, tmp_path):
        catalog = write_catalog(tmp_path, [boot("A1")])
        agent = Agent(catalog)
        agent.reset("s", {"preference_tags": []})
        response = agent.respond("s", "I'm looking for Women Hiking Boots.", 1, 10)
        assert set(response) == {"message", "ask_attribute", "recommendations", "usage"}
        assert isinstance(response["message"], str)
        assert response["ask_attribute"] in {
            "category", "material", "color", "size", "style", "brand",
            "budget", "feature", "use_case", "other", None,
        }
        assert all(set(r) == {"parent_asin"} for r in response["recommendations"])
        assert set(response["usage"]) == {"prompt_tokens", "completion_tokens"}
        assert all(v >= 0 for v in response["usage"].values())


# --------------------------------------------------------------------------
# the semantic index must never train inside a scored turn
# --------------------------------------------------------------------------

class TestSemanticLifecycle:
    def test_scored_path_never_trains(self, tmp_path, monkeypatch):
        catalog = write_catalog(tmp_path, [boot("A1"), boot("A2")])
        calls = []

        import starter.semantic as semantic_mod

        class Spy:
            def __init__(self, path, cache_path=None, fingerprint="", train=True):
                calls.append(train)
                if not train:
                    raise FileNotFoundError("no cache")

        monkeypatch.setattr(semantic_mod, "SemanticIndex", Spy)
        agent = Agent(catalog)
        monkeypatch.setattr("starter.agent.llm_layer.extract", lambda m: None)
        agent.reset("s", {})
        agent.respond("s", "anything waterproof and rugged?", 1, 10)
        assert calls == [False], "respond() must only ever load a prebuilt index"

    def test_prewarm_is_the_only_training_entrypoint(self, tmp_path, monkeypatch):
        catalog = write_catalog(tmp_path, [boot("A1")])
        calls = []

        import starter.semantic as semantic_mod

        class Spy:
            def __init__(self, path, cache_path=None, fingerprint="", train=True):
                calls.append(train)

            def load_alignment(self, path):
                return False

        monkeypatch.setattr(semantic_mod, "SemanticIndex", Spy)
        agent = Agent(catalog)
        agent.prewarm_semantic()
        assert calls == [True]

    def test_cache_from_a_different_catalog_is_rejected(self, tmp_path):
        pytest.importorskip("numpy")
        from starter.semantic import SemanticIndex

        products = []
        for i in range(4):
            products.append({"parent_asin": f"BOOT{i}", "title": "Waterproof Hiking Boot",
                             "features": ["waterproof leather upper", "rugged outdoor sole"],
                             "categories": ["Shoes", "Hiking Boots"]})
            products.append({"parent_asin": f"TEE{i}", "title": "Cotton Graphic Tshirt",
                             "features": ["soft cotton fabric", "casual summer wear"],
                             "categories": ["Clothing", "Shirts"]})
        catalog = write_catalog(tmp_path, products)
        cache = tmp_path / "cache.npz"
        SemanticIndex(catalog, cache_path=cache, fingerprint="catalog-v1")
        assert cache.exists()
        # Same cache file, different catalog identity: must refuse to load it.
        stale = SemanticIndex(catalog, cache_path=cache, fingerprint="catalog-v2")
        assert stale.fingerprint == "catalog-v2"
        reloaded = SemanticIndex(catalog, cache_path=cache, fingerprint="catalog-v2", train=False)
        assert reloaded.pids
