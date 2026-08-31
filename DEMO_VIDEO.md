# Demo Video Plan — Shopping Copilot

**Deliverable 4.5.3.** Companion to [PROJECT_DESCRIPTION.md](PROJECT_DESCRIPTION.md).
Voiceover: Justin Tan ([@justhehippo](https://github.com/justhehippo)). Repository and
YouTube links are submitted separately on Devpost.

## Requirements checklist (from the Track 4 deliverables)

- [ ] Demonstrates the solution working end-to-end — for a backend/NLP track, a walkthrough
      of API usage, inference examples, or result analysis is explicitly accepted, so a
      terminal walkthrough of `demo.py` plus the evaluator is sufficient.
- [ ] Uploaded to **YouTube** with visibility set to **Public** (not "Unlisted").
- [ ] Linked in the Devpost description.
- [ ] Contains no third-party trademarks or copyrighted content used without permission.
      See "Trademark and copyright care" below — this matters here, because the catalog is
      real Amazon product data.
- [ ] Repository is public before the video is submitted.

Recommended length: about three minutes. One clear story:
**problem → insight → working system → measured evidence → practical value.**

## Table of contents

| Time | Segment | What appears on screen | Key message |
|---|---|---|---|
| 0:00–0:20 | Opening problem | A simple slide: 50,000 products, one hidden target, a ten-turn limit. | Ordinary keyword search struggles because the customer's requirements arrive gradually. |
| 0:20–0:45 | Scoring and baseline | HR@10 (50%), MRR (30%), MTTC efficiency (20%), and the starter's 0.107 score. | The agent must find the right product, rank it highly, and do so early. |
| 0:45–1:15 | Core insight | The intent-card derivation in `starter/card_spec.py` (or the evaluator's `intent_card()`), then the architecture diagram `docs/architecture.png`. | The clues come from structured product metadata, so we reconstruct that card and invert the lookup. |
| 1:15–2:05 | Live conversation | Run `python3 demo.py`. Show a buying request, a useful clarification, the saved state line, an override, and a no-preference response. | The agent extracts clues, remembers active preferences, replaces outdated ones, and narrows the candidate set. |
| 2:05–2:25 | Free-form demo | Type a natural request such as "cozy winter sweater" or "gold necklace for a wedding". | The self-trained semantic model handles meaning with no external API and no network. |
| 2:25–2:50 | Results and evidence | Evaluator output: aggregate plus per-scenario metrics, the passing test suite, and the ablation table. | Measured improvement from 0.107 to 0.956 on the public evaluator, 100% HR@10 across all four scenarios. |
| 2:50–3:00 | Close | Repository link and the one-command reproduction. | Deterministic scored core, optional AI generality, fast local execution, reproducible results. |

### Segment notes

**1:15–2:05, live demo.** `demo.py` sets `agent.always_reveal = True` so the list is shown
every turn; mention on camera that the scored evaluator keeps the confidence gate active.
Have this sequence rehearsed:

1. A templated buying opener → instant top 10, with the `state:` line visible.
2. A free-form sentence → matched by meaning, no API call.
3. An override ("forget that — white casual sneakers instead") → point at the `state:` line
   showing the old color replaced rather than appended.
4. A "no preference" reply → point out that the agent never asks that attribute again.

**2:25–2:50, results.** Show both the aggregate and the per-scenario breakdown, not only the
composite score. Quote the numbers from the fresh run, not from the README.

## Pre-recording verification

Do this before recording — the on-screen numbers are claims, and they must match a real run.

- [ ] **Re-measure the score.** `results.json` is not currently in the working tree, and the
      published ablation table predates the `DEVLOG.md` §7 robustness pass. Push to `main`
      (or run the **Evaluate** workflow manually) and read the metric tables off the run
      summary — `.github/workflows/evaluate.yml` runs the unmodified evaluator on the
      checksummed catalog. Then update `PROJECT_DESCRIPTION.md` §7, `README.md`, and
      `SUBMISSION.md` with those figures and remove their pending-re-measurement notes.
      Quote only numbers that appear in a CI run summary.
- [ ] `python3 -m pytest tests/` passes, and the run is recent enough to show on camera.
- [ ] `data/catalog.jsonl` is present (gitignored; download per `PROJECT_DESCRIPTION.md` §11)
      — `demo.py` and the evaluator both fail without it.
- [ ] `starter/llm_layer.py` — confirm the model identifier and timeout shown or spoken match
      the code: `claude-opus-5`, 30-second timeout, no retries, silent fallback.
      (`DEVLOG.md` still says "8s timeout" in its historical entries — that is the log
      recording what was true at the time, not a current claim. Don't read it on camera.)
- [ ] `starter/semantic.py` — confirm TF-IDF, randomized SVD, `DIMS = 128`, lazy init, numpy-only.
- [ ] `starter/agent.py` — confirm session state, `MAX_WITHHOLD_TURNS = 2`, ranking weights, fallback behavior.
- [ ] `starter/parser.py` — confirm the protocol templates, override detection, no-preference
      handling, and the singular `ask_attribute` contract.
- [ ] `starter/intent_index.py` — confirm the card derivation, inverse maps, IDF weighting, and build timing.
- [ ] `evaluator/local_evaluator.py` and `data/public_set.jsonl` are byte-identical to the
      organizer's release.
- [ ] `stress/train_alignment.py` and `stress/harness.py` — confirm the 20,000 / 2,000 split
      and that both commands run.
- [ ] Every behavior demonstrated on screen has a passing test behind it.

## Recording checklist

- [ ] Record at 1080p with a terminal font of at least 16 pt.
- [ ] Run the evaluator and `starter.build_index` once before recording so the index caches are warm.
- [ ] Prepare every terminal command in advance; do not film installation or index-build waits.
- [ ] Show both aggregate and per-scenario results, not only the final composite score.
- [ ] If demonstrating the optional Claude path, export `ANTHROPIC_API_KEY` **before** opening
      the recorded terminal, and never let the key appear on screen (no `env`, no `echo`, no
      shell history scrollback).
- [ ] End on the public repository URL, the setup instructions, and the exact reproduction command.

## Trademark and copyright care

The catalog is real Amazon product data, so the demo output contains third-party brand names,
product titles, and ASINs.

- Keep it to plain terminal text — product titles and ASINs as data, which is what the
  organizer-provided dataset is for. Do not display product **images**, brand logos, or
  scraped Amazon pages.
- Do not use the Amazon logo, TikTok logo, or any brand mark in the slides. Refer to the
  dataset in words ("the organizer-provided Amazon Reviews 2023 catalog").
- Use no background music unless it is your own or explicitly licensed for reuse.
- Do not show any third-party UI or copyrighted screenshot beyond your own code and terminal.

## Post-recording

- [ ] Upload to YouTube, set visibility to **Public**, and confirm it plays in a signed-out browser.
- [ ] Make the repository public: `gh repo edit kimiyangg/techjam-shopping-copilot --visibility public`.
- [ ] Submit both links on Devpost (handled separately from these docs).
- [ ] Confirm submission before **1 Sep 2026, 12:00 pm SGT**.
