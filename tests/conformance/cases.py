"""The 200 conformance cases, in eight families of 25.

Each family isolates one protocol obligation and builds a catalog where that
obligation is *decisive* -- the target is unreachable unless the agent honours
it. Families 6 and 8 are the opposite: they assert only that the contract holds
under input the agent has no reason to expect, and are meant to pass always.
"""
from __future__ import annotations

from evaluator.local_evaluator import TOP_K

from tests.conformance import catalogs
from tests.conformance.runner import Case

FAMILY_SIZE = 25


def _separator_cases() -> list[Case]:
    """F1 - a constraint containing the simulator's own "; " join separator.

    Browsing, so the compound constraint arrives through `customer_reply`
    (which joins with "; ") rather than through the opening message (which does
    not). Splitting it naively hands the target's only discriminating evidence
    to the two decoys keyed on its fragments.
    """
    cases = []
    for seed in range(FAMILY_SIZE):
        products, target = catalogs.separator_family(seed)
        cases.append(Case(
            case_id=f"f1_separator_{seed:02d}",
            family="separator",
            products=products,
            target=target,
            scenario_type="browsing",
            checks=("contract", "no_exception", "hit", "rank"),
            max_rank=1,
        ))
    return cases


def _lookalike_cases() -> list[Case]:
    """F2 - more indistinguishable candidates than one slate can hold.

    Nothing the protocol emits separates them, and the target is the least
    popular of the pool, so it is reachable only by showing successive slates.
    """
    cases = []
    for i in range(FAMILY_SIZE):
        size = 12 + i * 3          # 12 .. 84
        target_at = size - 1 - (i % 4)
        products, target = catalogs.lookalike_family(size, target_at)
        cases.append(Case(
            case_id=f"f2_lookalike_{i:02d}_n{size}",
            family="lookalike",
            products=products,
            target=target,
            scenario_type="buying",
            checks=("contract", "no_exception", "fresh_slates", "coverage")
                   + (("hit",) if size <= TOP_K * 8 else ()),
            min_coverage=min(size, TOP_K * 2),
        ))
    return cases


def _boundary_cases() -> list[Case]:
    """F3 - a customer who answers every question with "no preference".

    The official simulator only does this once per session; this is the same
    behaviour taken to its limit. Re-asking a locked attribute is both against
    the protocol and useless, since the answer cannot change.
    """
    cases = []
    for seed in range(FAMILY_SIZE):
        products, target = catalogs.boundary_family(seed)
        cases.append(Case(
            case_id=f"f3_boundary_{seed:02d}",
            family="boundary",
            products=products,
            target=target,
            scenario_type="boundary",
            reply_policy="always_no_pref",
            checks=("contract", "no_exception", "no_repeat_ask"),
        ))
    return cases


def _wide_category_cases() -> list[Case]:
    """F4 - a category with far more members than any sane rerank pool.

    Every member ties on the category bonus, so popularity is the only signal
    -- and it only counts if it is applied before the pool is truncated. The
    popular row sits deep in catalog order precisely to catch a pool cut that
    happens too early.
    """
    cases = []
    for i in range(FAMILY_SIZE):
        size = 320 + i * 20        # 320 .. 800
        popular_at = size - 1 - (i * 7 % 40)
        products, target = catalogs.wide_category_family(size, popular_at)
        cases.append(Case(
            case_id=f"f4_wide_{i:02d}_n{size}",
            family="wide_category",
            products=products,
            target=target,
            scenario_type="browsing",
            always_reveal=True,     # the reveal gate is not what is under test
            checks=("contract", "no_exception", "popular_first"),
        ))
    return cases


def _paraphrase_cases() -> list[Case]:
    """F5 - every simulator message rewritten into free-form English.

    The paraphraser rewrites the sentence frame but keeps the product's own
    wording, exactly as a real customer or an organizer paraphraser would. The
    distinguishing phrase is therefore still present verbatim; the template
    parser just cannot see it any more.
    """
    cases = []
    for seed in range(FAMILY_SIZE):
        products, target = catalogs.paraphrase_family(seed)
        cases.append(Case(
            case_id=f"f5_paraphrase_{seed:02d}",
            family="paraphrase",
            products=products,
            target=target,
            scenario_type="browsing",
            paraphrase_seed=seed + 1,
            checks=("contract", "no_exception", "hit"),
        ))
    return cases


def _hostile_input_cases() -> list[Case]:
    """F6 - input the agent has no reason to expect. Must never break it.

    A regression net rather than a differentiator: every one of these should
    pass on any revision, and the corpus is only trustworthy if they do.
    """
    hostile = [
        ("empty", ("",) * 3),
        ("whitespace", ("   \t  \n ",) * 3),
        ("newlines", ("line one\nline two\r\nline three",) * 2),
        ("very_long", ("quartz " * 4000,) * 2),
        ("emoji", ("\U0001f9e5\U0001f45f\U0001f9f5 anything?",) * 2),
        ("control_chars", ("bad \x00 \x07 \x1b[31m input",) * 2),
        ("json_text", ('{"parent_asin": "TARGET", "hack": true}',) * 2),
        ("sql_ish", ("'; DROP TABLE products; --",) * 2),
        ("template_prefix_only", ("I'm looking for",) * 2),
        ("template_truncated", ("For that, what matters is:",) * 2),
        ("template_no_payload", ("For that, what matters is: .",) * 2),
        ("only_separators", ("; ; ; ; ;",) * 2),
        ("repeated_override", ("Actually, ignore my earlier preference. What I need is: .",) * 3),
        ("no_pref_blank", ("I don't have a preference for ; please use your judgment.",) * 2),
        ("unicode_rtl", ("‮evil‬ مرحبا",) * 2),
        ("null_bytes_only", ("\x00\x00\x00",) * 2),
        ("html", ("<script>alert(1)</script>",) * 2),
        ("path_traversal", ("../../etc/passwd",) * 2),
        ("format_string", ("%s %d {0} {target} $HOME",) * 2),
        ("regex_bomb", ("(" * 200 + ")" * 200,) * 2),
        ("huge_number", ("budget around $" + "9" * 400,) * 2),
        ("negative_budget", ("For that, what matters is: budget around $-50.",) * 2),
        ("mixed_scripts", ("中文 русский عربي",) * 2),
        ("lone_surrogate_escape", ("text \\ud800 more",) * 2),
        ("very_many_separators", ("For that, what matters is: " + "; ".join(["x"] * 60) + ".",) * 2),
    ]
    cases = []
    for index, (name, script) in enumerate(hostile[:FAMILY_SIZE]):
        products, target = catalogs.degenerate_catalog("no_prices", index)
        cases.append(Case(
            case_id=f"f6_hostile_{index:02d}_{name}",
            family="hostile_input",
            products=products,
            target=target,
            messages=script,
            checks=("contract", "no_exception"),
        ))
    return cases


def _override_cases() -> list[Case]:
    """F7 - intent override, in both the simulator's shape and a real one.

    Even-numbered cases mirror the official simulator, where the abandoned
    value is drawn from the target's own card and so stays true of it.
    Odd-numbered cases are a genuine override: the abandoned preference
    describes a different product, and carrying it forward can only mislead.
    """
    cases = []
    for seed in range(FAMILY_SIZE):
        contradictory = bool(seed % 2)
        products, target = catalogs.override_family(seed, contradictory)
        card_of_old = products[1]["features"][0] if contradictory else products[0]["details"]["Spec"]
        new_value = products[0]["features"][0]
        cases.append(Case(
            case_id=f"f7_override_{seed:02d}_{'real' if contradictory else 'sim'}",
            family="override",
            products=products,
            target=target,
            scenario_type="intent_override",
            override={
                "turn": 3 + (seed % 2),
                "old_value": card_of_old,
                "new_value": new_value,
                "message": f"Actually, ignore my earlier preference. What I need is: {new_value}.",
            },
            checks=("contract", "no_exception", "hit", "rank"),
            max_rank=1,
        ))
    return cases


def _degenerate_cases() -> list[Case]:
    """F8 - catalogs that violate the shape the agent assumes.

    Missing ratings, missing prices, no features at all, empty strings,
    duplicate ids, a one-row catalog. The agent must still answer, and must
    still answer with ten valid ids when it has ten to give.
    """
    kinds = ("no_ratings", "no_prices", "single", "no_features", "empty_strings",
             "unicode", "long_text", "duplicate_ids")
    cases = []
    for index in range(FAMILY_SIZE):
        kind = kinds[index % len(kinds)]
        products, target = catalogs.degenerate_catalog(kind, index)
        checks = ["contract", "no_exception", "nonempty"]
        cases.append(Case(
            case_id=f"f8_degenerate_{index:02d}_{kind}",
            family="degenerate",
            products=products,
            target=target,
            scenario_type="browsing",
            always_reveal=True,
            # Half the cases skip reset() entirely, which is the path into the
            # agent's last-resort fallback list.
            skip_reset=bool(index % 2),
            checks=tuple(checks),
        ))
    return cases


def all_cases() -> list[Case]:
    cases = (
        _separator_cases() + _lookalike_cases() + _boundary_cases()
        + _wide_category_cases() + _paraphrase_cases() + _hostile_input_cases()
        + _override_cases() + _degenerate_cases()
    )
    assert len(cases) == 8 * FAMILY_SIZE, len(cases)
    assert len({c.case_id for c in cases}) == len(cases), "duplicate case id"
    return cases
