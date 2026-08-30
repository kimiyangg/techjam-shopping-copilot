"""Pytest front end for the black-box conformance corpus.

200 cases, one test each, driving the agent through nothing but its public
contract and the unmodified evaluator's own message helpers. See
`tests/conformance/__init__.py` for why this exists alongside the unit tests,
and `tests/conformance/cases.py` for what each family asserts.

Run the corpus standalone (any revision, no pytest) with:

    python3 -m tests.conformance.report
"""
from __future__ import annotations

import pytest

from tests.conformance.cases import all_cases
from tests.conformance.runner import run_case

CASES = all_cases()


@pytest.fixture(scope="module")
def corpus_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("conformance")


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.case_id)
def test_conformance_case(case, corpus_dir):
    result = run_case(case, corpus_dir)
    if result.failures:
        detail = "\n".join(f"  - {f}" for f in result.failures)
        pytest.fail(
            f"{case.case_id} ({case.family}) violated {len(result.failures)} "
            f"invariant(s):\n{detail}\n"
            f"  hit_turn={result.hit_turn} rank={result.rank} "
            f"distinct_products_shown={len(result.shown)}"
        )


def test_corpus_is_two_hundred_distinct_cases():
    assert len(CASES) == 200
    assert len({c.case_id for c in CASES}) == 200
    assert len({c.family for c in CASES}) == 8


def test_corpus_touches_no_private_agent_api():
    """The corpus must run unchanged against any revision of the agent."""
    import ast
    from pathlib import Path

    for path in [*Path("tests/conformance").glob("*.py"), Path("tests/test_conformance.py")]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
                if isinstance(node.value, ast.Name) and node.value.id in {"agent", "index"}:
                    pytest.fail(f"{path}: touches private attribute {node.attr}")
