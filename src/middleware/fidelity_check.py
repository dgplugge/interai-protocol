"""
Summary fidelity check (Q3 from the Summarizer-Role design).

Forge's locked Q3 protocol (Round 5): for each committed AICP journal message
covered by a summary, validate against live fields only —
  - $DECISION, when present, must be in {CHALLENGE, CLARIFY, EXECUTE}.
  - $TASK must be non-empty.
  - $STATUS must be one of the expected values (below).
  - Payload must match any available baseline (e.g. chunk_index.content).

No invented fields, no unmeasured thresholds. If any check fails, the caller
reverts to raw-last-N instead of trusting the summary.

This module is validation-only. It does not generate summaries, does not call
LLMs, and does not modify journal files.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from middleware.decision_validator import VALID_DECISIONS
from middleware.summary_index import get_chunk


EXPECTED_STATUS = {"OPEN", "IN_PROGRESS", "COMPLETE", "CLOSED", "PENDING"}

_PAYLOAD_OPEN = "---PAYLOAD---"
_PAYLOAD_CLOSE = "---END---"


@dataclass
class FidelityIssue:
    message_id: str
    code: str
    detail: str

    def to_dict(self) -> dict:
        return {"message_id": self.message_id, "code": self.code, "detail": self.detail}


@dataclass
class FidelityReport:
    messages_checked: int = 0
    issues: list[FidelityIssue] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.issues

    def to_dict(self) -> dict:
        return {
            "messages_checked": self.messages_checked,
            "passed": self.passed,
            "issues": [i.to_dict() for i in self.issues],
        }


def parse_aicp_file(path: Path | str) -> dict:
    """Parse an AICP message file from disk into a dict.

    Recognizes `$FIELD: value` header lines and the `---PAYLOAD---` /
    `---END---` delimiters. Unrecognized lines before PAYLOAD are ignored.
    Missing fields simply absent from the returned dict.
    """
    text = Path(path).read_text(encoding="utf-8")
    fields: dict = {}
    lines = text.splitlines()

    in_payload = False
    payload_lines: list[str] = []

    for line in lines:
        stripped = line.rstrip()
        if not in_payload:
            if stripped == _PAYLOAD_OPEN:
                in_payload = True
                continue
            if stripped.startswith("$") and ":" in stripped:
                key, _, value = stripped.partition(":")
                fields[key.strip()] = value.strip()
        else:
            if stripped == _PAYLOAD_CLOSE:
                break
            payload_lines.append(line)

    # Strip surrounding blank lines from payload but preserve internal structure.
    fields["payload"] = "\n".join(payload_lines).strip("\n")
    return fields


def check_message(msg: dict, baseline: Optional[str] = None) -> list[FidelityIssue]:
    """Run Forge's fidelity protocol on a single parsed AICP message.

    `baseline`, if provided, is the payload text the message is expected to
    match (typically the content stored in the chunk_index). An exact-string
    comparison is used — divergence is reported as PAYLOAD_DRIFT.

    Returns a list of issues; empty list means the message passed.
    """
    issues: list[FidelityIssue] = []
    msg_id = msg.get("$ID", "UNKNOWN")

    # $DECISION: validate only if present. Not every message carries one.
    decision = msg.get("$DECISION", "").upper().strip()
    if decision and decision not in VALID_DECISIONS:
        issues.append(FidelityIssue(
            message_id=msg_id,
            code="INVALID_DECISION",
            detail=f"$DECISION value '{decision}' not in {sorted(VALID_DECISIONS)}",
        ))

    # $TASK: must be non-empty
    task = msg.get("$TASK", "").strip()
    if not task:
        issues.append(FidelityIssue(
            message_id=msg_id,
            code="EMPTY_TASK",
            detail="$TASK is missing or empty",
        ))

    # $STATUS: must be in the expected set (when present)
    status = msg.get("$STATUS", "").upper().strip()
    if not status:
        issues.append(FidelityIssue(
            message_id=msg_id,
            code="MISSING_STATUS",
            detail="$STATUS header is absent",
        ))
    elif status not in EXPECTED_STATUS:
        issues.append(FidelityIssue(
            message_id=msg_id,
            code="UNKNOWN_STATUS",
            detail=f"$STATUS value '{status}' not in {sorted(EXPECTED_STATUS)}",
        ))

    # Payload baseline comparison — only when a baseline was supplied
    if baseline is not None:
        actual = (msg.get("payload") or "").strip()
        expected = (baseline or "").strip()
        if actual != expected:
            issues.append(FidelityIssue(
                message_id=msg_id,
                code="PAYLOAD_DRIFT",
                detail=f"payload differs from baseline "
                       f"(actual={len(actual)} chars, baseline={len(expected)} chars)",
            ))

    return issues


def check_file(path: Path | str, baseline: Optional[str] = None) -> list[FidelityIssue]:
    """Parse one AICP file and run fidelity checks on it."""
    msg = parse_aicp_file(path)
    return check_message(msg, baseline=baseline)


def check_project(
    journal_dir: Path | str,
    index_db: Optional[Path | str] = None,
    limit: Optional[int] = None,
) -> FidelityReport:
    """Run fidelity on every message file in a project's journal directory.

    If `index_db` is supplied, each message's parsed payload is compared to
    the chunk_index row for that $ID (baseline mode). Without an index DB,
    payload comparison is skipped and only header-level checks run.

    `limit` caps the number of files checked; useful when only recent entries
    matter. Files are sorted by name (which is date-prefixed), so the most
    recent N entries are taken when limit is set.
    """
    journal_dir = Path(journal_dir)
    messages_dir = journal_dir / "messages"
    report = FidelityReport()
    if not messages_dir.is_dir():
        return report

    files = sorted(messages_dir.glob("*.md"))
    if limit is not None:
        files = files[-limit:]

    for f in files:
        msg = parse_aicp_file(f)
        report.messages_checked += 1

        baseline: Optional[str] = None
        if index_db is not None:
            msg_id = msg.get("$ID", "")
            if msg_id:
                chunk = get_chunk(index_db, msg_id)
                if chunk is not None:
                    baseline = chunk.content

        report.issues.extend(check_message(msg, baseline=baseline))

    return report
