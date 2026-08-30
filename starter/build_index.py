"""Build the free-form semantic index ahead of time.

The index is a self-trained LSA model over the catalog (starter/semantic.py).
Training is a multi-minute pure-Python randomized SVD, so it must never run
inside a scored turn — a timeout counts as a miss, and under organizer
paraphrasing every message takes the free-form path, which would put the whole
training cost on turn 1 of session 1.

    python3 -m starter.build_index [--catalog data/catalog.jsonl]

Writes `data/catalog.semantic.npz`, which `Agent` loads (never trains) on the
scored path. Safe to skip: without it the free-form semantic channel simply
stays off and the deterministic engine is unaffected.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from starter.intent_index import catalog_fingerprint


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--force", action="store_true", help="rebuild even if cached")
    args = parser.parse_args()

    catalog = Path(args.catalog)
    if not catalog.exists():
        raise SystemExit(f"catalog not found: {catalog} (see README > Setup)")
    cache = catalog.with_suffix(".semantic.npz")
    if args.force and cache.exists():
        cache.unlink()

    from starter.semantic import SemanticIndex

    started = time.time()
    index = SemanticIndex(catalog, fingerprint=catalog_fingerprint(catalog))
    print(
        f"semantic index ready: {len(index.pids)} products, "
        f"{len(index.vocab)} terms, {time.time() - started:.1f}s -> {cache}"
    )

    alignment = catalog.with_suffix(".alignment.npz")
    if index.load_alignment(alignment):
        print(f"alignment model loaded: {alignment}")
    else:
        print(f"no alignment model at {alignment} (optional; see stress/train_alignment.py)")


if __name__ == "__main__":
    main()
