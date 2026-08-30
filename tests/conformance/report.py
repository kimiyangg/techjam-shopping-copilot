"""Run the whole conformance corpus and print a per-family summary.

Deliberately free of pytest so the same corpus can be run against any revision
of the agent -- including one checked out in a git worktree -- and the JSON
compared:

    python3 -m tests.conformance.report --json before.json
    python3 -m tests.conformance.report --json after.json --compare before.json
"""
from __future__ import annotations

import argparse
import json
import tempfile
import time
from collections import defaultdict
from pathlib import Path

from tests.conformance.cases import all_cases
from tests.conformance.runner import run_case


def run_all(limit: int | None = None, family: str | None = None) -> dict:
    cases = all_cases()
    if family:
        cases = [c for c in cases if c.family == family]
    if limit:
        cases = cases[:limit]
    started = time.time()
    records = []
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        for case in cases:
            result = run_case(case, tmp)
            records.append({
                "case_id": case.case_id,
                "family": case.family,
                "passed": result.passed,
                "failures": result.failures,
                "hit_turn": result.hit_turn,
                "rank": result.rank,
                "distinct_products_shown": len(result.shown),
            })
    by_family: dict[str, dict] = defaultdict(lambda: {"total": 0, "passed": 0})
    for record in records:
        bucket = by_family[record["family"]]
        bucket["total"] += 1
        bucket["passed"] += int(record["passed"])
    return {
        "total": len(records),
        "passed": sum(r["passed"] for r in records),
        "failed": sum(not r["passed"] for r in records),
        "seconds": round(time.time() - started, 1),
        "by_family": {k: dict(v) for k, v in sorted(by_family.items())},
        "cases": records,
    }


def render(report: dict, compare: dict | None = None) -> str:
    lines = []
    if compare:
        lines.append(f"{'family':<16} {'baseline':>12} {'this run':>12}")
        lines.append("-" * 42)
        old = compare["by_family"]
        for name, stats in report["by_family"].items():
            before = old.get(name, {})
            before_text = (f"{before.get('passed', 0)}/{before.get('total', 0)}"
                           if before else "n/a")
            lines.append(
                f"{name:<16} {before_text:>12} {stats['passed']}/{stats['total']:>10}"
            )
        lines.append("-" * 42)
        lines.append(
            f"{'TOTAL':<16} {compare['passed']}/{compare['total']:>10} "
            f"{report['passed']}/{report['total']:>10}"
        )
    else:
        lines.append(f"{'family':<16} {'passed':>10}")
        lines.append("-" * 28)
        for name, stats in report["by_family"].items():
            lines.append(f"{name:<16} {stats['passed']}/{stats['total']:>8}")
        lines.append("-" * 28)
        lines.append(f"{'TOTAL':<16} {report['passed']}/{report['total']:>8}")
    lines.append(f"\n{report['failed']} failing, {report['seconds']}s")
    if report["failed"]:
        lines.append("\nfirst failure per family:")
        seen = set()
        for record in report["cases"]:
            if record["passed"] or record["family"] in seen:
                continue
            seen.add(record["family"])
            lines.append(f"  {record['case_id']}: {record['failures'][0]}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", help="write the full report here")
    parser.add_argument("--compare", help="a previous --json report to diff against")
    parser.add_argument("--family", help="run only one family")
    parser.add_argument("--limit", type=int, help="run only the first N cases")
    args = parser.parse_args()

    report = run_all(limit=args.limit, family=args.family)
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    baseline = None
    if args.compare:
        baseline = json.loads(Path(args.compare).read_text(encoding="utf-8"))
    print(render(report, baseline))


if __name__ == "__main__":
    main()
