"""
Tests for the RAG chunk index (Q9 + Q11 from the Summarizer-Role design).
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from middleware.summary_index import (
    Chunk,
    init_db,
    upsert_chunk,
    get_chunk,
    list_chunks,
    delete_chunk,
    chunk_count,
)


def _tmpdb(tmpdir: str) -> str:
    return str(Path(tmpdir) / "index.db")


class TestInit:
    def test_init_creates_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _tmpdb(tmp)
            init_db(db)
            assert Path(db).exists()

    def test_init_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _tmpdb(tmp)
            init_db(db)
            init_db(db)  # should not raise
            assert chunk_count(db) == 0


class TestUpsertAndGet:
    def test_insert_new_chunk(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _tmpdb(tmp)
            c = upsert_chunk(
                db,
                chunk_id="MSG-0170",
                project="InterAI-Protocol",
                entry_type="REPORT",
                from_agent="Pharos",
                content="Design lock summary for Rounds 1-6.",
            )
            assert c.chunk_id == "MSG-0170"
            assert c.token_count > 0
            assert c.last_indexed

            loaded = get_chunk(db, "MSG-0170")
            assert loaded is not None
            assert loaded.project == "InterAI-Protocol"
            assert loaded.from_agent == "Pharos"
            assert loaded.content == "Design lock summary for Rounds 1-6."
            assert loaded.embedding is None

    def test_upsert_replaces_on_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _tmpdb(tmp)
            upsert_chunk(db, "MSG-0170", "P", "REPORT", "Pharos", "first content")
            upsert_chunk(db, "MSG-0170", "P", "REPORT", "Pharos", "replacement content")
            loaded = get_chunk(db, "MSG-0170")
            assert loaded.content == "replacement content"
            assert chunk_count(db) == 1

    def test_get_missing_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _tmpdb(tmp)
            assert get_chunk(db, "MSG-9999") is None

    def test_upsert_rejects_empty_chunk_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _tmpdb(tmp)
            try:
                upsert_chunk(db, "", "P", "REPORT", "Pharos", "x")
            except ValueError as e:
                assert "chunk_id" in str(e)
            else:
                raise AssertionError("should have raised ValueError")

    def test_upsert_rejects_empty_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _tmpdb(tmp)
            try:
                upsert_chunk(db, "MSG-1", "", "REPORT", "Pharos", "x")
            except ValueError as e:
                assert "project" in str(e)
            else:
                raise AssertionError("should have raised ValueError")

    def test_embedding_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _tmpdb(tmp)
            emb = b"\x01\x02\x03\x04" * 96  # 384-byte payload, MiniLM-ish
            upsert_chunk(db, "MSG-1", "P", "RESPONSE", "Pharos", "text", embedding=emb)
            loaded = get_chunk(db, "MSG-1")
            assert loaded.embedding == emb


class TestListAndFilter:
    def _seed(self, db: str) -> None:
        upsert_chunk(db, "MSG-0100", "InterAI-Protocol", "REQUEST",  "Don",    "a")
        upsert_chunk(db, "MSG-0101", "InterAI-Protocol", "RESPONSE", "Pharos", "b")
        upsert_chunk(db, "MSG-0102", "InterAI-Protocol", "RESPONSE", "Lumen",  "c")
        upsert_chunk(db, "MSG-0103", "OperatorHub",      "REPORT",   "Pharos", "d")

    def test_list_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _tmpdb(tmp)
            self._seed(db)
            chunks = list_chunks(db)
            assert len(chunks) == 4

    def test_filter_by_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _tmpdb(tmp)
            self._seed(db)
            chunks = list_chunks(db, project="InterAI-Protocol")
            assert len(chunks) == 3
            assert all(c.project == "InterAI-Protocol" for c in chunks)

    def test_filter_by_entry_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _tmpdb(tmp)
            self._seed(db)
            chunks = list_chunks(db, entry_type="RESPONSE")
            assert len(chunks) == 2
            assert all(c.entry_type == "RESPONSE" for c in chunks)

    def test_filter_by_from_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _tmpdb(tmp)
            self._seed(db)
            chunks = list_chunks(db, from_agent="Pharos")
            assert len(chunks) == 2
            assert all(c.from_agent == "Pharos" for c in chunks)

    def test_combined_filters(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _tmpdb(tmp)
            self._seed(db)
            chunks = list_chunks(
                db,
                project="InterAI-Protocol",
                from_agent="Pharos",
            )
            assert len(chunks) == 1
            assert chunks[0].chunk_id == "MSG-0101"

    def test_ordering_by_chunk_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _tmpdb(tmp)
            self._seed(db)
            chunks = list_chunks(db, project="InterAI-Protocol")
            ids = [c.chunk_id for c in chunks]
            assert ids == sorted(ids)


class TestDelete:
    def test_delete_existing_returns_true(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _tmpdb(tmp)
            upsert_chunk(db, "MSG-1", "P", "REPORT", "Pharos", "x")
            assert delete_chunk(db, "MSG-1") is True
            assert get_chunk(db, "MSG-1") is None

    def test_delete_missing_returns_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _tmpdb(tmp)
            assert delete_chunk(db, "MSG-NOPE") is False


class TestChunkCount:
    def test_empty_db_is_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _tmpdb(tmp)
            assert chunk_count(db) == 0

    def test_count_by_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _tmpdb(tmp)
            upsert_chunk(db, "MSG-1", "A", "REPORT", "Pharos", "x")
            upsert_chunk(db, "MSG-2", "A", "REPORT", "Pharos", "y")
            upsert_chunk(db, "MSG-3", "B", "REPORT", "Pharos", "z")
            assert chunk_count(db, project="A") == 2
            assert chunk_count(db, project="B") == 1
            assert chunk_count(db) == 3
