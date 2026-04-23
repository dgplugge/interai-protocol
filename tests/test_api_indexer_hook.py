"""
Integration test for the RAG indexer hook in api/server.py.

Verifies that POST /threads/{project}/messages triggers a chunk_index upsert
for the newly-written entry, without needing a live uvicorn process.

Uses FastAPI's TestClient + monkeypatch of the module-level INDEX_DB and
SUMMARIES_DIR constants so the hook writes to a temp location per test.
"""

import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api import server as server_module
from api.server import app
from middleware.summary_index import chunk_count, get_chunk


@pytest.fixture
def isolated_server(monkeypatch, tmp_path):
    """Redirect SUMMARIES_DIR, INDEX_DB, and JOURNALS_ROOT to temp locations.

    The journal write path also touches the journal filesystem (messages dir,
    index.json) and the deploy-sync helper. We point all of those into tmp_path
    so nothing leaks into the real repo.
    """
    summaries = tmp_path / "summaries"
    journals = tmp_path / "journals"
    deploy = tmp_path / "deploy"

    monkeypatch.setattr(server_module, "SUMMARIES_DIR", summaries)
    monkeypatch.setattr(server_module, "INDEX_DB", summaries / "index.db")
    monkeypatch.setattr(server_module, "JOURNALS_ROOT", journals)
    monkeypatch.setattr(server_module, "DEPLOY_ROOT", deploy)

    # The existing project must have a journal dir before get_journal_dir()
    # will accept it (it raises 404 otherwise).
    project_dir = journals / "InterAI-Protocol"
    (project_dir / "messages").mkdir(parents=True)
    (project_dir / "journal-index.json").write_text(
        '{"protocol":"AICP/1.0","messages":[],"participants":[]}',
        encoding="utf-8",
    )

    # Disable deploy-sync so the hook path doesn't try to git-push in tests.
    monkeypatch.setattr(server_module, "sync_to_deploy", lambda p: "skipped-in-test")

    return {
        "client": TestClient(app),
        "summaries": summaries,
        "index_db": summaries / "index.db",
        "project": "InterAI-Protocol",
    }


def _post_message(client, project, payload_text="test content"):
    return client.post(
        f"/threads/{project}/messages",
        json={
            "type": "UPDATE",
            "from_agent": "Pharos",
            "to": ["All"],
            "task": "Integration test",
            "status": "CLOSED",
            "payload": payload_text,
        },
    )


class TestIndexerHook:
    def test_post_creates_chunk_row(self, isolated_server):
        s = isolated_server
        r = _post_message(s["client"], s["project"], "hello from test")
        assert r.status_code == 200, r.text
        msg_id = r.json()["message"]["id"]

        assert s["index_db"].exists()
        assert chunk_count(s["index_db"], project=s["project"]) == 1

        chunk = get_chunk(s["index_db"], msg_id)
        assert chunk is not None
        assert chunk.chunk_id == msg_id
        assert chunk.project == s["project"]
        assert chunk.entry_type == "UPDATE"
        assert chunk.from_agent == "Pharos"
        assert chunk.content == "hello from test"
        assert chunk.token_count > 0

    def test_multiple_posts_accumulate(self, isolated_server):
        s = isolated_server
        _post_message(s["client"], s["project"], "one")
        _post_message(s["client"], s["project"], "two")
        _post_message(s["client"], s["project"], "three")

        assert chunk_count(s["index_db"], project=s["project"]) == 3

    def test_hook_failure_does_not_break_post(self, isolated_server, monkeypatch):
        """If index_upsert raises, the journal write must still succeed.

        Real-world risk: disk-full or permission error on the index DB.
        The journal remains the source of truth and must not regress.
        """
        s = isolated_server

        def boom(*args, **kwargs):
            raise RuntimeError("simulated index failure")

        monkeypatch.setattr(server_module, "index_upsert", boom)

        r = _post_message(s["client"], s["project"], "should still save")
        assert r.status_code == 200, r.text
        # Journal write succeeded; indexer was prevented from upserting.
        assert chunk_count(s["index_db"], project=s["project"]) == 0
