"""
Tests for the similarity-retrieval module.

The embedder is mocked via the `client` parameter — no real API calls.
The index layer is exercised against a fresh SQLite temp file.
"""

import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from middleware.agent_config import AgentConfig, EmbedderConfig, RetrievalConfig
from middleware.embedder import pack_float32
from middleware.retrieval import (
    RetrievalHit,
    _cosine_similarity_matrix,
    retrieve,
)
from middleware.summary_index import upsert_chunk


def _cfg(dims: int = 3) -> AgentConfig:
    c = AgentConfig()
    c.embedder = EmbedderConfig(provider="openai", model="fake", dims=dims)
    c.retrieval = RetrievalConfig(top_k=3)
    return c


def _client_for(query_vec: list[float]):
    """Build a mock openai client whose embeddings.create returns the given
    query vector. Only used to embed the retrieval query (single input)."""
    def create(model, input):
        return SimpleNamespace(data=[SimpleNamespace(embedding=query_vec)])
    return SimpleNamespace(embeddings=SimpleNamespace(create=create))


def _seed_chunks(db, project, entries):
    """entries: list of (chunk_id, content, embedding_vec_or_None)."""
    for chunk_id, content, vec in entries:
        blob = pack_float32(vec) if vec is not None else None
        upsert_chunk(
            db, chunk_id=chunk_id, project=project,
            entry_type="UPDATE", from_agent="Pharos",
            content=content, embedding=blob,
        )


class TestCosineHelper:
    def test_identical_vectors_score_1(self):
        import numpy as np
        q = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        m = np.array([[1.0, 0.0, 0.0]], dtype=np.float32)
        scores = _cosine_similarity_matrix(q, m)
        assert scores[0] == pytest.approx(1.0, abs=1e-6)

    def test_orthogonal_vectors_score_0(self):
        import numpy as np
        q = np.array([1.0, 0.0], dtype=np.float32)
        m = np.array([[0.0, 1.0]], dtype=np.float32)
        assert _cosine_similarity_matrix(q, m)[0] == pytest.approx(0.0, abs=1e-6)

    def test_zero_query_gives_zero_scores(self):
        import numpy as np
        q = np.array([0.0, 0.0], dtype=np.float32)
        m = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
        scores = _cosine_similarity_matrix(q, m)
        assert list(scores) == [0.0, 0.0]

    def test_zero_row_gives_zero_score(self):
        import numpy as np
        q = np.array([1.0, 0.0], dtype=np.float32)
        m = np.array([[0.0, 0.0]], dtype=np.float32)
        assert _cosine_similarity_matrix(q, m)[0] == 0.0


class TestRetrieve:
    def test_returns_top_k_by_cosine(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "idx.db")
            _seed_chunks(db, "P", [
                ("MSG-0001", "apple",   [1.0, 0.0, 0.0]),  # exact match
                ("MSG-0002", "banana",  [0.0, 1.0, 0.0]),
                ("MSG-0003", "cherry",  [0.9, 0.1, 0.0]),  # close-ish to query
                ("MSG-0004", "durian",  [0.0, 0.0, 1.0]),
            ])
            cfg = _cfg(dims=3)
            client = _client_for([1.0, 0.0, 0.0])
            hits = retrieve("query", "P", db, top_k=2, config=cfg, client=client)
            assert len(hits) == 2
            assert hits[0].chunk.chunk_id == "MSG-0001"
            assert hits[0].score == pytest.approx(1.0, abs=1e-5)
            assert hits[1].chunk.chunk_id == "MSG-0003"

    def test_top_k_defaults_from_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "idx.db")
            _seed_chunks(db, "P", [
                (f"MSG-{i:04d}", f"c{i}", [float(i), 0.0, 0.0])
                for i in range(1, 10)
            ])
            cfg = _cfg(dims=3)
            cfg.retrieval.top_k = 4
            client = _client_for([1.0, 0.0, 0.0])
            hits = retrieve("q", "P", db, config=cfg, client=client)
            assert len(hits) == 4

    def test_empty_query_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "idx.db")
            cfg = _cfg()
            assert retrieve("", "P", db, config=cfg, client=_client_for([1.0, 0.0, 0.0])) == []

    def test_zero_top_k_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "idx.db")
            _seed_chunks(db, "P", [("MSG-1", "x", [1.0, 0.0, 0.0])])
            cfg = _cfg()
            hits = retrieve("q", "P", db, top_k=0, config=cfg, client=_client_for([1.0, 0.0, 0.0]))
            assert hits == []

    def test_no_embedded_chunks_returns_empty(self):
        """When every chunk for the project has a NULL embedding, retrieve
        returns empty — there's nothing to rank."""
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "idx.db")
            _seed_chunks(db, "P", [
                ("MSG-0001", "a", None),
                ("MSG-0002", "b", None),
            ])
            cfg = _cfg()
            hits = retrieve("q", "P", db, config=cfg, client=_client_for([1.0, 0.0, 0.0]))
            assert hits == []

    def test_query_embed_failure_returns_empty(self):
        """EmbedError on the query short-circuits to empty instead of
        bubbling up. The caller falls back to raw-last-N per Q8."""
        class BoomClient:
            class embeddings:
                @staticmethod
                def create(model, input):
                    raise RuntimeError("no api key")

        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "idx.db")
            _seed_chunks(db, "P", [("MSG-1", "x", [1.0, 0.0, 0.0])])
            cfg = _cfg()
            hits = retrieve("q", "P", db, config=cfg, client=BoomClient())
            assert hits == []

    def test_skips_chunks_with_wrong_dim(self):
        """Embedder config changing mid-life leaves old chunks at the old
        dim. Those should be skipped, not crash the query."""
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "idx.db")
            _seed_chunks(db, "P", [
                ("MSG-0001", "match",  [1.0, 0.0, 0.0]),
                ("MSG-0002", "stale",  [0.5, 0.5]),  # 2-dim; wrong
            ])
            cfg = _cfg(dims=3)
            client = _client_for([1.0, 0.0, 0.0])
            hits = retrieve("q", "P", db, top_k=5, config=cfg, client=client)
            # only MSG-0001 survives the dim filter
            assert len(hits) == 1
            assert hits[0].chunk.chunk_id == "MSG-0001"

    def test_project_scoping(self):
        """Chunks in a different project must not leak into results."""
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "idx.db")
            _seed_chunks(db, "ProjA", [("MSG-A1", "a", [1.0, 0.0, 0.0])])
            _seed_chunks(db, "ProjB", [("MSG-B1", "b", [1.0, 0.0, 0.0])])
            cfg = _cfg(dims=3)
            hits = retrieve("q", "ProjA", db, top_k=5, config=cfg,
                           client=_client_for([1.0, 0.0, 0.0]))
            assert {h.chunk.chunk_id for h in hits} == {"MSG-A1"}


class TestRetrievalHit:
    def test_to_dict_shape(self):
        from middleware.summary_index import Chunk
        c = Chunk(
            chunk_id="MSG-1", project="P", entry_type="UPDATE",
            from_agent="Pharos", content="body", token_count=2,
            last_indexed="2026-04-23T00:00:00", embedding=None,
        )
        d = RetrievalHit(chunk=c, score=0.87).to_dict()
        assert d["chunk_id"] == "MSG-1"
        assert d["project"] == "P"
        assert d["score"] == 0.87
