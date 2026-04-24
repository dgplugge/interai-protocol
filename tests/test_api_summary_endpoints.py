"""
Integration tests for the new summarizer endpoints on api/server.py:

  POST /threads/{project}/retrieve
  POST /threads/{project}/generate-summary
  GET  /threads/{project}/summary-due

The underlying LLM / embedder calls are monkeypatched at the server
module level so the HTTP envelope can be exercised without network.
"""

import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api import server as server_module
from api.server import app

from middleware.summary_index import upsert_chunk
from middleware.summary_meta import record_journal_entry
from middleware.embedder import pack_float32


@pytest.fixture
def isolated_server(monkeypatch, tmp_path):
    summaries = tmp_path / "summaries"
    journals = tmp_path / "journals"
    deploy = tmp_path / "deploy"

    monkeypatch.setattr(server_module, "SUMMARIES_DIR", summaries)
    monkeypatch.setattr(server_module, "INDEX_DB", summaries / "index.db")
    monkeypatch.setattr(server_module, "JOURNALS_ROOT", journals)
    monkeypatch.setattr(server_module, "DEPLOY_ROOT", deploy)
    monkeypatch.setattr(server_module, "sync_to_deploy", lambda p: "skipped-in-test")

    project_dir = journals / "InterAI-Protocol"
    (project_dir / "messages").mkdir(parents=True)
    (project_dir / "journal-index.json").write_text(
        '{"protocol":"AICP/1.0","messages":[],"participants":[]}',
        encoding="utf-8",
    )

    return {
        "client": TestClient(app),
        "summaries": summaries,
        "index_db": summaries / "index.db",
        "journals": journals,
        "project": "InterAI-Protocol",
    }


class TestRetrieve:
    def test_404_on_unknown_project(self, isolated_server):
        r = isolated_server["client"].post(
            "/threads/NoSuchProject/retrieve",
            json={"query": "hello"},
        )
        assert r.status_code == 404

    def test_empty_hits_when_index_is_empty(self, isolated_server, monkeypatch):
        # Stub retrieval to prove the endpoint hands off cleanly.
        monkeypatch.setattr(server_module, "rag_retrieve", lambda **kwargs: [])
        r = isolated_server["client"].post(
            f"/threads/{isolated_server['project']}/retrieve",
            json={"query": "hello"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["project"] == isolated_server["project"]
        assert data["count"] == 0
        assert data["hits"] == []

    def test_hits_serialize_with_scores(self, isolated_server, monkeypatch):
        from middleware.summary_index import Chunk
        from middleware.retrieval import RetrievalHit

        fake_hits = [
            RetrievalHit(
                chunk=Chunk(
                    chunk_id="MSG-0001", project="InterAI-Protocol",
                    entry_type="UPDATE", from_agent="Pharos",
                    content="hello world", token_count=2,
                    last_indexed="2026-04-23T12:00:00",
                ),
                score=0.97,
            ),
            RetrievalHit(
                chunk=Chunk(
                    chunk_id="MSG-0002", project="InterAI-Protocol",
                    entry_type="REPORT", from_agent="Lumen",
                    content="summary text", token_count=2,
                    last_indexed="2026-04-23T12:01:00",
                ),
                score=0.42,
            ),
        ]

        def fake_retrieve(**kwargs):
            assert kwargs["query"] == "find me"
            assert kwargs["project"] == "InterAI-Protocol"
            return fake_hits

        monkeypatch.setattr(server_module, "rag_retrieve", fake_retrieve)
        r = isolated_server["client"].post(
            f"/threads/{isolated_server['project']}/retrieve",
            json={"query": "find me", "top_k": 5},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["count"] == 2
        assert data["hits"][0]["chunk_id"] == "MSG-0001"
        assert data["hits"][0]["score"] == pytest.approx(0.97)
        assert data["hits"][1]["score"] == pytest.approx(0.42)

    def test_top_k_defaults_from_config(self, isolated_server, monkeypatch):
        seen = {}

        def fake_retrieve(**kwargs):
            seen.update(kwargs)
            return []

        monkeypatch.setattr(server_module, "rag_retrieve", fake_retrieve)
        r = isolated_server["client"].post(
            f"/threads/{isolated_server['project']}/retrieve",
            json={"query": "q"},
        )
        assert r.status_code == 200
        # top_k echoed in response comes from agent_config.retrieval.top_k
        assert r.json()["top_k"] == server_module.agent_config.retrieval.top_k


class TestGenerateSummary:
    def test_404_on_unknown_project(self, isolated_server):
        r = isolated_server["client"].post(
            "/threads/NoSuchProject/generate-summary",
            json={},
        )
        assert r.status_code == 404

    def test_successful_generation_returns_tiers(self, isolated_server, monkeypatch):
        from middleware.summary_store import TieredSummary

        def fake_runner(**kwargs):
            assert kwargs["project"] == "InterAI-Protocol"
            s = TieredSummary(full="F", compressed="C", shorthand="S")
            s.touch()
            return s

        monkeypatch.setattr(server_module, "run_summary_generator", fake_runner)
        r = isolated_server["client"].post(
            f"/threads/{isolated_server['project']}/generate-summary",
            json={"limit": 10},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "generated"
        assert data["summary"]["full"] == "F"
        assert data["summary"]["compressed"] == "C"
        assert data["summary"]["shorthand"] == "S"

    def test_empty_project_status_is_empty(self, isolated_server, monkeypatch):
        from middleware.summary_store import TieredSummary

        def fake_runner(**kwargs):
            s = TieredSummary()  # all tiers empty
            s.touch()
            return s

        monkeypatch.setattr(server_module, "run_summary_generator", fake_runner)
        r = isolated_server["client"].post(
            f"/threads/{isolated_server['project']}/generate-summary",
            json={},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "empty"

    def test_generation_failure_returns_502(self, isolated_server, monkeypatch):
        def boom(**kwargs):
            raise server_module.SummaryGenerationError("simulated LLM failure")

        monkeypatch.setattr(server_module, "run_summary_generator", boom)
        r = isolated_server["client"].post(
            f"/threads/{isolated_server['project']}/generate-summary",
            json={},
        )
        assert r.status_code == 502
        err = r.json()["detail"]
        assert err["error"] == "SUMMARY_GENERATION_FAILED"
        assert "simulated LLM failure" in err["message"]


class TestSummaryDue:
    def test_fresh_project_reports_not_due(self, isolated_server):
        r = isolated_server["client"].get(
            f"/threads/{isolated_server['project']}/summary-due"
        )
        assert r.status_code == 200
        d = r.json()
        assert d["project"] == "InterAI-Protocol"
        assert d["due"] is False
        assert d["entries_since_last_summary"] == 0

    def test_advance_counter_flips_due(self, isolated_server):
        s = isolated_server
        for _ in range(server_module.DEFAULT_SUMMARY_THRESHOLD):
            record_journal_entry(s["summaries"], s["project"])
        r = s["client"].get(f"/threads/{s['project']}/summary-due")
        d = r.json()
        assert d["due"] is True
        assert d["entries_since_last_summary"] == server_module.DEFAULT_SUMMARY_THRESHOLD

    def test_threshold_override_via_query(self, isolated_server):
        s = isolated_server
        record_journal_entry(s["summaries"], s["project"])
        record_journal_entry(s["summaries"], s["project"])
        r = s["client"].get(f"/threads/{s['project']}/summary-due?threshold=2")
        d = r.json()
        assert d["due"] is True
        assert d["threshold"] == 2

    def test_404_on_unknown_project(self, isolated_server):
        r = isolated_server["client"].get("/threads/NoSuchProject/summary-due")
        assert r.status_code == 404
