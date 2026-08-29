# TikTok TechJam 2026 — Track 4: Shopping Copilot — Master Doc

The single reference for our whole development process. Merged from: official info doc (bit.ly/TikTokTechJam2026Info) and the full 28 Aug Track 4 webinar (`transcript.md` — raw source kept in repo).

---

## 1. Logistics & Deadlines

- **72-hour challenge & submission window: 29 Aug 12:00pm → 1 Sep 12:00pm SGT.** Submission via Devpost only. Late = not considered (repeated with emphasis ~5 times).
- Every team member must register on **both** the [Registration Form](https://bit.ly/TikTokTechJam2026Registration) and [Devpost](https://tiktoktechjam2026.devpost.com/) by 1 Sep 12pm. New members can join up to that same deadline (they must list all teammates on the form). Team changes: email apac-earlycareers@tiktok.com.
- Team of up to 5; students at a Singapore university, graduating Dec 2026+, age 18+. TikTok interns/employees ineligible.
- **Prizes (across ALL tracks, not per track — confirmed in Q&A):** 1st SGD 15,000 · 2nd 8,000 · 3rd 5,000 · 4th/5th 3,000 · People's Choice 500.
- **People's Choice:** public Devpost voting. PDF says 1–4 Sep 3pm; webinar said (twice) **1 Sep 3pm → 7 Sep 3pm** — verify on Devpost. One vote per person per project; bots/incentivized votes = disqualification.
- **Top 12 teams** → Grand Final, 11 Sep (Fri) 9am–6pm, TikTok Singapore office, in-person expected. Finalists announced 8 Sep, winners 15 Sep.
- Existing projects allowed only if "significantly updated" — ours is new anyway.
- Support: Telegram @TikTokTechJam2026, email apac-earlycareers@tiktok.com (no reply guaranteed). They explicitly encourage **writing down assumptions** when the spec is ambiguous.
- Track owner / judge: **Chenxin Liu**, Search Algorithm Engineer, Global E-Commerce Search (NUS AI grad, joined TikTok June 2026). Her closing 3 lines: **ask better questions · remember customer intents · rank the product earlier.**

## 2. Judging Criteria (project-level, on top of the technical score)

| Criterion | Weight | What judges look for |
|---|---|---|
| Technical Execution | 35% | Well-structured code, thoughtful architecture, effective API/model use, demo runs reliably, deliberate technical complexity |
| Innovation & Problem Insight | 20% | Originality of idea AND approach; sharpness of problem framing — why it matters, how directly the solution addresses it |
| Impact & Relevance | 20% | Real value to users/stakeholders, reach beyond the hackathon prompt |
| Feasibility & Practicality | 15% | Buildable beyond prototype; proportionate resource use; architecture holds under real-world conditions |
| Presentation & Communication | 10% | Final event only: coherent story problem→solution→potential, deep answers to questions |

⚠️ Discrepancy: the Track 4 speaker read 35/25/25/15/10 in both her sessions; hosts and the written doc say 35/20/20/15/10. Trust the written problem statement, but note innovation/impact may be weighted heavier by this track's judge.

Implication: the leaderboard TechnicalScore is not everything — problem framing, story, and "value beyond the prompt" are ~40% of judging. Budget time for the write-up and demo.

## 3. The Problem

Normal product search: one query in, one list out. Real shopping isn't — "I need shoes for a trip" says the category but not use case, material, or budget. Details emerge gradually; customers change their minds after seeing results.

**The agent's four jobs:**
1. **Search** the catalog.
2. **Ask** a useful question when important information is missing.
3. **Remember** the customer's *active* preferences.
4. **Re-rank** when new information arrives.

**Core philosophy (stated repeatedly):** the goal is NOT a long conversation — it's **better evidence for search**. A strong agent asks only when the expected value of the answer is high. The agent is not rewarded for talking more; it's rewarded for finding the target earlier and ranking it higher.

**Worked example from the talk:** "I need shoes for a trip" → weak system returns 10 popular shoes immediately. Strong agent identifies the missing info that would change the result → asks about walking distance / material / budget → customer: "water-resistant, comfortable, under $80" → agent stores {use case, comfort, water-resistant, budget}, retrieves a smaller candidate set, re-ranks against all active constraints.

**Difficulty ladder (why clothing/shoes/jewelry was chosen):** products differ by material, fit, style, color, brand, use case, size, price — one good question massively cleans up a vague request. Beginners can serve well-described products; strong teams win on ambiguous requests, changing preferences, subtle ranking.

**Stated skill floor/ceiling:** a beginner team can build a valid entry with BM25 + simple state tracking; a stronger team wins by asking better questions, representing intent more accurately, and ranking more effectively.

## 4. Benchmark Data

**Provenance pipeline (deterministic, frozen, checksummed):**
1. Amazon Reviews 2023 (McAuley Lab, UCSD) — real product metadata + real purchase/review records. Official **Clothing 5-core leave-last-out** split: earlier eligible purchases → safe anonymous aggregate profile; final purchase → hidden target.
2. 2,524,981 official records → joined against the frozen 50,000-product catalog; target must exist in catalog and have enough pre-target history → **10,187 eligible records**, **>1,000 distinct candidate targets**.
3. Deterministic selection → **~200 labeled public dev sessions + 800 organizer-only private sessions** (~1,000 total). **Zero user overlap AND zero target overlap** between public/private — the private split is a genuine generalization test, not memorization.

**Conversations are synthetic.** Amazon has no multi-turn shopping dialogues. A **hidden intent card** is derived from the target product + a scenario policy; the **official simulator** answers clarification questions in natural language from that card. Real retrieval evidence + organizer-defined interaction protocol.

**Catalog:** 50,000 products, `catalog.jsonl.gz`, ~19.2 MB compressed (whole participant kit about the same). SHA256 checksum provided — verify after download. Indexable on any laptop, but big enough that guessing/manual rules fail.

**The 10 exposed fields:** `parent_asin, title, features, details, description, categories, store, average_rating, rating_number, price`.
- **title, features, details** = strongest product evidence (organizer's own words).
- **price = soft preference** — missing/inconsistent price must NOT make a product impossible.
- **average_rating / rating_number** = weak popularity/confidence signals only, not relevance.
- Fields have unequal quality/coverage — how to combine them "depends on you"; this is a scored differentiator.
- **parent_asin = parent product**, not a color/size SKU variant. Intent cards derive only from these same exposed metadata records + the scenario policy — no hidden variant attributes.

**Privacy / leakage controls (for our report):** not released: raw user IDs, raw purchase histories, review text, timestamps. Organizer-only: 800 private labels, intent cards, simulator states, split manifest, source data. Automated checks: hidden target never in visible history; intent-card fields excluded from released data; public labels can't reappear as private answers.

## 5. Agent Interface Contract

Plain **Python** interface — no hosted API, no network port. The evaluator imports and runs our code locally, in **our own environment** (we run final eval ourselves).

- `reset(session_id, anonymous_profile)` — new session, gives the anonymous aggregate profile.
- `respond(latest_customer_message, turn_number, top_k)` → response with four possible fields:
  - `message` — customer-facing natural-language text
  - `ask_attributes` — which preference type we want the simulator to clarify (simulator answers via a **deterministic attribute-response policy**, incl. repeat/other requests and preference vs. additional-preference distinction)
  - `recommendations` — **ordered** list of parent ASINs. List order = ranking. Numeric scores ignored. Duplicates and catalog-invalid IDs are removed; evaluator keeps the first K valid unique IDs.
  - `usage` — optional prompt/completion token counts (cost recorded, kept separate from score)

**Hard rules:**
- Exceptions, malformed output, timeouts → count as **misses**. Wrap everything; never crash; always return a valid list.
- **We may ask AND recommend in the same turn.** Always return a full ranked list every turn — a hit while clarifying is free.
- Intent-override sessions **cannot end before the changed preference has been revealed** — no lucky early hit skips the override test.

## 6. Evaluator Loop & Scoring

**Session loop:** evaluator calls `reset` → simulator sends next customer message (per scenario policy + intent card) → agent returns reply / optional ask_attributes / ranked list → evaluator validates, compares by **exact parent-ASIN match** → on hit: records rank + first-hit turn, session stops → on miss: simulator reveals only what policy allows, next turn → **hard limit 10 turns**, miss after turn 10 ends session.

Separation of powers: simulator controls disclosure, agent controls questions+recommendations, evaluator controls correctness. **No LLM ever judges correctness** — deterministic, fast, cheap.

**TechnicalScore over the 800 private sessions:**

| Metric | Definition | Weight |
|---|---|---|
| **Hit Rate@10** | target anywhere in top 10 (the most important metric) | **50%** |
| **MRR** | reciprocal rank of hit: rank 1 → 1.0, rank 4 → 0.25 | **30%** |
| **Efficiency** | from MTTC (mean turns to conversion); no-hit session = 11; converted to 0–1 | **20%** |

Worked example: target at rank 4 on turn 2 → hit=1, RR=0.25, first-hit turn=2.

- Metrics also **reported per scenario** (buying/browsing/override/boundary) — a weak behavior can't hide in the average.
- Final reported results must come from the **unmodified official evaluator** — same metric formulas, stopping rules, invalid-output handling, timeout behavior as released. Any evaluator/template updates will be published before the deadline and apply to everyone.
- Private simulator messages follow the **released templates** + deterministic policy; no undisclosed paraphrases.
- Cost/token info collected but separate from the core score (still feeds Feasibility judging — keep it proportionate).

**Starter baseline to beat** (BM25, Python stdlib only, no LLM, no state, no clarification — deliberately weak):

| Hit Rate@10 | MRR | MTTC | TechnicalScore |
|---|---|---|---|
| ~12.5% | ~0.06 | ~9.81 | ~0.1 |

They will NOT publish stronger baseline numbers — our measured improvement over the starter is the story we tell.

## 7. The Four Simulator Scenarios (same proportions in public & private)

| Scenario | Share | Required behavior |
|---|---|---|
| **Buying** | 40% | A hard constraint arrives early → retrieval quality matters immediately |
| **Browsing** | 40% | Vague opening → choose a *useful* clarification question instead of guessing |
| **Intent override** | 15% | At turn 2–4 a preference changes (black→white, running→casual sneakers) → **REPLACE the old slot, never append**. Session can't end before the override is revealed |
| **Boundary** | 5% | "No preference" for a requested attribute → accept and move on; don't repeat the question, don't invent a constraint |

**The override failure mode she spent the most time on:** a weak agent appends and searches for *black, white, running, casual* simultaneously → contradictory constraints → retrieval collapses. Strong agent: recognize the correction, update color+style, rewrite the query, re-rank on **active intent only**. Acceptable methods: structured slots, recency-aware extraction, or an LLM-based state updater — method open, behavior explicit and testable.

## 8. Scope & Q&A Rulings

**In scope:** keyword search, embeddings, hybrid retrieval, query rewriting, semantic re-ranking, conversation state, clarification strategies.

**Out of scope:** UI (headless eval only), training/full fine-tuning of large models, image processing, payments, catalog mutation/mock ASIN injection, deployed vector-DB clusters (must run in-memory), production infrastructure.

**Constraints:** max 10 turns (exceed = zero for the session); catalog read-only/static; inputs are pre-cleaned text (no typo/ASR handling needed); sessions are isolated single-user (no concurrency).

**Q&A rulings (from the collected-questions doc, answered live):**
- **Pretrained models + prebuilt index artifacts (FAISS etc.) allowed** — must be disclosed and reproducible. No package size limit, but large assets via documented download instructions, not committed to the repo. Precomputed sidecar artifacts do NOT need rebuilding at startup.
- **External LLM APIs with network access allowed**; local models fine; non-LLM approaches fine. A paid LLM is NOT required. Our keys, our rate limits, our costs — never publish secrets.
- **Upstream Amazon Reviews 2023 / other public corpora allowed for preprocessing** with disclosure — but must not be used to reconstruct hidden evaluation labels, and every final recommendation must be a valid parent ASIN in the frozen catalog.
- **Python** for the agent; CPU or GPU for ANN/embeddings — free choice.
- Private evaluator = released evaluator (same ask-attribute policy, templates, rules).

**Resources:**
- Repo: https://github.com/TechJam2026/techjam-conversational-search
- Participant kit: https://github.com/TechJam2026/techjam-conversational-search/releases/tag/participant-kit
- Upstream data docs: https://amazon-reviews-2023.github.io/ (no need to download upstream — kit is self-contained)

---

## 9. Brainstorming — Architecture & Ideas

### Proposed architecture

```
customer msg ──► State Updater ──► active slots ──► Query Builder ──► Hybrid Retrieval ──► Re-ranker ──► top-10
                     │                                   (BM25 + dense + filters)              ▲
                     └──► Clarification Policy ──► ask_attributes ────────────────────────────┘
                            (only when EV of asking is high)
```

### Component options (pick per measurement, not per vibe)

**a) Retrieval (drives Hit Rate@10, 50% of score — highest priority)**
- Index title+features+details (weighted; those three are the strongest evidence per organizer).
- Hybrid: BM25 (rank_bm25 or custom) + dense embeddings (small sentence-transformer, precomputed catalog embeddings shipped as sidecar artifact) + category filter. Fuse with RRF (reciprocal rank fusion) — simple, robust, no tuning data needed.
- Query rewriting: build the query from **active slots**, not raw dialog history (this is what makes override handling automatic downstream).
- Hard vs. soft constraints: category/type can hard-filter; **price and ratings must stay soft** (score boosts/penalties, never elimination — explicit organizer guidance).

**b) Dialog state (drives override 15% + boundary 5% + enables everything else)**
- Structured slot dict: {category, use_case, material, color, style, size, budget, brand, ...}.
- LLM-based state updater per turn: input = current slots + new message → output = updated slots. Prompt explicitly: REPLACE on contradiction (recency wins), mark "no_preference" as a locked state (never re-ask, never invent).
- Fallback non-LLM path: recency-aware regex/keyword extraction — keep as a degradation path and an ablation for the report.

**c) Clarification policy (drives MTTC 20% + browsing 40%)**
- Ask only when it pays: estimate candidate-pool entropy over attribute values (e.g., if top-200 candidates split broadly on color/use-case, that attribute has high information value). Ask the attribute with highest expected pool reduction.
- If pool is already small/confident → don't ask, just rank.
- Respect boundary rule: attribute answered "no preference" → locked, move on.
- **Always attach a full top-10 list even when asking** (free hit chance; also insurance because a hit stops the session and caps MTTC).

**d) Re-ranking (drives MRR 30%)**
- LLM re-ranker over top-N (~30–50) candidates against all active slots each turn: listwise or scoring prompt, then order by score. Cheap model is fine (deterministic correctness means we only need good ordering, and cost is tracked but unscored).
- Non-LLM fallback: cross-encoder or weighted field-match scoring.
- Use the anonymous profile as a weak prior (it exists for "safe personalization") — e.g., historical category/price affinity nudges.

### Strategy insights (from the mechanics)

- A hit **stops the session** — so front-load ranking quality; every turn without a list is a wasted MTTC turn.
- Miss = 11 turns for MTTC; exceptions/timeouts = misses → defensive engineering is directly worth score: try/except everything, timeout guards on LLM calls, always emit a valid fallback list (e.g., last good ranking or BM25 top-10).
- Per-scenario reporting means we must build a per-scenario dashboard from day 1 and never let override/boundary regress silently.
- Public 200 sessions are our only labeled feedback; private set has disjoint users AND targets → don't overfit session-specific tricks; prefer behaviors that generalize (the whole design punishes memorization).
- Determinism of the simulator (fixed templates + policy) means local scores should transfer well — trust the local evaluator.

### Risks / open questions

- LLM latency vs. timeout behavior — need to know the evaluator's timeout budget (check kit config).
- What exactly `ask_attributes` accepts (enumerated attribute types?) — read the API contract in the kit.
- Embedding model choice/size vs. "proportionate resource use" (Feasibility criterion) — small model preferred; document cost.
- How the anonymous profile is structured — inspect the 200 dev sessions.
- Verify People's Choice window and judging-weight discrepancy against Devpost.

### Report/demo angles (for the 40% non-technical judging)

- Frame as: "clarification as information gain" — a principled, measurable idea, not just plumbing.
- Ablation table: baseline → +hybrid retrieval → +state machine → +clarification policy → +re-ranker, each with HR@10/MRR/MTTC per scenario. This is the single most convincing artifact we can produce.
- Impact story: maps directly to TikTok Shop conversational commerce (the speaker's own team); fewer turns = less user friction = higher conversion.

## 10. Deliverables Checklist

- [ ] **Devpost written description**: how the solution addresses the problem; dev tools; APIs; libraries/frameworks; datasets/assets
- [ ] **Public GitHub repo**: structured, commented code; README with overview, setup, repro steps, limitations + what we'd improve, team member contributions
- [ ] **~3-min demo video**, public YouTube, linked on Devpost. Headless walkthrough (API usage / evaluator runs / result analysis) explicitly acceptable for this track; format is our call — whatever conveys the solution best
- [ ] Final numbers from the **unmodified official evaluator**, run in our environment
- [ ] Disclose all pretrained models, prebuilt indexes, external data; large assets via download instructions
- [ ] No secrets in repo/history (LLM keys via env vars)

## 11. Development Plan

**Day 0 (now):**
- [ ] Clone repo + participant kit; verify catalog SHA256
- [ ] Run the official evaluator on the starter agent end-to-end; reproduce ~12.5% / 0.06 / 9.81
- [ ] Read the kit's API contract (`ask_attributes` values, timeout config, profile schema); inspect the 200 dev sessions
- [ ] Build the per-scenario results dashboard/script

**Day 1:**
- [ ] Hybrid retrieval (BM25 + dense + RRF) with slot-built queries → measure
- [ ] Slot state updater (LLM + fallback) with replace/lock semantics → measure override + boundary scenarios specifically

**Day 2:**
- [ ] Clarification policy (entropy-based attribute selection) → measure MTTC/browsing
- [ ] LLM re-ranker on top-N → measure MRR
- [ ] Hardening: try/except everywhere, timeouts, fallback list; run full 200-session eval repeatedly

**Day 3 (submit by 12pm on 1 Sep!):**
- [ ] Ablation runs + results table
- [ ] README, Devpost write-up, demo video
- [ ] Final clean run with unmodified evaluator; freeze numbers; submit with buffer time
