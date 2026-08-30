# CLAUDE.md

TikTok TechJam 2026 — Track 4 "Shopping Copilot": a headless conversational shopping agent that finds a hidden target product in a frozen 50k Amazon catalog within 10 turns. **Deadline: 1 Sep 2026, 12:00pm SGT (Devpost).**

Read `IDEAS.md` first — it is the master doc (full rules, scoring, scenarios, Q&A rulings, architecture plan). `transcript.md` is the raw webinar source.

## Commands

```bash
# One-time data setup (catalog is gitignored; download from the upstream release)
gzip -dk catalog.jsonl.gz && mv catalog.jsonl data/catalog.jsonl

# Dev/eval extras (the scored path needs none of them)
pip install -r requirements-dev.txt

# Run the full 200-session evaluation → writes results.json (aggregate + per-session)
python3 -m evaluator.local_evaluator

# Tests
python3 -m pytest tests/

# One-time build of the free-form semantic index (optional; never runs in a turn)
python3 -m starter.build_index
```

Python 3.10+, stdlib-only starter. Baseline scores to beat: HR@10 0.125, MRR 0.068, MTTC 9.81 (technical score ~0.107).

## Layout

- `starter/agent.py` — the agent. This is where all our work goes.
- `starter/card_spec.py` — vendored copy of the evaluator's card derivation. **`starter/` must never import `evaluator/`**: the submission bundle ships only `starter/`, and `Agent.__init__` is not covered by the `respond()` fallback, so an unresolvable import scores 0. Enforced by `tests/test_submission_bundle.py`; parity with the evaluator by `tests/test_card_spec_parity.py`.
- `evaluator/local_evaluator.py` — official evaluator. **Never modify** (final scores must come from the unmodified evaluator); same for `data/public_set.jsonl` labels.
- `data/catalog.jsonl` — 50k products, untracked. `data/public_set.jsonl` — 200 dev sessions.
- `docs/` — API contract (JSON schema), competition spec, submission rules, evaluation config.

## Hard rules

- Scoring: 50% HitRate@10, 30% MRR, 20% efficiency (`clip((11-MTTC)/10,0,1)`); exact `parent_asin` match; miss = 11 turns. Metrics reported per scenario (buying 40% / browsing 40% / intent_override 15% / boundary 5%) — never let override/boundary regress silently.
- `respond()` must always return `message`, `ask_attribute`, `recommendations` (ordered ASIN list, top_k always 10). Exceptions/malformed output/timeouts count as misses — wrap everything, always return a valid fallback list.
- Always recommend every turn, even when asking a clarification (a hit stops the session). The reveal gate is the one deliberate exception — it trades a silent turn for MRR — and is capped at `MAX_WITHHOLD_TURNS` (2).
- A slate that did not end the session proves those 10 products are not the target (except before an intent override lands). Retire them and show 10 fresh ones — never re-show a failed slate.
- Intent override: REPLACE contradicted slots, never append — "contradicted" is decided by the catalog (no single card holds both values), not by assuming it. Boundary: "no preference" locks the attribute — never re-ask it.
- Nothing may train, download, or call the network inside `respond()`; a timeout counts as a miss. Model building goes in `starter/build_index.py` / `Agent.prewarm_semantic()`.
- Price is a soft preference (never hard-filter on it); ratings are weak popularity signals.
- No secrets in the repo (LLM keys via env vars). Pretrained models/prebuilt indexes allowed but must be disclosed and reproducible; large assets via download instructions, not committed.

## Git

- `origin` = kimiyangg/techjam-shopping-copilot (private until submission; make public before the deadline). `upstream` = TechJam2026/techjam-conversational-search — pull from it for organizer evaluator/template updates.
- Do not add Claude attribution (Co-Authored-By etc.) to commit messages.
