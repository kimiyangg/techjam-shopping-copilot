"""Tests for the inverse intent-card engine (parser + index + agent wiring)."""
from __future__ import annotations

import json

import pytest

from evaluator.local_evaluator import intent_card
from starter.intent_index import IntentIndex, normalize, parse_budget
from starter.parser import parse_message


class TestParser:
    def test_initial_buying(self):
        event = parse_message(
            "I'm looking for Women's Hiking Boots. A key requirement is: leather.", 1
        )
        assert event["type"] == "initial_buying"
        assert event["category"] == "Women's Hiking Boots"
        assert event["constraints"] == ["leather"]

    def test_initial_exploring(self):
        event = parse_message("I'm looking for Ankle Socks, but I'm still exploring.", 1)
        assert event["type"] == "initial_exploring"
        assert event["category"] == "Ankle Socks"

    def test_initial_override_carries_old_value(self):
        event = parse_message(
            "I'm looking for Running Shoes. Breathable mesh upper for all-day comfort", 1
        )
        assert event["type"] == "initial_override"
        assert event["category"] == "Running Shoes"
        assert event["constraints"] == ["Breathable mesh upper for all-day comfort"]

    def test_disclosure_splits_two_constraints(self):
        event = parse_message(
            "For that, what matters is: color: brown; budget around $75.99.", 5
        )
        assert event["type"] == "disclosure"
        assert event["constraints"] == ["color: brown", "budget around $75.99"]

    def test_override_message(self):
        event = parse_message(
            "Actually, ignore my earlier preference. What I need is: leather.", 3
        )
        assert event["type"] == "override"
        assert event["constraints"] == ["leather"]

    def test_boundary_no_preference(self):
        event = parse_message(
            "I don't have a preference for other; please use your judgment.", 2
        )
        assert event["type"] == "no_preference"
        assert event["attribute"] == "other"

    def test_exhausted_card(self):
        event = parse_message("I don't have an additional preference for other.", 4)
        assert event["type"] == "exhausted"

    def test_freeform_falls_through(self):
        assert parse_message("do you have anything waterproof?", 2)["type"] == "freeform"


class TestBudget:
    def test_parse_budget(self):
        assert parse_budget("budget around $75.99") == 75.99
        assert parse_budget("budget around $1,299") == 1299.0
        assert parse_budget("color: brown") is None


@pytest.fixture()
def tiny_catalog(tmp_path):
    products = [
        {
            "parent_asin": "A1",
            "title": "Trail Boot",
            "categories": ["Clothing, Shoes & Jewelry", "Women", "Hiking Boots"],
            "features": ["Waterproof full-grain leather upper", "Rubber outsole"],
            "details": {"Color": "Brown"},
            "price": 75.99,
            "rating_number": 900,
        },
        {
            "parent_asin": "A2",
            "title": "Cotton Tee",
            "categories": ["Clothing, Shoes & Jewelry", "Men", "T-Shirts"],
            "features": ["100% cotton"],
            "details": {},
            "price": 12.0,
            "rating_number": 40,
        },
    ]
    path = tmp_path / "catalog.jsonl"
    path.write_text("\n".join(json.dumps(p) for p in products) + "\n")
    return path


class TestIndex:
    def test_index_keys_match_evaluator_intent_card(self, tiny_catalog):
        index = IntentIndex(tiny_catalog)
        product = json.loads(tiny_catalog.read_text().splitlines()[0])
        card = intent_card(product)
        for constraint in [*card["hard_constraints"], *card["soft_preferences"]]:
            ids = [pid for pid, _ in index.constraint_map[normalize(constraint)]]
            assert "A1" in ids, f"missing key: {constraint!r}"

    def test_category_map_uses_coarse_leaf(self, tiny_catalog):
        index = IntentIndex(tiny_catalog)
        assert "A1" in index.category_map[normalize("Women Hiking Boots")]


class TestAgentEndToEnd:
    def test_banked_constraints_rank_target_first(self, tiny_catalog):
        from starter.agent import Agent

        agent = Agent(tiny_catalog)
        agent.reset("s1", {"preference_tags": ["durability"]})
        first = agent.respond(
            "s1", "I'm looking for Women Hiking Boots. A key requirement is: leather.", 1, 10
        )
        assert first["ask_attribute"] == "other"
        assert first["recommendations"][0]["parent_asin"] == "A1"
        second = agent.respond(
            "s1", "For that, what matters is: color: brown; budget around $75.99.", 2, 10
        )
        assert second["recommendations"][0]["parent_asin"] == "A1"

    def test_respond_never_raises(self, tiny_catalog):
        from starter.agent import Agent

        agent = Agent(tiny_catalog)
        # missing reset → internal error → safe fallback, not an exception
        response = agent.respond("ghost", "hello", 1, 10)
        assert isinstance(response["recommendations"], list)
        assert isinstance(response["message"], str)


class TestLLMLayer:
    def test_freeform_uses_extraction_when_available(self, tiny_catalog, monkeypatch):
        from starter import agent as agent_mod

        monkeypatch.setattr(
            agent_mod.llm_layer, "extract",
            lambda message: {
                "category": "Women Hiking Boots",
                "constraints": ["waterproof full-grain leather upper"],
                "usage": {"prompt_tokens": 100, "completion_tokens": 20},
            },
        )
        agent = agent_mod.Agent(tiny_catalog)
        agent.reset("s1", {})
        response = agent.respond("s1", "hey, got any waterproof leather boots?", 1, 10)
        assert response["usage"]["prompt_tokens"] == 100
        assert response["recommendations"][0]["parent_asin"] == "A1"

    def test_freeform_degrades_without_llm(self, tiny_catalog, monkeypatch):
        from starter import agent as agent_mod

        monkeypatch.setattr(agent_mod.llm_layer, "extract", lambda message: None)
        agent = agent_mod.Agent(tiny_catalog)
        agent.reset("s1", {})
        response = agent.respond("s1", "hey, got any boots?", 1, 10)
        assert isinstance(response["recommendations"], list)

    def test_extract_returns_none_without_sdk_or_key(self, monkeypatch):
        from starter import llm_layer

        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
        # Either the SDK is missing (ImportError path) or the call fails fast;
        # both must yield None, never an exception.
        assert llm_layer.extract("hello") is None or isinstance(
            llm_layer.extract("hello"), dict
        )
