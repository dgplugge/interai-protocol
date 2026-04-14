# Future API endpoints:
# POST /acal/expand   -- accepts ACAL text, returns AICP
# POST /acal/compress -- accepts AICP text, returns ACAL
# POST /acal/validate -- accepts AICP text, returns round-trip validation

"""ACAL <-> AICP bidirectional converter.

Implements parsing, expansion, compression, and round-trip validation
for the AICP Compressed Agent Language (ACAL) v0.1 specification.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

# ---------------------------------------------------------------------------
# Forward dictionaries
# ---------------------------------------------------------------------------

MSG_TYPES: dict[str, str] = {
    "RQ": "REQUEST",
    "RS": "RESPONSE",
    "AK": "ACK",
    "RV": "REVIEW",
    "UP": "UPDATE",
    "PL": "PLAN",
    "ER": "ERROR",
    "BS": "BRAINSTORM",
}

AGENTS: dict[str, str] = {
    "D": "Don",
    "P": "Pharos",
    "L": "Lodestar",
    "F": "Forge",
    "S": "SpinDrift",
    "T": "Trident",
    "U": "Lumen",
    "*": "ALL",
}

STATUS: dict[str, str] = {
    "C": "COMPLETE",
    "W": "IN_PROGRESS",
    "Q": "PENDING",
    "A": "APPROVED",
    "X": "ERROR",
    "H": "HOLD",
}

PRIORITY: dict[str, str] = {
    "!": "HIGH",
    ".": "MEDIUM",
    "_": "LOW",
}

ROLES: dict[str, str] = {
    "LC": "Lead Coder",
    "LD": "Lead Designer",
    "RV": "Reviewer",
    "OR": "Orchestrator",
    "AR": "Architect",
    "DA": "Design Advisor",
    "IL": "Implementation Lead",
}

PROJECTS: dict[str, str] = {
    "IP": "InterAI-Protocol",
    "OH": "OperatorHub",
    "SG": "StudyGuide",
    "PA": "PortfolioAnalysis",
}

DOMAINS: dict[str, str] = {
    "IP": "Multi-Agent Systems",
    "OH": "Flow Cytometry Lab Operations",
    "SG": "AI-Assisted Learning",
    "PA": "Financial portfolio tooling",
}

ACTIONS: dict[str, str] = {
    "+": "Add",
    "~": "Modify",
    "-": "Remove",
    "?": "Review",
    "!": "Approve",
    "^": "Refactor",
    ">": "Deploy",
    "#": "Test",
    "@": "Fix",
    "<": "Migrate",
    "&": "Route",
}

LAYERS: dict[str, str] = {
    "V": "View",
    "PR": "Presenter",
    "M": "Model",
    "SV": "Service",
    "AD": "Adapter",
    "MW": "Middleware",
    "DB": "Database",
    "CF": "Configuration",
    "IF": "Interface",
    "TS": "Test",
    "PX": "Parser",
    "WH": "Webhook",
    "RT": "Router",
}

PHRASES: dict[str, str] = {
    "ACK": "Receipt acknowledged",
    "APR": "Approved as proposed",
    "APR+": "Approved with amendments",
    "AWO": "Awaiting orchestrator decision",
    "AWR": "Awaiting review",
    "AWG": "Awaiting green light",
    "RFR": "Ready for review",
    "RFI": "Ready for implementation",
    "NOE": "No overlapping edits",
    "HTC": "Per Hub team consensus",
    "NGA": "Non-goals",
    "SCR": "Success criteria",
    "SLC": "Slice",
    "PHS": "Phase",
    "MVP": "Minimum viable product",
    "BLK": "Blocked",
    "DEF": "Deferred to future iteration",
    "BC": "Backward compatible",
    "ZD": "Zero dependencies",
    "NB": "No build step required",
    "FW": "Forward-compatible",
    "BRK": "Breaking change",
    "TD": "Technical debt",
}

# ---------------------------------------------------------------------------
# Reverse-lookup dictionaries (auto-generated)
# ---------------------------------------------------------------------------

MSG_TYPES_REV: dict[str, str] = {v: k for k, v in MSG_TYPES.items()}
AGENTS_REV: dict[str, str] = {v: k for k, v in AGENTS.items()}
STATUS_REV: dict[str, str] = {v: k for k, v in STATUS.items()}
# Also support the hyphenated variant found in real messages
STATUS_REV["IN-PROGRESS"] = "W"
PRIORITY_REV: dict[str, str] = {v: k for k, v in PRIORITY.items()}
ROLES_REV: dict[str, str] = {v: k for k, v in ROLES.items()}
PROJECTS_REV: dict[str, str] = {v: k for k, v in PROJECTS.items()}
DOMAINS_REV: dict[str, str] = {v: k for k, v in DOMAINS.items()}
ACTIONS_REV: dict[str, str] = {v: k for k, v in ACTIONS.items()}
LAYERS_REV: dict[str, str] = {v: k for k, v in LAYERS.items()}
PHRASES_REV: dict[str, str] = {v: k for k, v in PHRASES.items()}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_msg_number(msg_id: str) -> str:
    """Extract the numeric portion from a message ID like 'MSG-0010' -> '10'."""
    m = re.search(r"(\d+)$", msg_id.strip())
    if m:
        return str(int(m.group(1)))  # strip leading zeros
    return msg_id.strip()


def _format_msg_id(num: str | int) -> str:
    """Format a numeric ID back to MSG-NNNN format."""
    return f"MSG-{int(num):04d}"


def _now_iso() -> str:
    """Return current time in ISO 8601 format with timezone offset."""
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _split_acal_sections(text: str) -> tuple[str, str, str]:
    """Split an ACAL message into (header, payload, audit).

    Sections are separated by '---' lines.
    Returns empty strings for missing sections.
    """
    text = text.strip()
    parts = re.split(r"^---\s*$", text, flags=re.MULTILINE)
    header = parts[0].strip() if len(parts) > 0 else ""
    payload = parts[1].strip() if len(parts) > 1 else ""
    audit = parts[2].strip() if len(parts) > 2 else ""
    return header, payload, audit


# ---------------------------------------------------------------------------
# 1. ACAL Parser
# ---------------------------------------------------------------------------

def parse_acal(acal_text: str) -> dict:
    """Parse an ACAL message into structured fields.

    Parses the header line format:
        TYPE:ID>REF|FROM>TO|STATUS PRIORITY|ROLE|PROJECT|TASK|INTENT

    And optional payload/audit sections delimited by '---'.

    Returns:
        dict with keys: type, id, ref, from_agent, to_agents, status,
        priority, role, project, task, intent, operations, raw_payload,
        audit
    """
    header_line, payload, audit = _split_acal_sections(acal_text)

    result: dict = {
        "type": "",
        "id": "",
        "ref": "",
        "from_agent": "",
        "to_agents": [],
        "status": "",
        "priority": "!",  # default HIGH
        "role": [],
        "project": "",
        "task": "",
        "intent": "",
        "operations": [],
        "raw_payload": payload,
        "audit": audit,
    }

    # Split header by pipe
    parts = header_line.split("|")
    if len(parts) < 5:
        raise ValueError(
            f"Invalid ACAL header: expected at least 5 pipe-separated fields, "
            f"got {len(parts)}. Header: {header_line!r}"
        )

    # --- Field 0: TYPE:ID>REF ---
    type_id_ref = parts[0].strip()
    m = re.match(r"^([A-Z]{2}):(\w+)(?:>(\w+))?$", type_id_ref)
    if not m:
        raise ValueError(f"Invalid TYPE:ID>REF field: {type_id_ref!r}")
    result["type"] = m.group(1)
    result["id"] = m.group(2)
    result["ref"] = m.group(3) or ""

    # --- Field 1: FROM>TO ---
    from_to = parts[1].strip()
    if ">" not in from_to:
        raise ValueError(f"Invalid FROM>TO field: {from_to!r}")
    from_part, to_part = from_to.split(">", 1)
    result["from_agent"] = from_part.strip()
    result["to_agents"] = [a.strip() for a in to_part.split(",")]

    # --- Field 2: STATUS [PRIORITY] ---
    status_pri = parts[2].strip()
    if not status_pri:
        raise ValueError("Empty STATUS field")
    result["status"] = status_pri[0]
    if len(status_pri) > 1 and status_pri[1] in PRIORITY:
        result["priority"] = status_pri[1]
    # If no priority char, default remains "!" (HIGH)

    # --- Field 3: ROLE ---
    role_field = parts[3].strip()
    result["role"] = [r.strip() for r in role_field.split(",")]

    # --- Field 4: PROJECT ---
    result["project"] = parts[4].strip()

    # --- Field 5: TASK (optional) ---
    if len(parts) > 5:
        result["task"] = parts[5].strip()

    # --- Field 6: INTENT (optional) ---
    if len(parts) > 6:
        result["intent"] = parts[6].strip()

    # --- Parse operations from payload ---
    if payload:
        result["operations"] = parse_operations(payload)

    return result


# ---------------------------------------------------------------------------
# 4. Payload Operation Parser
# ---------------------------------------------------------------------------

_ACTION_CHARS = set(ACTIONS.keys())
# Sort layer codes longest first so "PR" matches before "P" (not a layer)
_LAYER_CODES_SORTED = sorted(LAYERS.keys(), key=len, reverse=True)
_LAYER_PATTERN = "|".join(re.escape(lc) for lc in _LAYER_CODES_SORTED)
_OP_RE = re.compile(
    rf"([+~\-?!^>#@<&])"           # action char
    rf"({_LAYER_PATTERN})"          # layer code
    r"\s+"                          # whitespace
    r"([^\s{]+)"                    # target (stop before whitespace or {)
    r"(?:\s*\{([^}]*)\})?"         # optional {params}
)


def parse_operations(payload: str) -> list[dict]:
    """Parse ACAL payload operations.

    Recognises patterns like:
        +IF IAgentConfig {read,display,verify}
        ~PR AgentHubPresenter
        #TS verify: all agents visible

    Operations may be separated by semicolons or newlines.

    Returns:
        list of dicts with keys: action, layer, target, params
    """
    results: list[dict] = []
    # Split on semicolons and newlines to find individual operation strings
    segments = re.split(r"[;\n]", payload)
    for segment in segments:
        segment = segment.strip()
        if not segment:
            continue
        m = _OP_RE.match(segment)
        if m:
            results.append({
                "action": m.group(1),
                "layer": m.group(2),
                "target": m.group(3),
                "params": m.group(4).strip() if m.group(4) else "",
            })
    return results


# ---------------------------------------------------------------------------
# 2. ACAL -> AICP Expander
# ---------------------------------------------------------------------------

def acal_to_aicp(
    acal_text: str,
    seq: Optional[int] = None,
    timestamp: Optional[str] = None,
) -> str:
    """Expand an ACAL message to full AICP format.

    Auto-generates $TIME if *timestamp* is not provided.
    Auto-generates $SEQ if *seq* is not provided (defaults to int(id)).
    Adds $PROTO: AICP/1.0 and derives DOMAIN from the PROJECT code.
    Expands all ACAL tokens (APR, RFR, SCR, etc.) found in the payload.

    Args:
        acal_text: The ACAL message string.
        seq: Optional explicit sequence number.
        timestamp: Optional ISO-8601 timestamp string.

    Returns:
        The expanded AICP message as a string.
    """
    parsed = parse_acal(acal_text)

    # Resolve codes to full values
    msg_type = MSG_TYPES.get(parsed["type"], parsed["type"])
    msg_id = _format_msg_id(parsed["id"])

    from_agent = AGENTS.get(parsed["from_agent"], parsed["from_agent"])
    to_agents = ", ".join(AGENTS.get(a, a) for a in parsed["to_agents"])

    status_full = STATUS.get(parsed["status"], parsed["status"])
    priority_full = PRIORITY.get(parsed["priority"], parsed["priority"])

    roles_full = ", ".join(ROLES.get(r, r) for r in parsed["role"])

    project_code = parsed["project"]
    project_full = PROJECTS.get(project_code, project_code)
    domain_full = DOMAINS.get(project_code, "")

    time_str = timestamp or _now_iso()

    if seq is not None:
        seq_val = seq
    else:
        try:
            seq_val = int(parsed["id"])
        except ValueError:
            seq_val = 0

    # Build header lines
    lines: list[str] = [
        "$PROTO: AICP/1.0",
        f"$TYPE: {msg_type}",
        f"$ID: {msg_id}",
    ]
    if parsed["ref"]:
        lines.append(f"$REF: {_format_msg_id(parsed['ref'])}")
    lines.append(f"$SEQ: {seq_val}")
    lines.append(f"$FROM: {from_agent}")
    lines.append(f"$TO: {to_agents}")
    lines.append(f"$TIME: {time_str}")
    if parsed["task"]:
        lines.append(f"$TASK: {parsed['task']}")
    lines.append(f"$STATUS: {status_full}")
    lines.append(f"$PRIORITY: {priority_full}")
    if roles_full:
        lines.append(f"$ROLE: {roles_full}")
    if parsed["intent"]:
        lines.append(f"$INTENT: {parsed['intent']}")
    lines.append(f"PROJECT: {project_full}")
    if domain_full:
        lines.append(f"DOMAIN: {domain_full}")

    # Expand payload tokens
    payload = _expand_payload_tokens(parsed["raw_payload"])

    lines.append("")
    lines.append("---PAYLOAD---")
    if payload:
        lines.append("")
        lines.append(payload)
    lines.append("")
    lines.append("---END---")

    # Audit / summary
    if parsed["audit"]:
        audit = parsed["audit"]
        if audit.startswith("S:"):
            lines.append("")
            lines.append(f"$SUMMARY: {audit[2:].strip()}")
        else:
            lines.append("")
            lines.append(audit)

    return "\n".join(lines) + "\n"


def _expand_payload_tokens(payload: str) -> str:
    """Expand ACAL phrase tokens in a payload string to their full forms."""
    if not payload:
        return payload

    result = payload

    # Expand SLC:N and PHS:N first (parameterized tokens)
    result = re.sub(r"\bSLC:(\S+)", lambda m: f"Slice {m.group(1)}", result)
    result = re.sub(r"\bPHS:(\S+)", lambda m: f"Phase {m.group(1)}", result)

    # Expand authority tokens IA:X, RA:X, OA:X
    result = re.sub(
        r"\bIA:([A-Z*])",
        lambda m: f"Implementation authority: {AGENTS.get(m.group(1), m.group(1))}",
        result,
    )
    result = re.sub(
        r"\bRA:([A-Z*])",
        lambda m: f"Review authority: {AGENTS.get(m.group(1), m.group(1))}",
        result,
    )
    result = re.sub(
        r"\bOA:([A-Z*])",
        lambda m: f"Orchestration authority: {AGENTS.get(m.group(1), m.group(1))}",
        result,
    )

    # Expand standalone phrase tokens (longest first to avoid partial matches)
    # APR+ must come before APR
    sorted_tokens = sorted(PHRASES.keys(), key=len, reverse=True)
    for token in sorted_tokens:
        # Skip SLC and PHS since we already handled them above
        if token in ("SLC", "PHS"):
            continue
        expanded = PHRASES[token]
        # Word-boundary match; tokens are uppercase so use case-sensitive
        result = re.sub(rf"\b{re.escape(token)}\b", expanded, result)

    return result


# ---------------------------------------------------------------------------
# 3. AICP -> ACAL Compressor
# ---------------------------------------------------------------------------

def aicp_to_acal(aicp_text: str) -> str:
    """Compress a standard AICP message to ACAL format.

    Strips $PROTO, $TIME, $SEQ, and DOMAIN (all recoverable).
    Compresses agent names, status, priority, type, and role to codes.
    Attempts to compress payload phrases to ACAL tokens.

    Args:
        aicp_text: The full AICP message string.

    Returns:
        The compressed ACAL message string.
    """
    headers, payload, audit_lines = _parse_aicp_raw(aicp_text)

    # Extract header values
    msg_type = MSG_TYPES_REV.get(headers.get("$TYPE", ""), headers.get("$TYPE", ""))
    msg_id = _extract_msg_number(headers.get("$ID", "0"))
    msg_ref = _extract_msg_number(headers.get("$REF", "")) if "$REF" in headers else ""

    from_agent = AGENTS_REV.get(headers.get("$FROM", ""), headers.get("$FROM", ""))
    to_raw = headers.get("$TO", "")
    to_agents = ",".join(
        AGENTS_REV.get(a.strip(), a.strip()) for a in to_raw.split(",")
    )

    status_raw = headers.get("$STATUS", "").replace("-", "_")
    status_code = STATUS_REV.get(status_raw, STATUS_REV.get(status_raw.upper(), status_raw))

    pri_raw = headers.get("$PRIORITY", "HIGH").upper()
    pri_code = PRIORITY_REV.get(pri_raw, "!")

    role_raw = headers.get("$ROLE", "")
    role_parts = [r.strip() for r in role_raw.split(",")]
    role_codes = ",".join(ROLES_REV.get(r, r) for r in role_parts if r)

    project_raw = headers.get("PROJECT", "")
    project_code = PROJECTS_REV.get(project_raw, project_raw)

    task = headers.get("$TASK", "")
    intent = headers.get("$INTENT", "")

    # Build header line
    id_ref = f"{msg_id}>{msg_ref}" if msg_ref else msg_id
    header_line = (
        f"{msg_type}:{id_ref}"
        f"|{from_agent}>{to_agents}"
        f"|{status_code}{pri_code}"
        f"|{role_codes}"
        f"|{project_code}"
    )
    if task:
        header_line += f"|{task}"
    if intent:
        header_line += f"|{intent}"

    # Compress payload
    compressed_payload = _compress_payload_tokens(payload)

    # Build output
    parts = [header_line]
    if compressed_payload:
        parts.append("---")
        parts.append(compressed_payload)
        parts.append("---")

    # Audit
    summary = ""
    for line in audit_lines:
        if line.startswith("$SUMMARY:"):
            summary = line[len("$SUMMARY:"):].strip()
            break
    if summary:
        parts.append(f"S:{summary}")

    return "\n".join(parts) + "\n"


def _parse_aicp_raw(text: str) -> tuple[dict[str, str], str, list[str]]:
    """Parse raw AICP text into (headers_dict, payload_str, audit_lines).

    Headers are key-value pairs before ---PAYLOAD---.
    Payload is text between ---PAYLOAD--- and ---END---.
    Audit lines are anything after ---END---.
    """
    headers: dict[str, str] = {}
    payload_lines: list[str] = []
    audit_lines: list[str] = []

    in_payload = False
    past_end = False

    for line in text.splitlines():
        stripped = line.strip()

        if stripped == "---PAYLOAD---":
            in_payload = True
            continue
        if stripped == "---END---":
            in_payload = False
            past_end = True
            continue

        if past_end:
            if stripped:
                audit_lines.append(stripped)
            continue

        if in_payload:
            payload_lines.append(line)
            continue

        # Header region
        if not stripped:
            continue
        # Parse $KEY: value  or  KEY: value
        m = re.match(r"^(\$?[A-Z_]+)\s*:\s*(.*)$", stripped)
        if m:
            headers[m.group(1)] = m.group(2).strip()

    payload = "\n".join(payload_lines).strip()
    return headers, payload, audit_lines


def _compress_payload_tokens(payload: str) -> str:
    """Compress common phrases in payload to ACAL tokens."""
    if not payload:
        return payload

    result = payload

    # Compress parameterized phrases first
    result = re.sub(r"\bSlice\s+(\S+)", r"SLC:\1", result, flags=re.IGNORECASE)
    result = re.sub(r"\bPhase\s+(\S+)", r"PHS:\1", result, flags=re.IGNORECASE)

    # Compress authority phrases
    for agent_name, agent_code in AGENTS_REV.items():
        if agent_name == "ALL":
            continue
        result = re.sub(
            rf"\bImplementation authority:\s*{re.escape(agent_name)}\b",
            f"IA:{agent_code}",
            result,
            flags=re.IGNORECASE,
        )
        result = re.sub(
            rf"\bReview authority:\s*{re.escape(agent_name)}\b",
            f"RA:{agent_code}",
            result,
            flags=re.IGNORECASE,
        )
        result = re.sub(
            rf"\bOrchestration authority:\s*{re.escape(agent_name)}\b",
            f"OA:{agent_code}",
            result,
            flags=re.IGNORECASE,
        )

    # Compress known phrases (longest first to avoid partial)
    sorted_phrases = sorted(PHRASES_REV.keys(), key=len, reverse=True)
    for phrase in sorted_phrases:
        token = PHRASES_REV[phrase]
        if token in ("SLC", "PHS"):
            continue  # handled above
        result = re.sub(re.escape(phrase), token, result, flags=re.IGNORECASE)

    # Common variations found in real messages
    result = re.sub(r"\bRECEIPT ACKNOWLEDGED\b", "ACK", result, flags=re.IGNORECASE)
    result = re.sub(r"\bACKNOWLEDGED\b", "ACK", result, flags=re.IGNORECASE)
    result = re.sub(r"\bREADY FOR REVIEW\b", "RFR", result, flags=re.IGNORECASE)
    result = re.sub(r"\bREADY FOR IMPLEMENTATION\b", "RFI", result, flags=re.IGNORECASE)
    result = re.sub(r"\bAPPROVED AS PROPOSED\b", "APR", result, flags=re.IGNORECASE)
    result = re.sub(
        r"\bAPPROVED WITH AMENDMENTS?\b", "APR+", result, flags=re.IGNORECASE
    )
    result = re.sub(
        r"\bAPPROVED WITH MINOR AMENDMENTS?\b", "APR+", result, flags=re.IGNORECASE
    )
    result = re.sub(
        r"\bAWAITING ORCHESTRATOR\b", "AWO", result, flags=re.IGNORECASE
    )
    result = re.sub(
        r"\bNO OVERLAPPING EDITS\b", "NOE", result, flags=re.IGNORECASE
    )
    result = re.sub(
        r"\bPER HUB TEAM CONSENSUS\b", "HTC", result, flags=re.IGNORECASE
    )
    result = re.sub(r"\bSUCCESS CRITERIA\b", "SCR", result, flags=re.IGNORECASE)
    result = re.sub(r"\bNON-?GOALS?\b", "NGA", result, flags=re.IGNORECASE)
    result = re.sub(r"\bBACKWARD COMPATIBLE\b", "BC", result, flags=re.IGNORECASE)
    result = re.sub(r"\bZERO DEPENDENCIES\b", "ZD", result, flags=re.IGNORECASE)
    result = re.sub(r"\bNO BUILD STEP REQUIRED\b", "NB", result, flags=re.IGNORECASE)
    result = re.sub(r"\bBREAKING CHANGE\b", "BRK", result, flags=re.IGNORECASE)
    result = re.sub(r"\bTECHNICAL DEBT\b", "TD", result, flags=re.IGNORECASE)

    return result


# ---------------------------------------------------------------------------
# 5. Round-trip Validator
# ---------------------------------------------------------------------------

def validate_roundtrip(aicp_text: str) -> tuple[bool, str]:
    """Compress an AICP message to ACAL, then expand back.

    Compares semantic equivalence of the original and reconstructed
    messages, ignoring whitespace, formatting, and auto-generated
    fields ($TIME, $SEQ, $PROTO).

    Args:
        aicp_text: The original AICP message string.

    Returns:
        Tuple of (is_equivalent, diff_report).
        is_equivalent is True when all semantically meaningful fields
        survive the round trip.
    """
    # Parse original
    orig_headers, orig_payload, _ = _parse_aicp_raw(aicp_text)

    # Compress then expand
    acal = aicp_to_acal(aicp_text)
    reconstructed = acal_to_aicp(
        acal,
        seq=int(orig_headers.get("$SEQ", 0)) if "$SEQ" in orig_headers else None,
        timestamp=orig_headers.get("$TIME"),
    )

    # Parse reconstructed
    recon_headers, recon_payload, _ = _parse_aicp_raw(reconstructed)

    # Fields to compare (skip auto-generated ones)
    compare_fields = ["$TYPE", "$ID", "$FROM", "$TO", "$STATUS", "$PRIORITY", "$ROLE"]
    # Also compare PROJECT and DOMAIN
    compare_fields += ["PROJECT", "DOMAIN"]

    diffs: list[str] = []
    for field in compare_fields:
        orig_val = _normalize(orig_headers.get(field, ""))
        recon_val = _normalize(recon_headers.get(field, ""))
        if orig_val != recon_val:
            diffs.append(f"  {field}: {orig_val!r} -> {recon_val!r}")

    # Compare $REF if present
    if "$REF" in orig_headers:
        orig_ref = _normalize(orig_headers["$REF"])
        recon_ref = _normalize(recon_headers.get("$REF", ""))
        if orig_ref != recon_ref:
            diffs.append(f"  $REF: {orig_ref!r} -> {recon_ref!r}")

    # Compare TASK and INTENT (these pass through as free text)
    for field in ["$TASK", "$INTENT"]:
        orig_val = orig_headers.get(field, "").strip()
        recon_val = recon_headers.get(field, "").strip()
        if orig_val != recon_val:
            diffs.append(f"  {field}: {orig_val!r} -> {recon_val!r}")

    if diffs:
        report = "Round-trip differences found:\n" + "\n".join(diffs)
        return False, report

    return True, "Round-trip successful: all semantic fields preserved."


def _normalize(value: str) -> str:
    """Normalize a header value for comparison.

    Strips whitespace, normalizes underscores/hyphens, uppercases.
    """
    return re.sub(r"[\s_-]+", "_", value.strip().upper())
