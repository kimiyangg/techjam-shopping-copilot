"""Interactive demo: chat with the shopping agent from a terminal.

Usage:  python3 demo.py
Type anything a shopper would say. Simulator-templated sentences hit the
deterministic parser; free-form sentences are resolved by verbatim key
recovery, then the self-trained semantic index, then the Claude extraction
layer when ANTHROPIC_API_KEY is set (each degrades gracefully).
"""
from __future__ import annotations

import json

from starter.agent import Agent


def main() -> None:
    print("Loading catalog and building intent index…")
    agent = Agent("data/catalog.jsonl")
    agent.always_reveal = True  # demo UX: always show the list; the evaluator keeps the gate
    print("Preparing the free-form semantic index (one-time, may take a minute)…")
    print("  semantic index:", "ready" if agent.prewarm_semantic() else "unavailable (numpy missing?)")
    titles: dict[str, str] = {}
    with open("data/catalog.jsonl", encoding="utf-8") as handle:
        for line in handle:
            product = json.loads(line)
            titles[str(product["parent_asin"])] = str(product.get("title") or "")[:80]

    agent.reset("demo", {"preference_tags": [], "summary": "demo user"})
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
        state = agent.session_state("demo")
        print(f"agent> {response['message']}")
        if state is not None:
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
