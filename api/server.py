"""
AICP Phase 2 — REST API Server
Provides dynamic read/write access to AICP journals.
Auto-syncs to GitHub (aicp-journals repo) on every write.
"""

import json
import os
import subprocess
import shutil
import sys
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add src to path for middleware imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from middleware.rate_limiter import ProviderRateLimiter
from middleware.retry_handler import RetryConfig, PROVIDER_RETRY_CONFIGS, RETRYABLE_STATUS_CODES
from middleware.token_estimator import estimate_tokens, estimate_dispatch_tokens, suggest_history_trim
from kernel.loader import KernelLoader
from acal.verifier import verify_roundtrip
from middleware.decision_validator import validate_decision, extract_decision_from_content, VALID_DECISIONS
from middleware.thread_compactor import ThreadTracker

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
    version="2.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Rate Limiter (shared instance) ---
rate_limiter = ProviderRateLimiter(default_delay=3.0)

# --- Kernel Loader (shared instance) ---
KERNELS_DIR = Path(__file__).parent.parent / "kernels"
kernel_loader = KernelLoader(KERNELS_DIR)

# --- Thread Compactor (shared instance) ---
SUMMARIES_DIR = Path(__file__).parent.parent / "summaries"
thread_tracker = ThreadTracker(summary_dir=SUMMARIES_DIR, threshold=10)


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


class TurnMode(str, Enum):
    PARALLEL = "parallel"          # All agents respond simultaneously
    SEQUENTIAL = "sequential"      # Agents respond in order, no cross-visibility
    ROUND_ROBIN = "round-robin"    # Each agent sees prior responses before replying


class DispatchRequest(BaseModel):
    prompt: str                        # The message/question to dispatch
    task: str                          # $TASK description
    turn_mode: TurnMode = TurnMode.ROUND_ROBIN
    agents: list[str] = []             # Agent names to include (empty = all)
    ref: Optional[str] = None         # $REF — parent message ID


class DispatchResult(BaseModel):
    dispatch_id: str
    turn_mode: str
    agents_dispatched: list[str]
    prompt_message_id: str
    status: str


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
        "version": "2.3.0",
        "phase": 2,
        "slices_complete": "1-5",
        "endpoints": [
            "GET    /threads",
            "POST   /threads",
            "GET    /threads/{project}",
            "GET    /threads/{project}/transcript",
            "GET    /threads/{project}/stats",
            "POST   /threads/{project}/messages",
            "POST   /threads/{project}/dispatch",
            "DELETE /threads/{project}",
            "GET    /providers",
            "GET    /providers/{name}/status",
            "GET    /health",
            "GET    /rate-limits",
            "POST   /estimate-tokens",
            "POST   /api/acal/verify",
            "GET    /kernels",
            "POST   /api/validate-decision",
            "GET    /threads/{project}/summary",
            "POST   /threads/{project}/compact",
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

    # --- Slice 8.6: $DECISION validation on RESPONSE messages ---
    if msg.type.upper() == "RESPONSE":
        decision = extract_decision_from_content(msg.payload)
        validation_msg = {
            "type": msg.type,
            "id": msg_id,
            "decision": decision or "",
        }
        error = validate_decision(validation_msg)
        if error:
            raise HTTPException(400, error.to_dict())

    # --- Slice 8.5: Track message in thread compactor ---
    thread_tracker.add_message(project, {
        "id": msg_id,
        "from": msg.from_agent,
        "to": msg.to,
        "task": msg.task,
        "status": msg.status,
        "time": timestamp,
        "content": msg.payload[:500],
        "decision": extract_decision_from_content(msg.payload) or "",
        "seq": seq,
    })

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


@app.post("/threads")
def create_thread(body: ThreadCreate):
    """Create a new project thread with journal directory and index."""
    key = body.project
    if key in PROJECTS:
        raise HTTPException(409, f"Project '{key}' already exists")

    # Create directory structure
    project_dir = JOURNALS_ROOT / key
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "messages").mkdir(exist_ok=True)

    # Create journal index
    label = key.replace("-", " ").replace("_", " ").title()
    index_data = {
        "protocol": "AICP/1.0",
        "project": key,
        "participants": body.participants or ["Don"],
        "messages": [],
    }
    (project_dir / "journal-index.json").write_text(
        json.dumps(index_data, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Register in runtime config
    PROJECTS[key] = {"label": label}

    # Sync to deploy repo
    sync_status = sync_to_deploy(key)

    return {
        "status": "created",
        "project": key,
        "label": label,
        "participants": index_data["participants"],
        "sync": sync_status,
    }


@app.delete("/threads/{project}")
def archive_thread(project: str):
    """Archive a project thread by marking it inactive. Does not delete data."""
    data = load_index(project)
    data["archived"] = True
    data["archived_at"] = datetime.now(timezone.utc).astimezone().isoformat()
    save_index(project, data)

    # Sync archive status
    sync_status = sync_to_deploy(project)

    return {
        "status": "archived",
        "project": project,
        "message_count": len(data.get("messages", [])),
        "sync": sync_status,
    }


@app.get("/threads/{project}/stats")
def thread_stats(project: str):
    """Get statistics for a project thread."""
    data = load_index(project)
    messages = data.get("messages", [])

    # Count by type
    type_counts = {}
    sender_counts = {}
    for m in messages:
        t = m.get("type", "UNKNOWN").upper()
        type_counts[t] = type_counts.get(t, 0) + 1
        s = m.get("from", "Unknown")
        sender_counts[s] = sender_counts.get(s, 0) + 1

    # Date range
    times = [m.get("time", "") for m in messages if m.get("time")]
    first_msg = times[0] if times else None
    last_msg = times[-1] if times else None

    return {
        "project": project,
        "total_messages": len(messages),
        "participants": data.get("participants", []),
        "archived": data.get("archived", False),
        "by_type": type_counts,
        "by_sender": sender_counts,
        "first_message": first_msg,
        "last_message": last_msg,
    }


@app.post("/threads/{project}/dispatch")
def dispatch_round(
    project: str,
    req: DispatchRequest,
    kernel: Optional[str] = Query(
        default=None,
        description="Name of a context kernel to inject (e.g. 'acal-dev')",
    ),
):
    """
    Dispatch a prompt to agents in the specified turn mode.

    This creates the orchestrator's prompt message, then sets up
    the dispatch plan. Actual agent API calls happen via the Hub
    (VB.NET app) — this endpoint records the dispatch intent and
    turn configuration so the Hub knows how to execute.

    Optional query parameter ``kernel`` loads a context kernel from
    the kernels/ directory and prepends it to the dispatch payload
    as a system-prompt preamble.

    Turn modes:
    - PARALLEL:    All agents respond simultaneously, no cross-visibility
    - SEQUENTIAL:  Agents respond in $TO order, no cross-visibility
    - ROUND_ROBIN: Each agent sees prior agents' responses (default)
    """
    data = load_index(project)

    # --- Kernel injection (optional) ---
    kernel_info: dict | None = None
    kernel_preamble = ""
    if kernel:
        try:
            kernel_data = kernel_loader.load(kernel)
            kernel_preamble = kernel_data.to_prompt()
            budget = kernel_loader.check_budget(kernel_data)
            kernel_info = {
                "name": kernel_data.name,
                "label": kernel_data.label,
                "version": kernel_data.version,
                "token_estimate": kernel_data.token_estimate,
                "within_budget": budget["within_budget"],
            }
        except FileNotFoundError:
            raise HTTPException(404, f"Kernel '{kernel}' not found")
        except ValueError as exc:
            raise HTTPException(422, f"Kernel '{kernel}' is malformed: {exc}")

    # Determine which agents to dispatch to
    if req.agents:
        agent_names = req.agents
    else:
        agent_names = [p["name"] for p in PROVIDERS if p["role"] != "Pending Setup"]

    # Create the orchestrator's prompt message
    msg_id = next_msg_id(data, project)
    seq = next_seq(data)
    now = datetime.now(timezone.utc).astimezone()
    timestamp = now.strftime("%Y-%m-%dT%H:%M:%S%z")
    timestamp = timestamp[:-2] + ":" + timestamp[-2:]
    date_str = now.strftime("%Y-%m-%d")

    filename = f"{date_str}-{msg_id}-dispatch-don.md"
    filepath = f"messages/{filename}"

    # Build dispatch payload
    dispatch_id = f"DISPATCH-{msg_id}"
    to_str = ", ".join(agent_names)
    lines = [
        "$PROTO: AICP/1.0",
        "$TYPE: REQUEST",
        f"$ID: {msg_id}",
    ]
    if req.ref:
        lines.append(f"$REF: {req.ref}")
    lines += [
        f"$SEQ: {seq}",
        "$FROM: Don",
        f"$TO: {to_str}",
        f"$TIME: {timestamp}",
        f"$TASK: {req.task}",
        "$STATUS: IN_PROGRESS",
        "$ROLE: Orchestrator",
        f"$INTENT: Dispatch ({req.turn_mode.value}) to {len(agent_names)} agents",
        f"PROJECT: {project}",
        f"TURN_MODE: {req.turn_mode.value}",
        f"DISPATCH_ID: {dispatch_id}",
        "",
        "---PAYLOAD---",
        "",
    ]

    # Prepend kernel content as system-prompt preamble if provided
    if kernel_preamble:
        lines += [
            "---KERNEL_PREAMBLE---",
            "",
            kernel_preamble,
            "",
            "---END_KERNEL_PREAMBLE---",
            "",
        ]

    lines += [
        req.prompt,
        "",
        f"[Dispatch Mode: {req.turn_mode.value}]",
        f"[Agents: {to_str}]",
    ]

    if req.turn_mode == TurnMode.ROUND_ROBIN:
        lines.append("[Each agent will see prior responses before replying]")
    elif req.turn_mode == TurnMode.SEQUENTIAL:
        lines.append("[Agents respond in order listed, no cross-visibility]")
    else:
        lines.append("[All agents respond simultaneously]")

    lines += ["---END---"]
    content = "\n".join(lines) + "\n"

    # Write message file
    msg_dir = get_journal_dir(project) / "messages"
    msg_dir.mkdir(exist_ok=True)
    (msg_dir / filename).write_text(content, encoding="utf-8")

    # Update index
    index_entry = {
        "id": msg_id,
        "type": "REQUEST",
        "from": "Don",
        "to": agent_names,
        "time": timestamp,
        "task": req.task,
        "file": filepath,
        "ref": req.ref or "NONE",
        "seq": seq,
        "dispatch_id": dispatch_id,
        "turn_mode": req.turn_mode.value,
    }
    messages = data.get("messages", [])
    messages.append(index_entry)
    data["messages"] = messages
    save_index(project, data)

    # Sync
    sync_status = sync_to_deploy(project)

    result = {
        "status": "dispatched",
        "dispatch_id": dispatch_id,
        "turn_mode": req.turn_mode.value,
        "agents": agent_names,
        "prompt_message_id": msg_id,
        "sync": sync_status,
    }
    if kernel_info:
        result["kernel"] = kernel_info
    return result


@app.get("/providers")
def list_providers():
    """List all configured agents and their backing providers."""
    return {"providers": PROVIDERS}


@app.get("/providers/{name}/status")
def provider_status(name: str):
    """Health check for a specific agent including rate limit stats."""
    provider = next((p for p in PROVIDERS if p["name"].lower() == name.lower()), None)
    if not provider:
        raise HTTPException(404, f"Provider '{name}' not found")

    # Get rate limiter stats for this provider's platform
    provider_key = provider["provider"].lower()
    limiter_stats = rate_limiter.get_stats(provider_key)

    # Get retry config
    retry_config = PROVIDER_RETRY_CONFIGS.get(provider_key, RetryConfig())

    return {
        **provider,
        "status": "configured",
        "rate_limiter": limiter_stats,
        "retry_config": {
            "max_retries": retry_config.max_retries,
            "base_delay": retry_config.base_delay,
            "max_delay": retry_config.max_delay,
            "backoff_factor": retry_config.backoff_factor,
        },
    }


# --- Middleware Endpoints ---

@app.get("/health")
def health_check():
    """Overall system health check."""
    return {
        "status": "healthy",
        "version": "2.3.0",
        "phase": 2,
        "slices_complete": "1-5",
        "rate_limiter": rate_limiter.get_stats(),
        "providers_configured": len(PROVIDERS),
        "projects_active": len([
            k for k in PROJECTS
            if (JOURNALS_ROOT / k).exists()
        ]),
    }


@app.get("/rate-limits")
def get_rate_limits():
    """View current rate limiting stats and configuration."""
    return {
        "limiter_stats": rate_limiter.get_stats(),
        "provider_delays": rate_limiter.provider_delays,
        "retry_configs": {
            name: {
                "max_retries": cfg.max_retries,
                "base_delay": cfg.base_delay,
                "max_delay": cfg.max_delay,
                "backoff_factor": cfg.backoff_factor,
                "retryable_codes": list(RETRYABLE_STATUS_CODES),
            }
            for name, cfg in PROVIDER_RETRY_CONFIGS.items()
        },
    }


class TokenEstimateRequest(BaseModel):
    system_prompt: str = ""
    conversation_history: list[str] = []
    current_prompt: str = ""
    provider: str = ""


@app.post("/estimate-tokens")
def estimate_tokens_endpoint(req: TokenEstimateRequest):
    """Estimate token usage for a planned dispatch."""
    estimate = estimate_dispatch_tokens(
        system_prompt=req.system_prompt,
        conversation_history=req.conversation_history,
        current_prompt=req.current_prompt,
        provider=req.provider or None,
    )

    # Also provide trim suggestions if history is large
    trim = suggest_history_trim(
        conversation_history=req.conversation_history,
        provider=req.provider or None,
    )

    return {
        "estimate": estimate,
        "trim_suggestion": trim,
    }


# --- Kernel Endpoints ---

@app.get("/kernels")
def list_kernels():
    """List available context kernels."""
    names = kernel_loader.list_kernels()
    kernels = []
    for name in names:
        try:
            k = kernel_loader.load(name)
            budget = kernel_loader.check_budget(k)
            kernels.append({
                "name": k.name,
                "label": k.label,
                "version": k.version,
                "updated": k.updated,
                "task": k.task,
                "token_estimate": k.token_estimate,
                "within_budget": budget["within_budget"],
            })
        except (ValueError, FileNotFoundError):
            kernels.append({"name": name, "error": "malformed or missing"})
    return {"kernels": kernels}


# --- ACAL Verification Endpoint ---


class AcalVerifyRequest(BaseModel):
    aicp_message: str  # Full AICP message text to verify


@app.post("/api/acal/verify")
def acal_verify(req: AcalVerifyRequest):
    """Verify ACAL round-trip fidelity for an AICP message.

    Compresses the message to ACAL, expands it back, and compares
    all semantic fields. Returns pass/fail, compression ratio, and
    any field-level mismatches.
    """
    result = verify_roundtrip(req.aicp_message)
    return result.to_dict()


# --- Slice 8.6: Decision Validation Endpoint ---


class DecisionValidateRequest(BaseModel):
    type: str
    id: str = ""
    decision: str = ""


@app.post("/api/validate-decision")
def validate_decision_endpoint(req: DecisionValidateRequest):
    """Validate a $DECISION header value.

    Only enforces on RESPONSE messages. Returns validation result.
    """
    error = validate_decision(req.model_dump())
    if error:
        raise HTTPException(400, error.to_dict())
    return {
        "valid": True,
        "type": req.type,
        "decision": req.decision,
        "allowed_values": sorted(VALID_DECISIONS),
    }


# --- Slice 8.5: Thread Compaction Endpoints ---


@app.get("/threads/{project}/summary")
def get_thread_summary(project: str):
    """Get the compacted summary for a project thread, if available."""
    summary = thread_tracker.load_summary(project)
    if summary is None:
        return {
            "project": project,
            "summary": None,
            "message_count_since_compact": thread_tracker.get_count(project),
            "threshold": thread_tracker.threshold,
        }
    return {
        "project": project,
        "summary": summary.to_dict(),
        "message_count_since_compact": thread_tracker.get_count(project),
        "threshold": thread_tracker.threshold,
        "context_prompt": summary.to_prompt(),
    }


@app.post("/threads/{project}/compact")
def compact_thread(project: str):
    """Manually trigger thread compaction for a project.

    Generates a summary from tracked messages and saves as sidecar JSON.
    Typically called by the last agent in turn order after a round completes.
    """
    count = thread_tracker.get_count(project)
    if count == 0:
        raise HTTPException(400, f"No tracked messages for project '{project}'")

    summary = thread_tracker.compact(project)

    # Update kernel if one exists for this project
    kernel_update = None
    try:
        kernel_name = project.lower().replace("-", "-").replace(" ", "-")
        kernel_names = kernel_loader.list_kernels()
        matching = [k for k in kernel_names if project.lower().replace("-", "") in k.replace("-", "")]
        if matching:
            kernel_update = {
                "kernel": matching[0],
                "note": "Kernel STATE should be updated with this summary",
            }
    except Exception:
        pass

    return {
        "status": "compacted",
        "project": project,
        "summary": summary.to_dict(),
        "messages_compacted": summary.message_count,
        "kernel_update": kernel_update,
    }
