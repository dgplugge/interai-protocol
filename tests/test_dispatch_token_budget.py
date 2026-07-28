"""
Tests for dispatch-time token budget enforcement.

The guard uses explicit provider context windows from agent_config, not rate
limit settings. These tests keep the HTTP path isolated from real journals,
embeddings, and deploy sync.
"""

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api import server as server_module
from api.server import app
from middleware.agent_config import AgentConfig, DispatchBudgetConfig
from middleware.thread_compactor import ThreadTracker


def _isolated_client(monkeypatch, tmp_path, dispatch_budget):
    project = "BudgetProject"
    summaries = tmp_path / "summaries"
    journals = tmp_path / "journals"
    deploy = tmp_path / "deploy"

    cfg = AgentConfig()
    cfg.dispatch_budget = dispatch_budget

    monkeypatch.setattr(server_module, "SUMMARIES_DIR", summaries)
    monkeypatch.setattr(server_module, "INDEX_DB", summaries / "index.db")
    monkeypatch.setattr(server_module, "JOURNALS_ROOT", journals)
    monkeypatch.setattr(server_module, "DEPLOY_ROOT", deploy)
    monkeypatch.setattr(server_module, "agent_config", cfg)
    monkeypatch.setattr(
        server_module,
        "thread_tracker",
        ThreadTracker(summary_dir=summaries, threshold=10),
    )
    monkeypatch.setattr(
        server_module,
        "PROJECTS",
        {project: {"label": "Budget Project"}},
    )
    monkeypatch.setattr(
        server_module,
        "PROVIDERS",
        [{"name": "Tiny", "provider": "openai", "model": "tiny", "role": "Test"}],
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

    return TestClient(app), project, project_dir


def _dispatch(client, project, prompt):
    return client.post(
        f"/threads/{project}/dispatch",
        json={
            "prompt": prompt,
            "task": "Budget check",
            "turn_mode": "round-robin",
            "agents": ["Tiny"],
        },
    )


def test_dispatch_returns_token_budget_metadata(monkeypatch, tmp_path):
    budget = DispatchBudgetConfig(
        enabled=True,
        expected_response_tokens=10,
        default_context_tokens=100,
        provider_context_tokens={"openai": 100},
    )
    client, project, _project_dir = _isolated_client(monkeypatch, tmp_path, budget)

    response = _dispatch(client, project, "short prompt")

    assert response.status_code == 200, response.text
    token_budget = response.json()["token_budget"]
    assert token_budget["enabled"] is True
    assert token_budget["within_budget"] is True
    assert token_budget["providers"][0]["agent"] == "Tiny"
    assert token_budget["providers"][0]["provider"] == "openai"
    assert token_budget["providers"][0]["context_limit_tokens"] == 100


def test_dispatch_rejects_over_context_limit_before_writing(monkeypatch, tmp_path):
    budget = DispatchBudgetConfig(
        enabled=True,
        expected_response_tokens=10,
        default_context_tokens=12,
        provider_context_tokens={"openai": 12},
    )
    client, project, project_dir = _isolated_client(monkeypatch, tmp_path, budget)

    response = _dispatch(client, project, "This prompt is intentionally too large.")

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["error"] == "TOKEN_BUDGET_EXCEEDED"
    assert detail["offenders"][0]["agent"] == "Tiny"
    assert detail["offenders"][0]["estimated_total_tokens"] > 12

    index_data = json.loads((project_dir / "journal-index.json").read_text(encoding="utf-8"))
    assert index_data["messages"] == []
    assert list((project_dir / "messages").glob("*.md")) == []


def test_disabled_guard_allows_oversized_dispatch(monkeypatch, tmp_path):
    budget = DispatchBudgetConfig(
        enabled=False,
        expected_response_tokens=10,
        default_context_tokens=12,
        provider_context_tokens={"openai": 12},
    )
    client, project, _project_dir = _isolated_client(monkeypatch, tmp_path, budget)

    response = _dispatch(client, project, "This prompt would exceed the tiny test limit.")

    assert response.status_code == 200, response.text
    assert response.json()["token_budget"]["enabled"] is False
    assert response.json()["token_budget"]["within_budget"] is False
