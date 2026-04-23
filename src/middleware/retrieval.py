"""
Similarity retrieval over the chunk index (Q5 / Round 7 Trident).

Takes a query string, embeds it, and returns the top-K chunks from a
project ranked by cosine similarity against the stored embeddings. Uses
numpy for the dot product; no sqlite-vss required.

Design trace:
  Q5 (Trident Round 7): cosine similarity via MiniLM/text-embedding-3-small.
  Q9 (Lumen Round 7):   chunks are per $ID-tagged journal entry.
  Q12 (Lodestar Round 7): retrieval augments the compressed-tier prompt-
      prefix; this module produces the raw top-K list. Tier selection
      is the caller's concern.

Chunks whose `embedding` column is NULL (embedding failed at upsert time,
or API key absent) are filtered out before scoring — they cannot be ranked.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

from middleware.agent_config import AgentConfig, load_config
from middleware.embedder import EmbedError, embed_text, unpack_float32
from middleware.summary_index import Chunk, list_chunks


@dataclass
class RetrievalHit:
    chunk: Chunk
    score: float

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk.chunk_id,
            "project": self.chunk.project,
            "entry_type": self.chunk.entry_type,
            "from_agent": self.chunk.from_agent,
            "content": self.chunk.content,
            "token_count": self.chunk.token_count,
            "score": self.score,
        }


def _cosine_similarity_matrix(query: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Return a 1-D array of cosine similarities of `query` against each row of
    `matrix`. Zero-vectors map to 0.0 to avoid divide-by-zero. `query` is
    (D,); `matrix` is (N, D); returns (N,).
    """
    q_norm = np.linalg.norm(query)
    if q_norm == 0:
        return np.zeros(matrix.shape[0], dtype=np.float32)
    row_norms = np.linalg.norm(matrix, axis=1)
    dots = matrix @ query
    denom = row_norms * q_norm
    out = np.zeros_like(dots, dtype=np.float32)
    nonzero = denom > 0
    out[nonzero] = dots[nonzero] / denom[nonzero]
    return out


def retrieve(
    query: str,
    project: str,
    db_path: Path | str,
    top_k: Optional[int] = None,
    config: Optional[AgentConfig] = None,
    client: object = None,
    env: Optional[dict] = None,
) -> list[RetrievalHit]:
    """Return the top-K chunks most similar to `query` for `project`.

    `client` is forwarded to embed_text so tests can inject a mock embedder
    without hitting the real OpenAI API. `config` defaults to the repo-root
    agent_config.json; `top_k` defaults to the config's retrieval.top_k.
    Returns an empty list when the index has no embedded chunks for the
    project, when the query itself cannot be embedded, or when top_k <= 0.
    """
    if not query or top_k == 0:
        return []

    cfg = config or load_config()
    k = top_k if top_k is not None else cfg.retrieval.top_k
    if k <= 0:
        return []

    # Embed the query. A missing API key or network failure short-circuits
    # to empty rather than bubbling up — callers are expected to fall back
    # to raw-last-N per Q8.
    try:
        q_blob = embed_text(query, config=cfg, client=client, env=env)
    except EmbedError:
        return []

    query_vec = np.asarray(unpack_float32(q_blob), dtype=np.float32)
    target_dim = int(query_vec.shape[0])

    # Enumerate chunks with non-null embeddings.
    rows = list_chunks(db_path, project=project)
    candidates = [c for c in rows if c.embedding]
    if not candidates:
        return []

    # Unpack one at a time so a single corrupt blob doesn't kill the query,
    # and filter by target dim so a stale embedder-config doesn't either.
    kept_chunks: list[Chunk] = []
    kept_vecs: list[list[float]] = []
    for c in candidates:
        try:
            v = unpack_float32(c.embedding)
        except (ValueError, TypeError):
            continue
        if len(v) != target_dim:
            continue
        kept_chunks.append(c)
        kept_vecs.append(v)

    if not kept_chunks:
        return []

    matrix = np.asarray(kept_vecs, dtype=np.float32)
    embedded = kept_chunks

    scores = _cosine_similarity_matrix(query_vec, matrix)
    # argsort descending; take top K
    order = np.argsort(-scores)[:k]
    return [
        RetrievalHit(chunk=embedded[int(i)], score=float(scores[int(i)]))
        for i in order
    ]
