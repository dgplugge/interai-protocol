"""
Tests for src.hub.status — Hub health status collector.
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.hub.status import (
    check_port,
    collect_agent_summary,
    collect_api_status,
    collect_hub_status,
    collect_inbox_summary,
    collect_journal_stats,
    collect_kernel_status,
    collect_relay_status,
)


# --- check_port ---


def test_check_port_closed():
    """A port with nothing listening should return False."""
    # Use a high port unlikely to be in use
    assert check_port("127.0.0.1", 59999, timeout=0.2) is False


@patch("src.hub.status.socket.create_connection")
def test_check_port_open(mock_conn):
    """When connection succeeds, check_port returns True."""
    mock_conn.return_value.__enter__ = lambda s: s
    mock_conn.return_value.__exit__ = lambda s, *a: None
    assert check_port("127.0.0.1", 8080) is True


# --- collect_relay_status / collect_api_status ---


@patch("src.hub.status.check_port", return_value=True)
def test_relay_status_up(mock_port):
    result = collect_relay_status()
    assert result["status"] == "up"
    assert result["port"] == 8080
    assert result["name"] == "Relay Server"


@patch("src.hub.status.check_port", return_value=False)
def test_relay_status_down(mock_port):
    result = collect_relay_status()
    assert result["status"] == "down"


@patch("src.hub.status.check_port", return_value=True)
def test_api_status_up(mock_port):
    result = collect_api_status()
    assert result["status"] == "up"
    assert result["port"] == 8000


@patch("src.hub.status.check_port", return_value=False)
def test_api_status_down(mock_port):
    result = collect_api_status()
    assert result["status"] == "down"


# --- collect_agent_summary ---


def test_agent_summary_with_registry(tmp_path):
    """Reads agent-registry.json and counts by status."""
    registry = {
        "agents": [
            {"id": "don", "name": "Don", "type": "human", "status": "active", "roles": ["Orchestrator"]},
            {"id": "pharos", "name": "Pharos", "type": "ai", "status": "active", "roles": ["Lead Coder"]},
            {"id": "lumen", "name": "Lumen", "type": "ai", "status": "pending", "roles": []},
        ]
    }
    reg_file = tmp_path / "agent-registry.json"
    reg_file.write_text(json.dumps(registry), encoding="utf-8")

    with patch("src.hub.status.AGENT_REGISTRY_FILE", reg_file):
        result = collect_agent_summary()

    assert result["total"] == 3
    assert result["active"] == 2
    assert result["pending_setup"] == 1
    assert len(result["agents"]) == 3


def test_agent_summary_missing_file(tmp_path):
    """Returns error when registry file is missing."""
    missing = tmp_path / "nonexistent.json"
    with patch("src.hub.status.AGENT_REGISTRY_FILE", missing):
        result = collect_agent_summary()
    assert result["total"] == 0
    assert "error" in result


def test_agent_summary_invalid_json(tmp_path):
    """Returns error when registry file contains invalid JSON."""
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("not json!", encoding="utf-8")
    with patch("src.hub.status.AGENT_REGISTRY_FILE", bad_file):
        result = collect_agent_summary()
    assert result["total"] == 0
    assert "error" in result


# --- collect_inbox_summary ---


def test_inbox_summary(tmp_path):
    """Counts unread notifications across agent inboxes."""
    inbox_dir = tmp_path / "inbox"
    inbox_dir.mkdir()

    # pharos: 1 unread, 1 read
    (inbox_dir / "pharos.json").write_text(json.dumps({
        "agentId": "pharos",
        "notifications": [
            {"read": False, "event": "new_message"},
            {"read": True, "event": "new_message"},
        ],
    }), encoding="utf-8")

    # don: all read
    (inbox_dir / "don.json").write_text(json.dumps({
        "agentId": "don",
        "notifications": [
            {"read": True, "event": "new_message"},
        ],
    }), encoding="utf-8")

    with patch("src.hub.status.INBOX_DIR", inbox_dir):
        result = collect_inbox_summary()

    assert result["total_unread"] == 1
    assert result["agents"]["pharos"]["unread"] == 1
    assert result["agents"]["pharos"]["total"] == 2
    assert result["agents"]["don"]["unread"] == 0


def test_inbox_summary_no_dir(tmp_path):
    """Returns empty result when inbox directory doesn't exist."""
    with patch("src.hub.status.INBOX_DIR", tmp_path / "nonexistent"):
        result = collect_inbox_summary()
    assert result["total_unread"] == 0
    assert result["agents"] == {}


def test_inbox_summary_bad_json(tmp_path):
    """Handles corrupt inbox files gracefully."""
    inbox_dir = tmp_path / "inbox"
    inbox_dir.mkdir()
    (inbox_dir / "bad.json").write_text("{{invalid", encoding="utf-8")

    with patch("src.hub.status.INBOX_DIR", inbox_dir):
        result = collect_inbox_summary()

    assert "bad" in result["agents"]
    assert "error" in result["agents"]["bad"]


# --- collect_kernel_status ---


def test_kernel_status(tmp_path):
    """Parses kernel files and computes staleness."""
    kernels_dir = tmp_path / "kernels"
    kernels_dir.mkdir()

    (kernels_dir / "kernel-test.md").write_text(
        "# CONTEXT KERNEL: Test\n"
        "# Version: 1.0 | Updated: 2026-04-14 | Task: Testing\n"
        "\n---PROTO---\n",
        encoding="utf-8",
    )

    with patch("src.hub.status.KERNELS_DIR", kernels_dir):
        result = collect_kernel_status()

    assert result["count"] == 1
    assert result["kernels"][0]["file"] == "kernel-test.md"
    assert result["kernels"][0]["updated"] == "2026-04-14"
    assert isinstance(result["kernels"][0]["stale_days"], int)


def test_kernel_status_no_date(tmp_path):
    """Handles kernel files without an Updated field."""
    kernels_dir = tmp_path / "kernels"
    kernels_dir.mkdir()

    (kernels_dir / "kernel-bare.md").write_text(
        "# CONTEXT KERNEL: Bare\n\nNo date here.\n",
        encoding="utf-8",
    )

    with patch("src.hub.status.KERNELS_DIR", kernels_dir):
        result = collect_kernel_status()

    assert result["count"] == 1
    assert result["kernels"][0]["updated"] is None
    assert result["kernels"][0]["stale_days"] is None


def test_kernel_status_empty_dir(tmp_path):
    """Returns zero count when no kernels exist."""
    kernels_dir = tmp_path / "kernels"
    kernels_dir.mkdir()

    with patch("src.hub.status.KERNELS_DIR", kernels_dir):
        result = collect_kernel_status()

    assert result["count"] == 0
    assert result["kernels"] == []


# --- collect_journal_stats ---


def test_journal_stats(tmp_path):
    """Reads journal indexes and aggregates message counts."""
    journals_root = tmp_path / "journals"

    # Create InterAI-Protocol with 3 messages
    proj_dir = journals_root / "InterAI-Protocol"
    proj_dir.mkdir(parents=True)
    (proj_dir / "journal-index.json").write_text(json.dumps({
        "protocol": "AICP/1.0",
        "project": "InterAI-Protocol",
        "messages": [
            {"id": "MSG-0001", "time": "2026-03-09T10:00:00-04:00"},
            {"id": "MSG-0002", "time": "2026-03-09T11:00:00-04:00"},
            {"id": "MSG-0003", "time": "2026-03-10T09:00:00-04:00"},
        ],
    }), encoding="utf-8")

    # Create StudyGuide with 1 message
    sg_dir = journals_root / "StudyGuide"
    sg_dir.mkdir(parents=True)
    (sg_dir / "journal-index.json").write_text(json.dumps({
        "protocol": "AICP/1.0",
        "project": "StudyGuide",
        "messages": [
            {"id": "SG-MSG-0001", "time": "2026-03-30T12:00:00-04:00"},
        ],
    }), encoding="utf-8")

    with patch("src.hub.status.JOURNALS_ROOT", journals_root):
        result = collect_journal_stats()

    assert result["total_messages"] == 4
    assert result["projects"]["InterAI-Protocol"]["count"] == 3
    assert result["projects"]["InterAI-Protocol"]["latest_message"] == "2026-03-10T09:00:00-04:00"
    assert result["projects"]["StudyGuide"]["count"] == 1


def test_journal_stats_missing_project(tmp_path):
    """Skips projects whose journal directories don't exist."""
    journals_root = tmp_path / "journals"
    journals_root.mkdir()
    # No project subdirectories created

    with patch("src.hub.status.JOURNALS_ROOT", journals_root):
        result = collect_journal_stats()

    assert result["total_messages"] == 0
    assert result["projects"] == {}


# --- collect_hub_status (integration) ---


@patch("src.hub.status.check_port", return_value=False)
def test_collect_hub_status_structure(mock_port):
    """Top-level collector returns all expected keys."""
    result = collect_hub_status()

    assert "timestamp" in result
    assert "relay" in result
    assert "api" in result
    assert "agents" in result
    assert "inboxes" in result
    assert "kernels" in result
    assert "journals" in result

    # Verify nested structures
    assert "status" in result["relay"]
    assert "status" in result["api"]
    assert "total" in result["agents"]
    assert "total_unread" in result["inboxes"]
    assert "count" in result["kernels"]
    assert "total_messages" in result["journals"]
