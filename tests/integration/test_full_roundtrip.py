"""
End-to-end API composition test for the MVP reliability path.

This deliberately follows the real API lifecycle:
- /dispatch records the orchestrator REQUEST and tracks compaction state.
- /messages enforces $DECISION on RESPONSE messages.
- /compact, /generate-summary, /retrieve, and /rag-prefix are explicit
  endpoints, not implicit stages of every dispatch.

Provider calls, embeddings, scheduler work, and deploy sync are mocked or
disabled so pytest stays offline and deterministic.
"""

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from api import server as server_module
from api.server import app
from middleware.retrieval import RetrievalHit
from middleware.summary_index import Chunk
from middleware.summary_store import TieredSummary, read_summary, write_summary
from middleware.thread_compactor import ThreadTracker


@pytest.fixture
def isolated_api(monkeypatch, tmp_path):
    project = "IntegrationTest"
    summaries = tmp_path / "summaries"
    journals = tmp_path / "journals"
    deploy = tmp_path / "deploy"
    index_db = summaries / "index.db"

    monkeypatch.setattr(server_module, "SUMMARIES_DIR", summaries)
    monkeypatch.setattr(server_module, "INDEX_DB", index_db)
    monkeypatch.setattr(server_module, "JOURNALS_ROOT", journals)
    monkeypatch.setattr(server_module, "DEPLOY_ROOT", deploy)
    monkeypatch.setattr(
        server_module,
        "thread_tracker",
        ThreadTracker(summary_dir=summaries, threshold=3),
    )
    monkeypatch.setattr(
        server_module,
        "PROJECTS",
        {project: {"label": "Integration Test"}},
    )
    monkeypatch.setattr(server_module, "sync_to_deploy", lambda project: "skipped-in-test")
    monkeypatch.setattr(server_module, "_try_embed", lambda content: None)

    project_dir = journals / project
    (project_dir / "messages").mkdir(parents=True)
    (project_dir / "journal-index.json").write_text(
        json.dumps({
            "protocol": "AICP/1.0",
            "project": project,
            "participants": ["Don"],
            "messages": [],
        }),
        encoding="utf-8",
    )

    return {
        "client": TestClient(app),
        "project": project,
        "summaries": summaries,
        "journals": journals,
        "index_db": index_db,
    }


def _dispatch(client: TestClient, project: str, prompt: str, task: str = "Roundtrip"):
    return client.post(
        f"/threads/{project}/dispatch",
        json={
            "prompt": prompt,
            "task": task,
            "turn_mode": "round-robin",
            "agents": ["Pharos"],
        },
    )


def _response(client: TestClient, project: str, payload: str):
    return client.post(
        f"/threads/{project}/messages",
        json={
            "type": "RESPONSE",
            "from_agent": "Pharos",
            "to": ["Don"],
            "task": "Roundtrip response",
            "status": "CLOSED",
            "payload": payload,
        },
    )


def test_full_roundtrip_api_lifecycle(isolated_api, monkeypatch):
    s = isolated_api
    client = s["client"]
    project = s["project"]

    # 1. /dispatch records an orchestrator REQUEST and reports compaction state.
    first = _dispatch(client, project, "Canary prompt.")
    assert first.status_code == 200, first.text
    first_data = first.json()
    assert first_data["status"] == "dispatched"
    assert first_data["prompt_message_id"] == "MSG-0001"
    assert first_data["messages_since_compact"] == 1
    assert first_data["compact_due"] is False

    # 2. RESPONSE $DECISION validation occurs on the live /messages write path.
    invalid = _response(client, project, "$DECISION: MAYBE\n\nInvalid decision.")
    assert invalid.status_code == 400
    assert invalid.json()["detail"]["error"] == "INVALID_DECISION_STATE"

    valid = _response(client, project, "$DECISION: EXECUTE\n\nValid decision.")
    assert valid.status_code == 200, valid.text
    assert valid.json()["messages_since_compact"] == 2
    assert valid.json()["compact_due"] is False

    second = _dispatch(client, project, "Second prompt drives compaction due.")
    assert second.status_code == 200, second.text
    assert second.json()["messages_since_compact"] == 3
    assert second.json()["compact_due"] is True

    # 3. Explicit compaction writes the thread summary sidecar and resets count.
    compacted = client.post(f"/threads/{project}/compact")
    assert compacted.status_code == 200, compacted.text
    compact_data = compacted.json()
    assert compact_data["status"] == "compacted"
    assert compact_data["messages_compacted"] == 3
    assert compact_data["summary"]["thread_id"] == project
    assert compact_data["summary"]["message_count"] == 3
    assert any(
        d["decision"] == "EXECUTE" and d["agent"] == "Pharos"
        for d in compact_data["summary"]["decisions"]
    )

    sidecar = s["summaries"] / f"{project}.summary.json"
    assert sidecar.exists()
    sidecar_data = json.loads(sidecar.read_text(encoding="utf-8"))
    assert sidecar_data["thread_id"] == project
    assert client.get(f"/threads/{project}/summary").json()["message_count_since_compact"] == 0

    # 4. /generate-summary is its own endpoint and can write the tiered YAML.
    def fake_summary_generator(**kwargs):
        summary = TieredSummary(
            full="Full integration summary.",
            compressed="Compressed integration summary.",
            shorthand="S: integration summary.",
        )
        summary.metadata.entry_range = ["MSG-0001", "MSG-0003"]
        summary.touch()
        write_summary(kwargs["summaries_root"], kwargs["project"], summary)
        return summary

    monkeypatch.setattr(server_module, "run_summary_generator", fake_summary_generator)

    generated = client.post(f"/threads/{project}/generate-summary", json={"limit": 3})
    assert generated.status_code == 200, generated.text
    generated_data = generated.json()
    assert generated_data["status"] == "generated"
    assert generated_data["summary"]["compressed"] == "Compressed integration summary."

    stored = read_summary(s["summaries"], project)
    assert stored is not None
    assert stored.shorthand == "S: integration summary."

    # 5. /retrieve and /rag-prefix are explicit RAG endpoints. Retrieval itself
    # is mocked here; vector math and embedder behavior have narrower unit tests.
    fake_hits = [
        RetrievalHit(
            chunk=Chunk(
                chunk_id="MSG-0002",
                project=project,
                entry_type="RESPONSE",
                from_agent="Pharos",
                content="$DECISION: EXECUTE\n\nValid decision.",
                token_count=4,
                last_indexed="2026-07-28T12:00:00Z",
            ),
            score=0.91,
        )
    ]
    monkeypatch.setattr(server_module, "rag_retrieve", lambda **kwargs: fake_hits)

    retrieved = client.post(
        f"/threads/{project}/retrieve",
        json={"query": "decision", "top_k": 1},
    )
    assert retrieved.status_code == 200, retrieved.text
    retrieved_data = retrieved.json()
    assert retrieved_data["count"] == 1
    assert retrieved_data["hits"][0]["chunk_id"] == "MSG-0002"
    assert retrieved_data["hits"][0]["score"] == pytest.approx(0.91)

    prefix = client.get(f"/threads/{project}/rag-prefix?query=decision&top_k=1")
    assert prefix.status_code == 200
    assert "=== RELEVANT CONTEXT (RAG) ===" in prefix.text
    assert "[MSG-0002 | RESPONSE | from=Pharos | score=0.910]" in prefix.text
    assert "$DECISION: EXECUTE" in prefix.text
