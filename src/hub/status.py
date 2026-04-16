"""
AICP Hub — Health Status Collector

Gathers health and status information from all Hub infrastructure components:
- Relay server (port 8080)
- API server (FastAPI)
- Agent registry
- Agent inboxes
- Context kernels
- AICP journals

Returns a structured dict suitable for CLI display or API responses.
"""

import json
import os
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# --- Paths (relative to repo root) ---

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VIEWER_DIR = REPO_ROOT / "viewer"
AGENT_REGISTRY_FILE = VIEWER_DIR / "agent-registry.json"
INBOX_DIR = VIEWER_DIR / "inbox"
KERNELS_DIR = REPO_ROOT / "kernels"
JOURNALS_ROOT = Path("H:/Code/Agent-Journals")

PROJECTS = ["InterAI-Protocol", "OperatorHub", "StudyGuide", "PortfolioAnalysis"]

# Default ports
RELAY_PORT = 8080
API_PORT = 8000


def check_port(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check if a TCP port is accepting connections."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (ConnectionRefusedError, TimeoutError, OSError):
        return False


def collect_relay_status() -> dict[str, Any]:
    """Check relay server health on port 8080."""
    up = check_port("127.0.0.1", RELAY_PORT)
    return {
        "name": "Relay Server",
        "port": RELAY_PORT,
        "status": "up" if up else "down",
    }


def collect_api_status() -> dict[str, Any]:
    """Check API server health on port 8000."""
    up = check_port("127.0.0.1", API_PORT)
    return {
        "name": "API Server",
        "port": API_PORT,
        "status": "up" if up else "down",
    }


def collect_agent_summary() -> dict[str, Any]:
    """
    Read agent-registry.json and summarize agent counts by status.
    Returns total, active, and pending_setup counts plus per-agent details.
    """
    result = {
        "total": 0,
        "active": 0,
        "pending_setup": 0,
        "agents": [],
    }

    if not AGENT_REGISTRY_FILE.exists():
        result["error"] = "agent-registry.json not found"
        return result

    try:
        data = json.loads(AGENT_REGISTRY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError) as e:
        result["error"] = str(e)
        return result

    agents = data.get("agents", [])
    result["total"] = len(agents)

    for agent in agents:
        status = agent.get("status", "unknown")
        entry = {
            "id": agent.get("id", "unknown"),
            "name": agent.get("name", "Unknown"),
            "type": agent.get("type", "unknown"),
            "status": status,
            "roles": agent.get("roles", []),
        }
        result["agents"].append(entry)

        if status == "active":
            result["active"] += 1
        elif status in ("pending", "standby"):
            result["pending_setup"] += 1

    return result


def collect_inbox_summary() -> dict[str, Any]:
    """
    Scan viewer/inbox/*.json and return unread counts per agent.
    """
    result = {
        "agents": {},
        "total_unread": 0,
    }

    if not INBOX_DIR.exists():
        return result

    for inbox_file in sorted(INBOX_DIR.glob("*.json")):
        agent_id = inbox_file.stem
        try:
            data = json.loads(inbox_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            result["agents"][agent_id] = {"unread": 0, "total": 0, "error": "parse error"}
            continue

        notifications = data.get("notifications", [])
        unread = sum(1 for n in notifications if not n.get("read", False))
        result["agents"][agent_id] = {
            "unread": unread,
            "total": len(notifications),
        }
        result["total_unread"] += unread

    return result


def collect_kernel_status() -> dict[str, Any]:
    """
    Scan kernels/*.md and report count plus staleness per kernel.
    Staleness is determined by parsing the 'Updated:' field in the header.
    """
    result = {
        "count": 0,
        "kernels": [],
    }

    if not KERNELS_DIR.exists():
        return result

    now = datetime.now(timezone.utc)

    for kernel_file in sorted(KERNELS_DIR.glob("*.md")):
        result["count"] += 1
        entry = {
            "file": kernel_file.name,
            "updated": None,
            "stale_days": None,
        }

        try:
            # Read first 5 lines to find the Updated field
            text = kernel_file.read_text(encoding="utf-8")
            for line in text.split("\n")[:5]:
                if "Updated:" in line:
                    # Extract date from patterns like "Updated: 2026-04-14"
                    parts = line.split("Updated:")
                    if len(parts) > 1:
                        date_str = parts[1].strip().split("|")[0].strip()
                        try:
                            updated = datetime.strptime(date_str, "%Y-%m-%d").replace(
                                tzinfo=timezone.utc
                            )
                            entry["updated"] = date_str
                            delta = now - updated
                            entry["stale_days"] = delta.days
                        except ValueError:
                            pass
                    break
        except IOError:
            entry["error"] = "read error"

        result["kernels"].append(entry)

    return result


def collect_journal_stats() -> dict[str, Any]:
    """
    Scan journal-index.json for each project and return message counts
    and latest message timestamps.
    """
    result = {
        "projects": {},
        "total_messages": 0,
    }

    for project in PROJECTS:
        index_path = JOURNALS_ROOT / project / "journal-index.json"
        if not index_path.exists():
            continue

        try:
            data = json.loads(index_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            result["projects"][project] = {"count": 0, "error": "parse error"}
            continue

        messages = data.get("messages", [])
        count = len(messages)
        result["total_messages"] += count

        # Find latest timestamp
        latest = None
        if messages:
            times = [m.get("time", "") for m in messages if m.get("time")]
            if times:
                latest = times[-1]

        result["projects"][project] = {
            "count": count,
            "latest_message": latest,
        }

    return result


def collect_hub_status() -> dict[str, Any]:
    """
    Collect full Hub health status from all components.
    Returns a structured dict with all subsystem statuses.
    """
    now = datetime.now(timezone.utc).astimezone()

    return {
        "timestamp": now.isoformat(),
        "relay": collect_relay_status(),
        "api": collect_api_status(),
        "agents": collect_agent_summary(),
        "inboxes": collect_inbox_summary(),
        "kernels": collect_kernel_status(),
        "journals": collect_journal_stats(),
    }
