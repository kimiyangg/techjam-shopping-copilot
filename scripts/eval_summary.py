"""Render an evaluator run as a GitHub Actions job summary.

Reads the JSON written by `python3 -m evaluator.local_evaluator` and emits a
Markdown report to $GITHUB_STEP_SUMMARY (stdout when running locally), so the
numbers quoted in README.md / PROJECT_DESCRIPTION.md can always be traced to a
specific CI run instead of a remembered figure.

Usage:  python3 scripts/eval_summary.py [--results results.json]
                                        [--baseline docs/baseline_results.json]
                                        [--min-score 0.90]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Scenario shares of the 200 public sessions, from docs/competition_specification.md.
SCENARIO_SHARE = {"buying": 0.40, "browsing": 0.40, "intent_override": 0.15, "boundary": 0.05}

# Weights from docs/evaluation_config.json; efficiency = clip((11 - mttc) / 10, 0, 1).
WEIGHTS = {"hit_rate_at_10": 0.50, "mrr": 0.30, "efficiency": 0.20}


def fmt(value: float | None, places: int = 3) -> str:
    return "—" if value is None else f"{value:.{places}f}"


def delta(ours: float | None, base: float | None, higher_is_better: bool = True) -> str:
    """Signed change vs. the baseline, with an arrow pointing at 'better'."""
    if ours is None or base is None:
        return "—"
    diff = ours - base
    if abs(diff) < 5e-4:
        return "±0.000"
    improved = diff > 0 if higher_is_better else diff < 0
    return f"{'▲' if improved else '▼'} {diff:+.3f}"


def headline(results: dict, baseline: dict) -> list[str]:
    rows = [
        ("Hit Rate@10", "hit_rate_at_10", True),
        ("MRR", "mrr", True),
        ("MTTC (turns)", "mttc", False),
        ("Efficiency", "efficiency", True),
    ]
    out = [
        "## Public-set evaluation (200 sessions, unmodified official evaluator)",
        "",
        "| Metric | Weight | BM25 starter | This run | Change |",
        "|---|---|---|---|---|",
    ]
    for label, key, higher in rows:
        weight = WEIGHTS.get("efficiency" if key == "mttc" else key)
        weight_text = f"{weight:.0%}" if weight and key != "mttc" else ("20% (via efficiency)" if key == "mttc" else "—")
        out.append(
            f"| {label} | {weight_text} | {fmt(baseline.get(key))} | "
            f"**{fmt(results.get(key))}** | {delta(results.get(key), baseline.get(key), higher)} |"
        )
    ours = results.get("recommended_technical_score")
    base = baseline.get("technical_score")
    out.append(
        f"| **Technical score** | 100% | {fmt(base)} | **{fmt(ours)}** | {delta(ours, base)} |"
    )
    out.append("")
    return out


def per_scenario(results: dict) -> list[str]:
    scenarios = results.get("scenario_metrics") or {}
    if not scenarios:
        return []
    out = [
        "### Per scenario",
        "",
        "Weighted 40 / 40 / 15 / 5 by the track spec — a regression here can hide"
        " inside a flat aggregate, so both are always reported.",
        "",
        "| Scenario | Expected share | Sessions | HR@10 | MRR | MTTC |",
        "|---|---|---|---|---|---|",
    ]
    total = results.get("sample_count") or sum(m.get("sample_count", 0) for m in scenarios.values())
    for name in sorted(scenarios, key=lambda n: -SCENARIO_SHARE.get(n, 0)):
        metrics = scenarios[name]
        count = metrics.get("sample_count", 0)
        share = f"{SCENARIO_SHARE[name]:.0%}" if name in SCENARIO_SHARE else "—"
        actual = f"{count} ({count / total:.0%})" if total else str(count)
        out.append(
            f"| `{name}` | {share} | {actual} | {fmt(metrics.get('hit_rate_at_10'))} | "
            f"{fmt(metrics.get('mrr'))} | {fmt(metrics.get('mttc'), 2)} |"
        )
    out.append("")
    return out


def disclosures(results: dict) -> list[str]:
    """Check the run against the claims made in the submission disclosures."""
    usage = results.get("reported_token_usage") or {}
    tokens = usage.get("total_tokens", 0)
    token_line = (
        f"✅ **{tokens} tokens** — the scored path made zero LLM calls, as disclosed."
        if not tokens
        else f"⚠️ **{tokens} tokens** reported ({usage.get('prompt_tokens', 0)} in / "
        f"{usage.get('completion_tokens', 0)} out). The disclosure claims zero on the "
        "scored path — reconcile before submitting."
    )
    return ["### Disclosure checks", "", token_line, ""]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", default="results.json")
    parser.add_argument("--baseline", default="docs/baseline_results.json")
    parser.add_argument(
        "--min-score",
        type=float,
        default=None,
        help="Exit non-zero if the technical score falls below this (regression gate).",
    )
    args = parser.parse_args()

    results_path = Path(args.results)
    if not results_path.exists():
        print(f"::error::{results_path} not found — did the evaluator run?", file=sys.stderr)
        return 1
    results = json.loads(results_path.read_text(encoding="utf-8"))
    baseline_path = Path(args.baseline)
    baseline = json.loads(baseline_path.read_text(encoding="utf-8")) if baseline_path.exists() else {}

    lines = headline(results, baseline) + per_scenario(results) + disclosures(results)
    lines += [
        "<details><summary>Raw aggregate JSON</summary>",
        "",
        "```json",
        json.dumps({k: v for k, v in results.items() if k != "sessions"}, indent=2),
        "```",
        "",
        "</details>",
        "",
    ]
    report = "\n".join(lines)

    # The report is UTF-8 (arrows, check marks). A Windows console defaults to
    # cp1252 and would raise on them, so widen stdout before printing.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write(report + "\n")
    print(report)

    score = results.get("recommended_technical_score")
    if args.min_score is not None and (score is None or score < args.min_score):
        print(
            f"::error::technical score {fmt(score)} is below the --min-score gate "
            f"of {args.min_score:.3f}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
