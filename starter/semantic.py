"""Self-trained latent semantic index over the catalog (numpy only).

We train a dense retrieval model on the competition's own data: TF-IDF over
the 50k catalog documents, factorized with randomized SVD into a 128-dim
latent space (classic LSA — learned semantic embeddings, no external models,
no network). Free-form queries embed into the same space and match products
by meaning rather than exact phrase overlap.

Built lazily on first free-form query and cached to disk, so the evaluator's
deterministic path never pays the training cost.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

TOKEN_RE = re.compile(r"[a-z0-9]+")
DIMS = 128
OVERSAMPLE = 32
POWER_ITERATIONS = 2
MAX_VOCAB = 40000
MIN_DF = 3
FIELDS = ("title", "features", "details", "description", "categories")


def _tokenize(text: str) -> list[str]:
    return [t for t in TOKEN_RE.findall(text.lower()) if len(t) > 2]


def _document_text(product: dict) -> str:
    parts: list[str] = []
    for field in FIELDS:
        value = product.get(field)
        if isinstance(value, dict):
            parts.extend(f"{k} {v}" for k, v in value.items())
        elif isinstance(value, list):
            parts.extend(str(v) for v in value)
        elif value is not None:
            parts.append(str(value))
    return " ".join(parts)


class SemanticIndex:
    def __init__(self, catalog_path: str | Path, cache_path: str | Path | None = None):
        import numpy as np

        self.np = np
        catalog_path = Path(catalog_path)
        cache = Path(cache_path) if cache_path else catalog_path.with_suffix(".semantic.npz")
        if cache.exists():
            self._load(cache)
        else:
            # macOS Accelerate emits spurious fp warnings on float32 matmuls;
            # results are validated finite below.
            with np.errstate(all="ignore"):
                self._train(catalog_path)
            if not np.isfinite(self.doc_vecs).all() or not np.isfinite(self.term_vecs).all():
                raise ArithmeticError("semantic training produced non-finite vectors")
            self._save(cache)

    # ---------- training ----------

    def _train(self, catalog_path: Path) -> None:
        np = self.np
        pids: list[str] = []
        docs: list[Counter] = []
        df: Counter = Counter()
        with catalog_path.open(encoding="utf-8") as handle:
            for line in handle:
                product = json.loads(line)
                pids.append(str(product["parent_asin"]))
                counts = Counter(_tokenize(_document_text(product)))
                docs.append(counts)
                df.update(counts.keys())

        n_docs = len(docs)
        vocab_terms = sorted(
            (t for t, d in df.items() if MIN_DF <= d <= n_docs * 0.5),
            key=lambda t: -df[t],
        )[:MAX_VOCAB]
        vocab = {t: i for i, t in enumerate(vocab_terms)}
        idf = np.array(
            [math.log(n_docs / df[t]) for t in vocab_terms], dtype=np.float32
        )

        # Sparse CSR TF-IDF, row-normalized.
        indptr = [0]
        indices: list[int] = []
        data: list[float] = []
        for counts in docs:
            row = [(vocab[t], c) for t, c in counts.items() if t in vocab]
            values = np.array([c for _, c in row], dtype=np.float32)
            cols = np.array([j for j, _ in row], dtype=np.int32)
            weights = (1.0 + np.log(values)) * idf[cols]
            norm = float(np.linalg.norm(weights)) or 1.0
            indices.extend(cols.tolist())
            data.extend((weights / norm).tolist())
            indptr.append(len(indices))
        indptr_arr = np.array(indptr, dtype=np.int64)
        indices_arr = np.array(indices, dtype=np.int32)
        data_arr = np.array(data, dtype=np.float32)

        def matmul(dense):  # A @ dense, A is (n_docs x vocab) CSR
            out = np.zeros((n_docs, dense.shape[1]), dtype=np.float32)
            for i in range(n_docs):
                s, e = indptr_arr[i], indptr_arr[i + 1]
                if s != e:
                    out[i] = data_arr[s:e] @ dense[indices_arr[s:e]]
            return out

        def rmatmul(dense):  # A.T @ dense
            out = np.zeros((len(vocab_terms), dense.shape[1]), dtype=np.float32)
            for i in range(n_docs):
                s, e = indptr_arr[i], indptr_arr[i + 1]
                if s != e:
                    out[indices_arr[s:e]] += data_arr[s:e, None] * dense[i]
            return out

        # Randomized SVD: A ~= (Q @ Ub) @ diag(s) @ Vt
        rng = np.random.default_rng(0)
        sample = rng.standard_normal((len(vocab_terms), DIMS + OVERSAMPLE)).astype(np.float32)
        projected = matmul(sample)
        for _ in range(POWER_ITERATIONS):
            projected = matmul(rmatmul(projected))
        q_basis, _ = np.linalg.qr(projected)
        small = rmatmul(q_basis).T  # (k' x vocab)
        u_small, singular, vt = np.linalg.svd(small, full_matrices=False)

        doc_vecs = (q_basis @ u_small[:, :DIMS]) * singular[:DIMS]
        norms = np.linalg.norm(doc_vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self.doc_vecs = (doc_vecs / norms).astype(np.float32)
        self.term_vecs = vt[:DIMS].T.astype(np.float32)  # (vocab x k)
        self.idf = idf
        self.vocab = vocab
        self.pids = pids

    # ---------- persistence ----------

    def _save(self, cache: Path) -> None:
        self.np.savez_compressed(
            cache,
            doc_vecs=self.doc_vecs,
            term_vecs=self.term_vecs,
            idf=self.idf,
            terms=self.np.array(list(self.vocab.keys())),
            pids=self.np.array(self.pids),
        )

    def _load(self, cache: Path) -> None:
        np = self.np
        blob = np.load(cache, allow_pickle=False)
        self.doc_vecs = blob["doc_vecs"]
        self.term_vecs = blob["term_vecs"]
        self.idf = blob["idf"]
        self.vocab = {t: i for i, t in enumerate(blob["terms"].tolist())}
        self.pids = blob["pids"].tolist()

    # ---------- inference ----------

    def query(self, text: str, top_n: int = 200) -> list[tuple[str, float]]:
        np = self.np
        counts = Counter(t for t in _tokenize(text) if t in self.vocab)
        if not counts:
            return []
        cols = np.array([self.vocab[t] for t in counts], dtype=np.int32)
        values = np.array(list(counts.values()), dtype=np.float32)
        with np.errstate(all="ignore"):
            weights = (1.0 + np.log(values)) * self.idf[cols]
            query_vec = weights @ self.term_vecs[cols]
            norm = float(np.linalg.norm(query_vec))
            if norm == 0:
                return []
            scores = self.doc_vecs @ (query_vec / norm)
        top = np.argpartition(-scores, min(top_n, len(scores) - 1))[:top_n]
        top = top[np.argsort(-scores[top])]
        return [(self.pids[i], float(scores[i])) for i in top if scores[i] > 0]
