"""The agent must be constructible from a submission bundle that ships only `starter/`.

docs/submission_rules.md asks for "one Python agent entry file exporting Agent"
plus "any required local helper modules" — not the organizer's evaluator
package. `Agent.__init__` is not covered by the `respond()` fallback, so an
import that resolves only inside this repository turns every session of the
official run into a miss.
"""
from __future__ import annotations

import ast
import json
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

STARTER = Path("starter")


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module)
    return modules


def test_starter_never_imports_the_evaluator():
    offenders = {
        path.name: sorted(m for m in _imported_modules(path) if m.split(".")[0] == "evaluator")
        for path in STARTER.glob("*.py")
    }
    offenders = {name: mods for name, mods in offenders.items() if mods}
    assert not offenders, f"starter/ must not import the evaluator: {offenders}"


def test_agent_constructs_from_a_starter_only_bundle(tmp_path):
    bundle = tmp_path / "submission"
    shutil.copytree(STARTER, bundle / "starter", ignore=shutil.ignore_patterns("__pycache__"))
    catalog = bundle / "catalog.jsonl"
    catalog.write_text(json.dumps({
        "parent_asin": "A1", "title": "Trail Boot",
        "categories": ["Clothing, Shoes & Jewelry", "Women", "Hiking Boots"],
        "features": ["Waterproof leather upper"], "details": {}, "price": 75.99,
        "rating_number": 900,
    }) + "\n", encoding="utf-8")

    script = textwrap.dedent("""
        import json, sys
        from starter.agent import Agent
        agent = Agent("catalog.jsonl")
        agent.reset("s", {"preference_tags": []})
        out = agent.respond("s", "I'm looking for Women Hiking Boots. A key requirement is: leather.", 1, 10)
        print(json.dumps({"asins": [r["parent_asin"] for r in out["recommendations"]]}))
    """)
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=bundle,
        capture_output=True,
        text=True,
        # Empty PYTHONPATH so nothing leaks in from the repo checkout.
        env={"PATH": "", "SYSTEMROOT": "C:\\Windows"},
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["asins"] == ["A1"]
