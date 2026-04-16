"""
AICP Hub — CLI Status Dashboard

Prints a formatted health dashboard to the terminal with color-coded output.
Run with:  python -m src.hub.cli
"""

import io
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Ensure src is importable when run as module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.hub.status import collect_hub_status


# --- ANSI Colors ---

class Color:
    GREEN = "\033[32m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def _status_color(status: str) -> str:
    """Return ANSI color code for a status string."""
    if status in ("up", "active", "healthy"):
        return Color.GREEN
    elif status in ("down", "offline", "error"):
        return Color.RED
    return Color.YELLOW


def _colored(text: str, color: str) -> str:
    return f"{color}{text}{Color.RESET}"


def _header(title: str) -> str:
    line = "=" * 56
    return f"\n{_colored(line, Color.DIM)}\n  {_colored(title, Color.BOLD + Color.CYAN)}\n{_colored(line, Color.DIM)}"


def _section(title: str) -> str:
    return f"\n  {_colored(title, Color.BOLD)}"


def print_dashboard(status: dict) -> None:
    """Print a formatted status dashboard to stdout."""
    print(_header("AICP Hub Status Dashboard"))
    print(f"  {_colored('Timestamp:', Color.DIM)} {status['timestamp']}")

    # --- Servers ---
    print(_section("Servers"))
    for key in ("relay", "api"):
        srv = status[key]
        color = _status_color(srv["status"])
        indicator = _colored("●", color)
        label = f"{srv['name']} (:{srv['port']})"
        print(f"    {indicator} {label:<30} {_colored(srv['status'].upper(), color)}")

    # --- Agents ---
    agents = status["agents"]
    print(_section(f"Agents ({agents['total']} total)"))
    if agents.get("error"):
        print(f"    {_colored('ERROR: ' + agents['error'], Color.RED)}")
    else:
        for agent in agents["agents"]:
            color = _status_color(agent["status"])
            indicator = _colored("●", color)
            roles_str = ", ".join(agent["roles"]) if agent["roles"] else "—"
            name = f"{agent['name']} ({agent['type']})"
            print(f"    {indicator} {name:<28} {roles_str}")
        summary_parts = [
            _colored(f"{agents['active']} active", Color.GREEN),
        ]
        if agents["pending_setup"] > 0:
            summary_parts.append(
                _colored(f"{agents['pending_setup']} pending", Color.YELLOW)
            )
        print(f"    Summary: {', '.join(summary_parts)}")

    # --- Inboxes ---
    inboxes = status["inboxes"]
    print(_section("Inboxes"))
    if not inboxes["agents"]:
        print(f"    {_colored('No inbox files found', Color.DIM)}")
    else:
        for agent_id, info in sorted(inboxes["agents"].items()):
            unread = info["unread"]
            total = info["total"]
            if unread > 0:
                count_str = _colored(f"{unread} unread", Color.YELLOW)
            else:
                count_str = _colored("0 unread", Color.GREEN)
            print(f"    {agent_id:<20} {count_str} / {total} total")
        print(f"    Total unread: {_colored(str(inboxes['total_unread']), Color.BOLD)}")

    # --- Kernels ---
    kernels = status["kernels"]
    print(_section(f"Context Kernels ({kernels['count']})"))
    if kernels["count"] == 0:
        print(f"    {_colored('No kernels found', Color.DIM)}")
    else:
        for k in kernels["kernels"]:
            stale = k.get("stale_days")
            updated = k.get("updated", "unknown")
            if stale is not None and stale > 7:
                stale_str = _colored(f"{stale}d stale", Color.RED)
            elif stale is not None and stale > 3:
                stale_str = _colored(f"{stale}d ago", Color.YELLOW)
            elif stale is not None:
                stale_str = _colored(f"{stale}d ago", Color.GREEN)
            else:
                stale_str = _colored("unknown", Color.DIM)
            print(f"    {k['file']:<36} updated: {updated}  ({stale_str})")

    # --- Journals ---
    journals = status["journals"]
    print(_section(f"Journals ({journals['total_messages']} messages)"))
    if not journals["projects"]:
        print(f"    {_colored('No journal projects found', Color.DIM)}")
    else:
        for project, info in sorted(journals["projects"].items()):
            count = info["count"]
            latest = info.get("latest_message", "—") or "—"
            count_str = _colored(str(count), Color.BOLD)
            print(f"    {project:<24} {count_str} msgs   latest: {latest}")

    print()


def main():
    status = collect_hub_status()
    print_dashboard(status)


if __name__ == "__main__":
    main()
