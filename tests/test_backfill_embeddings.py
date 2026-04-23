"""
Tests for the backfill_embeddings utility.

Exercises find_missing and backfill against a temp SQLite DB with injected
fake config and mock embedder. No real OpenAI call.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import tempfile

import pytest

from middleware.agent_config import AgentConfig, EmbedderConfig
from middleware.embedder import pack_float32
from middleware.summary_index import list_chunks, upsert_chunk

import backfill_embeddings as bf


def _seed_db(db: str) -> None:
    upsert_chunk(db, "MSG-001", "P", "UPDATE", "Pharos", "content one")
    upsert_chunk(db, "MSG-002", "P", "UPDATE", "Pharos", "content two")
    upsert_chunk(
        db, "MSG-003", "P", "UPDATE", "Pharos", "content three",
        embedding=pack_float32([0.1, 0.2, 0.3]),
    )
    upsert_chunk(db, "MSG-004", "Q", "UPDATE", "Pharos", "other project")


class TestFindMissing:
    def test_finds_chunks_with_null_embedding(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "idx.db")
            _seed_db(db)
            missing = bf.find_missing(Path(db), project=None)
            ids = sorted(c.chunk_id for c in missing)
            assert ids == ["MSG-001", "MSG-002", "MSG-004"]

    def test_project_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "idx.db")
            _seed_db(db)
            missing = bf.find_missing(Path(db), project="P")
            ids = sorted(c.chunk_id for c in missing)
            assert ids == ["MSG-001", "MSG-002"]


class TestBackfillDryRun:
    def test_reports_missing_count_without_api_call(self, monkeypatch):
        def boom(*a, **k):
            raise AssertionError("embedder must not be called on dry-run")
        monkeypatch.setattr(bf, "embed_text_batch", boom)

        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "idx.db")
            _seed_db(db)
            result = bf.backfill(Path(db), project=None, batch_size=32, dry_run=True)
            assert result["dry_run"] is True
            assert result["missing_count"] == 3


class TestBackfillExecutes:
    def test_all_missing_get_embedded(self, monkeypatch):
        def fake_embed(texts, config=None, client=None, env=None):
            return [pack_float32([float(i), 0.0, 0.0]) for i in range(len(texts))]

        # Skip the real API-key probe.
        monkeypatch.setattr(bf, "resolve_api_key", lambda *a, **k: "test-key")
        monkeypatch.setattr(bf, "embed_text_batch", fake_embed)

        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "idx.db")
            _seed_db(db)
            result = bf.backfill(Path(db), project=None, batch_size=32, dry_run=False)
            assert result["embedded"] == 3
            assert result["failed"] == 0

            # Verify the database actually has embeddings now.
            remaining_missing = bf.find_missing(Path(db), project=None)
            assert remaining_missing == []

    def test_batch_failure_counted_not_fatal(self, monkeypatch):
        from middleware.embedder import EmbedError

        def always_fail(texts, config=None, client=None, env=None):
            raise EmbedError("simulated")

        monkeypatch.setattr(bf, "resolve_api_key", lambda *a, **k: "test-key")
        monkeypatch.setattr(bf, "embed_text_batch", always_fail)

        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "idx.db")
            _seed_db(db)
            result = bf.backfill(Path(db), project=None, batch_size=32, dry_run=False)
            assert result["embedded"] == 0
            assert result["failed"] == 3

    def test_missing_api_key_reports_error(self, monkeypatch):
        from middleware.agent_config import MissingApiKey

        def no_key(*a, **k):
            raise MissingApiKey("set OPENAI_API_KEY or add openai_api_key")

        monkeypatch.setattr(bf, "resolve_api_key", no_key)

        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "idx.db")
            _seed_db(db)
            result = bf.backfill(Path(db), project=None, batch_size=32, dry_run=False)
            assert "error" in result
            assert "OPENAI_API_KEY" in result["error"]

    def test_batch_size_respected(self, monkeypatch):
        batches_called = []

        def fake_embed(texts, config=None, client=None, env=None):
            batches_called.append(len(texts))
            return [pack_float32([0.0]) for _ in texts]

        monkeypatch.setattr(bf, "resolve_api_key", lambda *a, **k: "test-key")
        monkeypatch.setattr(bf, "embed_text_batch", fake_embed)

        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "idx.db")
            _seed_db(db)
            # 3 missing chunks, batch size 2 → two batches (2 + 1).
            result = bf.backfill(Path(db), project=None, batch_size=2, dry_run=False)
            assert result["embedded"] == 3
            assert batches_called == [2, 1]
