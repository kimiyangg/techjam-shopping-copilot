"""Replay one conformance case through the official protocol and judge it.

The turn loop mirrors `evaluator.local_evaluator.evaluate` exactly -- same
`initial_message`, same `customer_reply`, same `normalize_recommendations`,
same `override_applied` gate and the same break on first hit -- so a case that
passes here would score the same way in the real harness. What is added on top
is a recorded trace and a set of invariant checks over it.

`respond` is called directly, *not* through the evaluator's try/except, so an
exception is recorded as a failure instead of being silently converted into a
turn with no recommendations.
"""
from __future__ import annotations

import json
import traceback
from dataclasses import dataclass, field
from pathlib import Path

from evaluator.local_evaluator import (
    ALLOWED_ATTRIBUTES,
    MAX_TURNS,
    TOP_K,
    coarse_category,
    customer_reply,
    initial_message,
    normalize_recommendations,
)

MAX_RECOMMENDATIONS = 100  # docs/agent_api_contract.json: recommendations.maxItems


@dataclass
class Case:
    case_id: str
    family: str
    products: list[dict]
    target: str
    scenario_type: str = "buying"
    checks: tuple[str, ...] = ("contract", "no_exception")
    reply_policy: str = "official"     # official | always_no_pref
    paraphrase_seed: int | None = None
    override: dict | None = None
    always_reveal: bool = False
    skip_reset: bool = False
    messages: tuple[str, ...] | None = None   # fixed script, ignores the simulator
    profile: dict = field(default_factory=lambda: {
        "purchase_frequency": "3-4 prior purchases",
        "average_prior_rating": 4.0,
        "rating_style": "usually positive",
        "preference_tags": ["fit", "comfort"],
        "summary": "conformance profile",
    })
    min_coverage: int = 0
    max_rank: int = TOP_K


@dataclass
class Turn:
    index: int
    sent: str
    response: object
    error: str | None
    slate: list[str]
    ask: object


@dataclass
class Result:
    case_id: str
    family: str
    hit_turn: int | None
    rank: int | None
    turns: list[Turn]
    failures: list[str]

    @property
    def passed(self) -> bool:
        return not self.failures

    @property
    def shown(self) -> set[str]:
        return {pid for turn in self.turns for pid in turn.slate}


def write_catalog(products: list[dict], path: Path) -> Path:
    path.write_text(
        "\n".join(json.dumps(p) for p in products) + "\n", encoding="utf-8"
    )
    return path


def _catalog_views(products: list[dict]):
    ids, categories = set(), {}
    for row in products:
        pid = str(row["parent_asin"])
        ids.add(pid)
        categories[pid] = [str(v) for v in row.get("categories") or []]
    return ids, categories


def _intent_card(product: dict) -> dict:
    from evaluator.local_evaluator import intent_card

    return intent_card(product)


def _paraphrase(text: str, turn: int, seed: int) -> str:
    from starter.parser import parse_message
    from stress.paraphraser import Paraphraser

    return Paraphraser(seed=seed * 1000 + turn).render(parse_message(text, turn))


def run_case(case: Case, tmp_dir: Path, agent_factory=None) -> Result:
    from starter.agent import Agent

    catalog = write_catalog(case.products, tmp_dir / f"{case.case_id}.jsonl")
    catalog_ids, categories = _catalog_views(case.products)
    products_by_id = {str(p["parent_asin"]): p for p in case.products}

    agent = (agent_factory or Agent)(catalog)
    if case.always_reveal:
        agent.always_reveal = True
    session = f"conf_{case.case_id}"
    if not case.skip_reset:
        agent.reset(session, dict(case.profile))

    card = _intent_card(products_by_id[case.target])
    sample = {
        "sample_id": case.case_id,
        "scenario_type": case.scenario_type,
        "intent_card": card,
        "user_profile": case.profile,
    }
    if case.override:
        sample["behavior"] = {"override": case.override}

    disclosed: set[str] = set()
    boundary_used = False
    override_applied = case.scenario_type != "intent_override"
    if case.messages:
        message = case.messages[0]
    else:
        message = initial_message(
            sample, coarse_category(categories.get(case.target, [])), disclosed
        )
    if case.paraphrase_seed is not None:
        message = _paraphrase(message, 1, case.paraphrase_seed)

    turns: list[Turn] = []
    hit_turn = rank = None
    for index in range(1, MAX_TURNS + 1):
        error = None
        try:
            response = agent.respond(session, message, index, TOP_K)
        except Exception:
            response = None
            error = traceback.format_exc(limit=3)
        raw = response.get("recommendations") if isinstance(response, dict) else None
        slate = normalize_recommendations(raw, catalog_ids)
        ask = response.get("ask_attribute") if isinstance(response, dict) else None
        turns.append(Turn(index, message, response, error, slate, ask))

        if override_applied and case.target in slate:
            hit_turn, rank = index, slate.index(case.target) + 1
            break
        if index == MAX_TURNS:
            break

        if case.messages:
            message = case.messages[min(index, len(case.messages) - 1)]
            continue
        override = (sample.get("behavior") or {}).get("override") or {}
        if not override_applied and index + 1 == int(override.get("turn", 3)):
            override_applied = True
            if override.get("new_value"):
                disclosed.add(str(override["new_value"]))
            message = str(override["message"])
        elif case.reply_policy == "always_no_pref":
            attribute = ask if isinstance(ask, str) else "other"
            message = f"I don't have a preference for {attribute}; please use your judgment."
        else:
            message, boundary_used = customer_reply(sample, ask, disclosed, boundary_used)
        if case.paraphrase_seed is not None:
            message = _paraphrase(message, index + 1, case.paraphrase_seed)

    result = Result(case.case_id, case.family, hit_turn, rank, turns, [])
    result.failures = judge(case, result, catalog_ids)
    return result


# ---------------------------------------------------------------- invariants

def judge(case: Case, result: Result, catalog_ids: set[str]) -> list[str]:
    failures: list[str] = []
    for check in case.checks:
        failures.extend(CHECKS[check](case, result, catalog_ids))
    return failures


def _check_no_exception(case, result, catalog_ids):
    for turn in result.turns:
        if turn.error:
            first = turn.error.strip().splitlines()[-1]
            return [f"respond() raised on turn {turn.index}: {first}"]
    return []


def _check_contract(case, result, catalog_ids):
    """docs/agent_api_contract.json turn_response, checked on every turn."""
    problems = []
    for turn in result.turns:
        where = f"turn {turn.index}"
        response = turn.response
        if not isinstance(response, dict):
            problems.append(f"{where}: response is {type(response).__name__}, not dict")
            continue
        missing = {"message", "ask_attribute", "recommendations"} - set(response)
        if missing:
            problems.append(f"{where}: missing required key(s) {sorted(missing)}")
        extra = set(response) - {"message", "ask_attribute", "recommendations", "usage"}
        if extra:
            problems.append(f"{where}: undeclared key(s) {sorted(extra)}")
        if not isinstance(response.get("message"), str):
            problems.append(f"{where}: message is not a string")
        ask = response.get("ask_attribute")
        if ask is not None and ask not in ALLOWED_ATTRIBUTES:
            problems.append(f"{where}: ask_attribute {ask!r} is not an allowed attribute")
        items = response.get("recommendations")
        if not isinstance(items, list):
            problems.append(f"{where}: recommendations is not a list")
            continue
        if len(items) > MAX_RECOMMENDATIONS:
            problems.append(f"{where}: {len(items)} recommendations exceeds maxItems")
        seen = set()
        for position, item in enumerate(items):
            if not isinstance(item, dict) or "parent_asin" not in item:
                problems.append(f"{where}: recommendation {position} is not {{parent_asin}}")
                continue
            if set(item) - {"parent_asin", "score"}:
                problems.append(f"{where}: recommendation {position} has undeclared keys")
            pid = item["parent_asin"]
            if not isinstance(pid, str) or not pid:
                problems.append(f"{where}: recommendation {position} has a non-string id")
                continue
            if pid not in catalog_ids:
                problems.append(f"{where}: recommendation {position} {pid!r} is not in the catalog")
            if pid in seen:
                problems.append(f"{where}: recommendation {position} {pid!r} is a duplicate")
            seen.add(pid)
        usage = response.get("usage")
        if usage is not None:
            if not isinstance(usage, dict) or {"prompt_tokens", "completion_tokens"} - set(usage):
                problems.append(f"{where}: usage is malformed")
            elif not all(isinstance(v, int) and v >= 0 for v in usage.values()):
                problems.append(f"{where}: usage has negative or non-integer counts")
    return problems


def _check_hit(case, result, catalog_ids):
    if result.hit_turn is None:
        return [f"target {case.target} never entered the top-{TOP_K} in {MAX_TURNS} turns"]
    return []


def _check_rank(case, result, catalog_ids):
    if result.hit_turn is None:
        return [f"target {case.target} never entered the top-{TOP_K}"]
    if result.rank > case.max_rank:
        return [f"target ranked {result.rank}, worse than the required {case.max_rank}"]
    return []


def _check_fresh_slates(case, result, catalog_ids):
    """A slate that failed to end the session must never be shown again."""
    seen: dict[tuple[str, ...], int] = {}
    for turn in result.turns:
        if not turn.slate:
            continue
        key = tuple(turn.slate)
        if key in seen:
            return [f"turn {turn.index} repeated the slate already shown on turn {seen[key]}"]
        seen[key] = turn.index
    return []


def _check_coverage(case, result, catalog_ids):
    shown = result.shown
    if len(shown) < case.min_coverage:
        return [f"examined only {len(shown)} distinct products, expected >= {case.min_coverage}"]
    return []


def _check_no_repeat_ask(case, result, catalog_ids):
    """Once "no preference for X" is answered, X must never be asked again."""
    locked: set[str] = set()
    for turn in result.turns:
        ask = turn.ask
        if isinstance(ask, str):
            if ask in locked:
                return [f"turn {turn.index} re-asked {ask!r} after it was locked"]
            locked.add(ask)
    return []


def _check_popular_first(case, result, catalog_ids):
    if not result.turns[0].slate:
        return ["turn 1 returned no recommendations"]
    top = result.turns[0].slate[0]
    if top != case.target:
        return [f"turn 1 led with {top!r}; the only popular product is {case.target!r}"]
    return []


def _check_nonempty(case, result, catalog_ids):
    for turn in result.turns:
        if not turn.slate:
            return [f"turn {turn.index} returned no valid recommendations"]
    return []


CHECKS = {
    "no_exception": _check_no_exception,
    "contract": _check_contract,
    "hit": _check_hit,
    "rank": _check_rank,
    "fresh_slates": _check_fresh_slates,
    "coverage": _check_coverage,
    "no_repeat_ask": _check_no_repeat_ask,
    "popular_first": _check_popular_first,
    "nonempty": _check_nonempty,
}
