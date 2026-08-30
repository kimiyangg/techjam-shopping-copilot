"""Paraphrase stress test: the official 200 sessions, in natural language.

Replays the official evaluator's session logic, but every simulator message
is paraphrased into varied human English before the agent sees it — which
deliberately destroys our template parser's advantage. What remains is the
generalization stack: fuzzy matching, the self-trained semantic index, the
learned alignment model, and (if configured) Claude extraction.

The official evaluator and public labels are untouched; this harness imports
their logic and only rewrites the message surface.

Usage: python3 -m stress.harness [--seed 0]
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict

from evaluator.local_evaluator import (
    MAX_TURNS,
    TOP_K,
    catalog_index,
    customer_reply,
    initial_message,
    coarse_category,
    load_jsonl,
    materialize_hidden_fields,
    metric_summary,
    normalize_recommendations,
)
from starter.agent import Agent
from starter.parser import parse_message
from stress.paraphraser import Paraphraser


def evaluate_paraphrased(agent: Agent, samples, catalog_ids, categories, products, seed=0):
    sessions = []
    for sample_number, sample in enumerate(samples):
        paraphraser = Paraphraser(seed=seed * 100_000 + sample_number)
        session_id = f"stress_{sample_number}"
        agent.reset(session_id, sample["user_profile"])
        target = str(sample["ground_truth"]["parent_asin"])
        card, behavior = materialize_hidden_fields(sample, products)
        effective = {**sample, "intent_card": card, "behavior": behavior}
        disclosed: set = set()
        boundary_used = False
        override_applied = sample["scenario_type"] != "intent_override"
        canonical = initial_message(effective, coarse_category(categories.get(target, [])), disclosed)
        user_message = paraphraser.render(parse_message(canonical, 1))
        hit_turn = best_rank = None
        for turn in range(1, MAX_TURNS + 1):
            try:
                response = agent.respond(session_id, user_message, turn, TOP_K)
            except Exception:
                response = {"message": "", "ask_attribute": None, "recommendations": []}
            ranked = normalize_recommendations(response.get("recommendations"), catalog_ids)
            if override_applied and target in ranked:
                best_rank = ranked.index(target) + 1
                hit_turn = turn
                break
            if turn == MAX_TURNS:
                break
            override = effective.get("behavior", {}).get("override") or {}
            if not override_applied and turn + 1 == int(override.get("turn", 3)):
                override_applied = True
                new_value = str(override.get("new_value", ""))
                if new_value:
                    disclosed.add(new_value)
                canonical = str(override.get("message", ""))
            else:
                canonical, boundary_used = customer_reply(
                    effective, response.get("ask_attribute"), disclosed, boundary_used
                )
            user_message = paraphraser.render(parse_message(canonical, turn + 1))
        sessions.append({
            "sample_id": sample["sample_id"],
            "scenario_type": sample["scenario_type"],
            "hit": hit_turn is not None,
            "first_hit_turn": hit_turn,
            "best_rank": best_rank,
            "reciprocal_rank": 0.0 if best_rank is None else 1.0 / best_rank,
        })

    overall = metric_summary(sessions)
    efficiency = max(0.0, min(1.0, (11.0 - float(overall["mttc"])) / 10.0))
    score = 0.50 * overall["hit_rate_at_10"] + 0.30 * overall["mrr"] + 0.20 * efficiency
    grouped = defaultdict(list)
    for session in sessions:
        grouped[session["scenario_type"]].append(session)
    return {
        **overall,
        "efficiency": round(efficiency, 6),
        "recommended_technical_score": round(score, 6),
        "scenario_metrics": {name: metric_summary(grouped[name]) for name in sorted(grouped)},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Paraphrase stress test")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--dataset", default="data/public_set.jsonl")
    args = parser.parse_args()
    samples = load_jsonl(args.dataset)
    catalog_ids, categories, products = catalog_index(args.catalog)
    agent = Agent(args.catalog)
    # Training must not happen inside a turn; build it up front like a
    # submission would ship a prebuilt index.
    print("building semantic index (one-time)...")
    print("  semantic index:", "ready" if agent.prewarm_semantic() else "unavailable")
    result = evaluate_paraphrased(agent, samples, catalog_ids, categories, products, args.seed)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
