"""
AICP Phase 2 — REST API Server
Provides dynamic read/write access to AICP journals.
Auto-syncs to GitHub (aicp-journals repo) on every write.
"""

import json
import os
import subprocess
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --- Configuration ---

JOURNALS_ROOT = Path("H:/Code/Agent-Journals")
DEPLOY_ROOT = Path("H:/Code/aicp-journals/data")

PROJECTS = {
    "InterAI-Protocol": {"label": "InterAI Protocol"},
    "OperatorHub":      {"label": "OperatorHub"},
    "StudyGuide":       {"label": "Study Guide"},
    "PortfolioAnalysis": {"label": "Portfolio Analysis"},
}

PROVIDERS = [
    {"name": "Pharos",    "provider": "Anthropic", "model": "Claude Sonnet 4",   "role": "Lead Coder"},
    {"name": "Lodestar",  "provider": "OpenAI",    "model": "GPT-4o",            "role": "Architect"},
    {"name": "Forge",     "provider": "OpenAI",    "model": "o3-mini",           "role": "Reasoner"},
    {"name": "SpinDrift", "provider": "OpenAI",    "model": "GPT-4o",            "role": "Analyst"},
    {"name": "Trident",   "provider": "Google",    "model": "Gemini 2.5 Flash",  "role": "Research / Synthesis"},
    {"name": "Lumen",     "provider": "Mistral",   "model": "Devstral 2",        "role": "Pending Setup"},
]

# --- App ---

app = FastAPI(
    title="AICP Journal API",
    description="Phase 2 — Dynamic read/write API for inter-agent communication journals",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Models ---

class MessageCreate(BaseModel):
    type: str                          # REQUEST, RESPONSE, ACK, REVIEW, UPDATE, PLAN
    from_agent: str                    # $FROM
    to: list[str]                      # $TO
    task: str                          # $TASK
    role: str = ""                     # $ROLE
    intent: str = ""                   # $INTENT
    status: str = "IN_PROGRESS"        # $STATUS
    ref: Optional[str] = None         # $REF — parent message ID
    payload: str = ""                  # ---PAYLOAD--- content


class ThreadCreate(BaseModel):
    project: str                       # project key from PROJECTS
    participants: list[str] = []


# --- Helpers ---

def get_journal_dir(project: str) -> Path:
    d = JOURNALS_ROOT / project
    if not d.exists():
        raise HTTPException(404, f"Project '{project}' not found")
    return d


def load_index(project: str) -> dict:
    idx_path = get_journal_dir(project) / "journal-index.json"
    if not idx_path.exists():
        raise HTTPException(404, f"No journal index for '{project}'")
    return json.loads(idx_path.read_text(encoding="utf-8"))


def save_index(project: str, data: dict):
    idx_path = get_journal_dir(project) / "journal-index.json"
    idx_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def next_seq(index_data: dict) -> int:
    messages = index_data.get("messages", [])
    if not messages:
        return 1
    max_seq = 0
    for m in messages:
        s = m.get("seq", 0)
        if isinstance(s, int) and s > max_seq:
            max_seq = s
    return max_seq + 1


def next_msg_id(index_data: dict, project: str) -> str:
    messages = index_data.get("messages", [])
    max_num = 0
    for m in messages:
        mid = m.get("id", "")
        # Extract numeric portion from IDs like MSG-0097, OH-MSG-0005, SG-MSG-0001
        parts = mid.split("-")
        for part in parts:
            if part.isdigit():
                num = int(part)
                if num > max_num:
                    max_num = num
    new_num = max_num + 1

    # Use project-specific prefix
    prefixes = {
        "InterAI-Protocol": "MSG",
        "OperatorHub": "OH-MSG",
        "StudyGuide": "SG-MSG",
        "PortfolioAnalysis": "PA-MSG",
    }
    prefix = prefixes.get(project, "MSG")
    return f"{prefix}-{new_num:04d}"


def sync_to_deploy(project: str):
    """Copy updated journal data to the deploy repo and push to GitHub."""
    src = JOURNALS_ROOT / project
    dst = DEPLOY_ROOT / project

    # Ensure destination exists
    dst.mkdir(parents=True, exist_ok=True)
    (dst / "messages").mkdir(exist_ok=True)

    # Copy index
    shutil.copy2(src / "journal-index.json", dst / "journal-index.json")

    # Copy all messages
    src_msgs = src / "messages"
    dst_msgs = dst / "messages"
    for f in src_msgs.glob("*.md"):
        shutil.copy2(f, dst_msgs / f.name)

    # Git add, commit, push
    repo = DEPLOY_ROOT.parent  # H:/Code/aicp-journals
    try:
        subprocess.run(
            ["git", "add", "."],
            cwd=str(repo), check=True, capture_output=True
        )
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(repo), check=True, capture_output=True, text=True
        )
        if result.stdout.strip():
            subprocess.run(
                ["git", "commit", "-m", f"Auto-sync: {project} journal update"],
                cwd=str(repo), check=True, capture_output=True
            )
            subprocess.run(
                ["git", "push", "origin", "main"],
                cwd=str(repo), check=True, capture_output=True
            )
            return "pushed"
        return "no-changes"
    except subprocess.CalledProcessError as e:
        return f"sync-error: {e.stderr}"


# --- Routes ---

@app.get("/")
def root():
    return {
        "service": "AICP Journal API",
        "version": "2.0.0",
        "phase": 2,
        "endpoints": [
            "GET  /threads",
            "GET  /threads/{project}",
            "GET  /threads/{project}/transcript",
            "POST /threads/{project}/messages",
            "GET  /providers",
        ]
    }


@app.get("/threads")
def list_threads():
    """List all projects (threads) with message counts."""
    threads = []
    for key, meta in PROJECTS.items():
        journal_dir = JOURNALS_ROOT / key
        if not journal_dir.exists():
            continue
        idx_path = journal_dir / "journal-index.json"
        count = 0
        if idx_path.exists():
            data = json.loads(idx_path.read_text(encoding="utf-8"))
            count = len(data.get("messages", []))
        threads.append({
            "project": key,
            "label": meta["label"],
            "message_count": count,
        })
    return {"threads": threads}


@app.get("/threads/{project}")
def get_thread(project: str):
    """Get thread metadata and participant list."""
    data = load_index(project)
    return {
        "project": project,
        "label": PROJECTS.get(project, {}).get("label", project),
        "protocol": data.get("protocol", "AICP/1.0"),
        "participants": data.get("participants", []),
        "message_count": len(data.get("messages", [])),
    }


@app.get("/threads/{project}/transcript")
def get_transcript(
    project: str,
    limit: int = 50,
    offset: int = 0,
    type: Optional[str] = None,
    from_agent: Optional[str] = None,
    order: str = "desc",
):
    """Read messages from a project thread. Returns newest-first by default."""
    data = load_index(project)
    messages = data.get("messages", [])

    # Filter
    if type:
        messages = [m for m in messages if m.get("type", "").upper() == type.upper()]
    if from_agent:
        messages = [m for m in messages if m.get("from", "") == from_agent]

    # Order
    if order == "desc":
        messages = list(reversed(messages))

    total = len(messages)
    messages = messages[offset:offset + limit]

    # Attach content
    journal_dir = get_journal_dir(project)
    results = []
    for m in messages:
        entry = dict(m)
        fpath = journal_dir / m.get("file", "")
        if fpath.exists():
            entry["content"] = fpath.read_text(encoding="utf-8")
        results.append(entry)

    return {
        "project": project,
        "total": total,
        "offset": offset,
        "limit": limit,
        "messages": results,
    }


@app.post("/threads/{project}/messages")
def create_message(project: str, msg: MessageCreate):
    """Write a new AICP message to a project thread. Auto-syncs to GitHub."""
    data = load_index(project)
    messages = data.get("messages", [])

    msg_id = next_msg_id(data, project)
    seq = next_seq(data)
    now = datetime.now(timezone.utc).astimezone()
    timestamp = now.strftime("%Y-%m-%dT%H:%M:%S%z")
    # Insert colon in timezone offset for ISO 8601
    timestamp = timestamp[:-2] + ":" + timestamp[-2:]
    date_str = now.strftime("%Y-%m-%d")
    type_lower = msg.type.lower()
    from_lower = msg.from_agent.lower()

    filename = f"{date_str}-{msg_id}-{type_lower}-{from_lower}.md"
    filepath = f"messages/{filename}"

    # Build AICP message content
    to_str = ", ".join(msg.to)
    lines = [
        f"$PROTO: AICP/1.0",
        f"$TYPE: {msg.type.upper()}",
        f"$ID: {msg_id}",
    ]
    if msg.ref:
        lines.append(f"$REF: {msg.ref}")
    lines += [
        f"$SEQ: {seq}",
        f"$FROM: {msg.from_agent}",
        f"$TO: {to_str}",
        f"$TIME: {timestamp}",
        f"$TASK: {msg.task}",
        f"$STATUS: {msg.status}",
    ]
    if msg.role:
        lines.append(f"$ROLE: {msg.role}")
    if msg.intent:
        lines.append(f"$INTENT: {msg.intent}")
    lines += [
        f"PROJECT: {project}",
        "",
        "---PAYLOAD---",
        "",
        msg.payload,
        "---END---",
    ]
    content = "\n".join(lines) + "\n"

    # Write message file
    msg_dir = get_journal_dir(project) / "messages"
    msg_dir.mkdir(exist_ok=True)
    (msg_dir / filename).write_text(content, encoding="utf-8")

    # Update index
    index_entry = {
        "id": msg_id,
        "type": msg.type.upper(),
        "from": msg.from_agent,
        "to": msg.to,
        "time": timestamp,
        "task": msg.task,
        "file": filepath,
        "ref": msg.ref or "NONE",
        "seq": seq,
    }
    messages.append(index_entry)
    data["messages"] = messages

    # Add new participants
    participants = data.get("participants", [])
    for agent in [msg.from_agent] + msg.to:
        if agent not in participants:
            participants.append(agent)
    data["participants"] = participants

    save_index(project, data)

    # Auto-sync to deploy repo and push
    sync_status = sync_to_deploy(project)

    return {
        "status": "created",
        "message": index_entry,
        "sync": sync_status,
    }


@app.get("/providers")
def list_providers():
    """List all configured agents and their backing providers."""
    return {"providers": PROVIDERS}


@app.get("/providers/{name}/status")
def provider_status(name: str):
    """Health check placeholder for a specific agent."""
    provider = next((p for p in PROVIDERS if p["name"].lower() == name.lower()), None)
    if not provider:
        raise HTTPException(404, f"Provider '{name}' not found")
    return {
        **provider,
        "status": "configured",
        "note": "Live health checks require API key validation (not yet implemented)",
    }
