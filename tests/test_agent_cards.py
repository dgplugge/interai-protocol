"""Tests for agent profile card endpoints."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure api module is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.server import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


class TestListAgents:
    """GET /agents — enumerate agents with cards."""

    def test_returns_200(self, client):
        r = client.get("/agents")
        assert r.status_code == 200

    def test_includes_carded_agents(self, client):
        r = client.get("/agents")
        data = r.json()
        assert "agents" in data
        for expected in ("lumen", "lodestar", "spindrift", "trident", "astra", "helix", "torch"):
            assert expected in data["agents"], f"expected {expected} in {data['agents']}"

    def test_count_matches_list(self, client):
        data = client.get("/agents").json()
        assert data["count"] == len(data["agents"])


class TestGetAgentCard:
    """GET /agents/{name}/card — fetch one card."""

    def test_lumen_returns_200(self, client):
        r = client.get("/agents/lumen/card")
        assert r.status_code == 200

    def test_lumen_payload_shape(self, client):
        data = client.get("/agents/lumen/card").json()
        assert data["name"] == "lumen"
        assert "card" in data
        assert len(data["card"]) > 0

    def test_card_contains_profile_header(self, client):
        data = client.get("/agents/lodestar/card").json()
        assert "# AGENT PROFILE:" in data["card"]

    def test_card_names_agent(self, client):
        data = client.get("/agents/trident/card").json()
        assert "Trident" in data["card"]

    def test_case_insensitive(self, client):
        r_lower = client.get("/agents/lumen/card")
        r_upper = client.get("/agents/LUMEN/card")
        r_mixed = client.get("/agents/Lumen/card")
        assert r_lower.status_code == 200
        assert r_upper.status_code == 200
        assert r_mixed.status_code == 200
        assert r_lower.json()["card"] == r_upper.json()["card"] == r_mixed.json()["card"]

    def test_missing_returns_404(self, client):
        r = client.get("/agents/nonexistent/card")
        assert r.status_code == 404

    def test_pharos_now_carded(self, client):
        r = client.get("/agents/pharos/card")
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "pharos"
        assert "Pharos" in data["card"]

    def test_forge_now_carded(self, client):
        r = client.get("/agents/forge/card")
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "forge"
        assert "Forge" in data["card"]

    def test_astra_now_carded(self, client):
        r = client.get("/agents/astra/card")
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "astra"
        assert "Astra" in data["card"]

    def test_helix_now_carded(self, client):
        r = client.get("/agents/helix/card")
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "helix"
        assert "Helix" in data["card"]

    def test_torch_now_carded(self, client):
        r = client.get("/agents/torch/card")
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "torch"
        assert "Torch" in data["card"]


class TestCardContent:
    """Content-level checks — each card has required sections."""

    @pytest.mark.parametrize("agent", ["lumen", "lodestar", "spindrift", "trident", "pharos", "forge", "astra", "helix", "torch"])
    def test_card_has_role_line(self, client, agent):
        data = client.get(f"/agents/{agent}/card").json()
        assert "Role:" in data["card"] or "## Role" in data["card"]

    @pytest.mark.parametrize("agent", ["lumen", "lodestar", "spindrift", "trident", "pharos", "forge", "astra", "helix", "torch"])
    def test_card_has_prohibitions(self, client, agent):
        data = client.get(f"/agents/{agent}/card").json()
        assert (
            "prohibitions" in data["card"].lower()
            or "Do NOT" in data["card"]
            or "NO " in data["card"]
        )

    @pytest.mark.parametrize("agent", ["lumen", "lodestar", "spindrift", "trident", "pharos", "forge", "astra", "helix", "torch"])
    def test_card_has_identity_anchoring(self, client, agent):
        data = client.get(f"/agents/{agent}/card").json()
        assert "Identity anchoring" in data["card"]

    def test_lumen_has_prohibition_7(self, client):
        """Verify Lumen's self-proposed prohibition #7 is present."""
        data = client.get("/agents/lumen/card").json()
        assert "MSG-0155 round" in data["card"] or "directly cut waste" in data["card"]
