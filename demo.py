"""Interactive demo: chat with the shopping agent from a terminal.

Usage:  python3 demo.py
Type anything a shopper would say. Simulator-templated sentences hit the
deterministic parser; free-form sentences go through the Claude extraction
layer when ANTHROPIC_API_KEY is set (otherwise they fall back gracefully).
"""
from __future__ import annotations

import json

from starter.agent import Agent


def main() -> None:
    print("Loading catalog and building intent index…")
    agent = Agent("data/catalog.jsonl")
    titles: dict[str, str] = {}
    with open("data/catalog.jsonl", encoding="utf-8") as handle:
        for line in handle:
            product = json.loads(line)
            titles[str(product["parent_asin"])] = str(product.get("title") or "")[:80]

    agent.reset("demo", {"preference_tags": [], "summary": "demo user"})
    state = agent._sessions["demo"]
    print("Ready. Tell me what you're shopping for (Ctrl-C to quit).\n")

    turn = 1
    while True:
        try:
            message = input("you> ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break
        if not message:
            continue
        response = agent.respond("demo", message, turn, 10)
        print(f"agent> {response['message']}")
        print(f"  state: category={state.category!r} constraints={state.constraints}")
        if response["recommendations"]:
            for rank, item in enumerate(response["recommendations"], 1):
                pid = item["parent_asin"]
                print(f"  {rank:2d}. {pid}  {titles.get(pid, '')}")
        else:
            print("  (holding recommendations until I'm confident)")
        turn = min(turn + 1, 10)
        print()


if __name__ == "__main__":
    main()
