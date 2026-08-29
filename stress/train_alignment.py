"""Train the query->product alignment model on synthetic paraphrased dialogues.

Data: for thousands of catalog products (excluding the 200 public-session
targets — no leakage), generate a paraphrased customer dialogue from the
product's own intent card, embed it with the self-trained LSA index, and pair
it with the product's document vector. Fit a ridge-regression alignment
matrix W mapping conversational-query space onto product space; validate on
held-out products by retrieval hit rate.

Usage: python3 -m stress.train_alignment [--samples 20000]
Writes data/catalog.alignment.npz, which the agent loads automatically.
"""
from __future__ import annotations

import argparse
import json
import random

from evaluator.local_evaluator import coarse_category, intent_card, load_jsonl
from starter.semantic import SemanticIndex
from stress.paraphraser import Paraphraser


def synth_dialogue(product: dict, paraphraser: Paraphraser, rng: random.Random) -> str:
    card = intent_card(product)
    category = coarse_category([str(v) for v in product.get("categories") or []])
    constraints = [*card["hard_constraints"], *card["soft_preferences"]]
    seen: set[str] = set()
    constraints = [c for c in constraints if not (c in seen or seen.add(c))]
    parts: list[str] = []
    if rng.random() < 0.5 and constraints:
        first = constraints.pop(0)
        parts.append(paraphraser.render(
            {"type": "initial_buying", "category": category, "constraints": [first]}
        ))
    else:
        parts.append(paraphraser.render(
            {"type": "initial_exploring", "category": category}
        ))
    while constraints:
        chunk, constraints = constraints[:2], constraints[2:]
        parts.append(paraphraser.render({"type": "disclosure", "constraints": chunk}))
    return " ".join(parts)


def main() -> None:
    import numpy as np

    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=20000)
    parser.add_argument("--holdout", type=int, default=2000)
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--dataset", default="data/public_set.jsonl")
    args = parser.parse_args()

    public_targets = {
        str(s["ground_truth"]["parent_asin"]) for s in load_jsonl(args.dataset)
    }
    products: dict[str, dict] = {}
    with open(args.catalog, encoding="utf-8") as handle:
        for line in handle:
            product = json.loads(line)
            products[str(product["parent_asin"])] = product

    index = SemanticIndex(args.catalog)
    pid_row = {pid: i for i, pid in enumerate(index.pids)}
    eligible = [p for p in index.pids if p not in public_targets]
    rng = random.Random(42)
    rng.shuffle(eligible)
    chosen = eligible[: args.samples + args.holdout]

    queries, targets, rows = [], [], []
    for n, pid in enumerate(chosen):
        text = synth_dialogue(products[pid], Paraphraser(seed=n), rng)
        vec = index.embed(text)
        if vec is None:
            continue
        queries.append(vec)
        targets.append(index.doc_vecs[pid_row[pid]])
        rows.append(pid_row[pid])
    queries = np.stack(queries).astype(np.float32)
    targets = np.stack(targets).astype(np.float32)
    split = len(queries) - args.holdout
    q_train, q_val = queries[:split], queries[split:]
    d_train = targets[:split]
    val_rows = np.array(rows[split:])
    print(f"train pairs: {split}  holdout: {len(q_val)}")

    def hit_rate(q_matrix) -> float:
        scores = q_matrix @ index.doc_vecs.T  # (val x n_docs)
        top10 = np.argpartition(-scores, 10, axis=1)[:, :10]
        return float((top10 == val_rows[:, None]).any(axis=1).mean())

    base = hit_rate(q_val)
    print(f"holdout Hit@10 without alignment: {base:.3f}")

    best = (None, base, None)
    for lam in (0.1, 1.0, 10.0):
        gram = q_train.T @ q_train + lam * np.eye(q_train.shape[1], dtype=np.float32)
        weight = np.linalg.solve(gram, q_train.T @ d_train)
        aligned = q_val @ weight
        aligned /= np.linalg.norm(aligned, axis=1, keepdims=True) + 1e-9
        rate = hit_rate(aligned)
        print(f"lambda={lam}: holdout Hit@10 {rate:.3f}")
        if rate > best[1]:
            best = (weight, rate, lam)

    if best[0] is None:
        print("alignment did not beat the raw embedding; not saving")
        return
    out = "data/catalog.alignment.npz"
    np.savez_compressed(out, W=best[0].astype(np.float32))
    print(f"saved {out}  (lambda={best[2]}, holdout Hit@10 {base:.3f} -> {best[1]:.3f})")


if __name__ == "__main__":
    main()
