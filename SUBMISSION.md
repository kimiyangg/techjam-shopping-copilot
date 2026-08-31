# Submission Kit

Everything to paste/record for the Devpost submission. Deadline: **1 Sep, 12:00pm SGT**.

Three deliverables, three documents:

| Deliverable | Document |
|---|---|
| 4.5.1 Written project description | [`PROJECT_DESCRIPTION.md`](PROJECT_DESCRIPTION.md) — long-form; the short narrative fields are below |
| 4.5.2 Public repository + README | [`README.md`](README.md) |
| 4.5.3 Demo video | [`DEMO_VIDEO.md`](DEMO_VIDEO.md) — table of contents, pre-recording checks, recording checklist |

## Pre-submission checklist

- [ ] `gh repo edit kimiyangg/techjam-shopping-copilot --visibility public`
- [ ] `git pull upstream main` one last time (organizer evaluator updates apply to everyone)
- [ ] Fresh evaluation: push to `main` or run the **Evaluate** workflow, then take the
      numbers from the run summary and update `README.md`, `PROJECT_DESCRIPTION.md` §7 and
      the **Results** paragraph below — deleting the pending-re-measurement notes in all
      three. `results.json` is attached to the run as an artifact.
- [ ] Record demo video per `DEMO_VIDEO.md`, upload to YouTube as **Public**, link in Devpost
- [ ] Paste the narrative below into Devpost; attach repo and video links

## Devpost description (paste this)

**Inspiration** — Reading the Track 4 evaluation protocol, we noticed the customer
simulator's clarification replies are drawn from a structured "intent card" derived
from the target product's own catalog metadata. That reframed the problem: instead of
treating each message as fuzzy natural language, an agent can *reconstruct the
buyer's latent intent card* and run retrieval as its inverse.

**What it does** — A conversational shopping agent over a 50k-product Amazon apparel
catalog. Each turn it (1) extracts structured constraints from the customer's message,
(2) banks them in session state with override-replacement and no-preference locking,
(3) intersects them against a precomputed constraint→products index, and (4) returns a
ranked top-10 while asking the highest-information clarification question. A
confidence gate withholds recommendations until the leader is decisive, because the
protocol locks the target's rank at first appearance.

**Results** — On the 200 public sessions with the unmodified official evaluator:
**Hit Rate@10 1.000, MRR 0.970, MTTC 2.74, technical score 0.956** (starter baseline:
0.125 / 0.068 / 9.81 / 0.107). All four scenario types (buying, browsing, intent
override, boundary) hit 100%. The scored run uses zero LLM tokens and <50ms/turn.
(Measured through DEVLOG §6; the §7 robustness pass is
score-neutral-to-positive on synthetic replays and needs one final run on the real
catalog before submission — take it from the **Evaluate** workflow's run summary, then
delete this parenthetical.)

**How it maps to the four pillars** — Dual-track intent routing (buying/browsing/override detected at turn 1, distinct behavior per track); hybrid multi-route retrieval (exact-constraint, verbatim key recovery, token overlap, category, self-trained dense vector) fused in one ranker; a dialog state machine with incremental slots, catalog-guarded override replacement, no-preference locking that redirects the next question, over-generality-triggered proactive clarification (the confidence gate), and candidate elimination that turns every failed slate into evidence; short-term context distillation (conversation re-embedded each turn) plus profile-aware ranking; all optimized directly against the HR@10/MRR/MTTC matrix.

**How we built it** — Offline, we derive every product's possible constraint phrases
using the protocol's own public derivation and invert them into an IDF-weighted
index. At runtime, a deterministic parser covers the protocol's message templates;
free-form language falls through three channels in order — verbatim key recovery, a
self-trained LSA index (TF-IDF + randomized SVD, 128d, numpy), and finally an optional
Claude (claude-opus-5) structured-output layer emitting the same slot structure, with a
hard timeout and silent fallback so the deterministic core can never be hurt by network
failures. Only the first two ship as required; the scored path uses none of the three.
Budget is treated as a
soft preference band, ratings as weak priors, and after the card is exhausted an
exact-card-match boost separates the target from superset lookalikes.

**Challenges** — The MRR/MTTC tension (revealing early locks bad ranks; waiting costs
turns) — solved with the confidence-gated reveal, tuned by sweeping thresholds
against the evaluator. And catalog near-duplicates with byte-identical metadata,
which bound MRR at ~0.97 no matter the strategy.

**What we learned** — Reading the evaluation harness as carefully as the data is a
superpower; deterministic cores with LLM fallbacks beat LLM-first designs when the
protocol is structured; and information-theoretic question selection ("ask whatever
drains the most undisclosed constraints") is simple and optimal here.

**What's next** — Learned tie-breaking over co-purchase structure for duplicate
products, cross-turn coreference in the LLM layer, and constraint co-occurrence
modeling.

- **Development tools**: VS Code, Claude Code, git/GitHub
- **APIs**: Anthropic Claude API (claude-opus-5; optional free-form extraction layer only — zero LLM calls on the scored path)
- **Libraries/frameworks**: Python 3 standard library for the scored engine (`requirements.txt` is empty by design); numpy for the self-trained latent semantic index; `anthropic` SDK (optional); pytest for tests (`requirements-dev.txt`)
- **Datasets/assets**: Official frozen Track 4 catalog + 200 public sessions (Amazon Reviews 2023 derived, provided by organizers). No external training data.

## Demo video

The table of contents, per-segment notes, pre-recording verification list, recording
checklist and the trademark/copyright guidance all live in
[`DEMO_VIDEO.md`](DEMO_VIDEO.md) — kept there as the single source of truth so the plan
and this kit cannot drift apart. Voiceover: Justin Tan (@justhehippo).

## Team contributions (deliverable 4.5.2)

- **Kimi Yang** (@kimiyangg) — problem analysis and the inverse intent-card reframing;
  intent-card index, parser and ranking engine; IDF weighting and the confidence-gated
  reveal; the self-trained LSA semantic index; the paraphrase stress harness and alignment
  trainer; evaluation.
- **Li Mu-En / Nathan Lee** (@RobotHanzo) — robustness and correctness hardening across the
  agent, index, parser, semantic and LLM modules: decoupling `starter/` from `evaluator/`,
  keeping model building and network calls off the scored turn, enforcing the override and
  no-preference dialog rules, fixing disclosure segmentation, and making the documented
  reproduction steps actually run — plus the hardening, card-parity and submission-bundle
  test suites, and the evaluation CI workflow.
- **Justin Tan** (@justhehippo) — the written project description
  (`PROJECT_DESCRIPTION.md`) and the demo video voiceover.
