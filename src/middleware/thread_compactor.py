"""
Slice 8.5 — Thread Cache Compaction

Tracks message count per thread. When threshold is reached (default N=10),
generates a summary object containing decisions, open tasks, and constraints.

The summary is stored as a JSON sidecar file per thread and is used by the
routing layer to provide compressed context for subsequent dispatches.

Design decisions (per Hub consensus):
  - Routing layer owns summary generation (not agents)
  - Last agent in turn order is the only summarizer
  - Summary updates the Context Kernel's STATE/MEMORY sections
  - JSON format (CBOR optimization deferred to future slice)
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# Default compaction threshold
DEFAULT_THRESHOLD = 10


class ThreadSummary:
    """Represents a compacted summary of a thread's messages."""

    def __init__(self):
        self.thread_id: str = ""
        self.message_count: int = 0
        self.time_range: list[str] = []  # [earliest_time, latest_time]
        self.decisions: list[dict] = []  # [{agent, decision, message_id}]
        self.open_tasks: list[str] = []
        self.constraints: list[str] = []
        self.participants: list[str] = []
        self.last_compacted_at: str = ""
        self.last_compacted_seq: int = 0

    def to_dict(self) -> dict:
        return {
            "thread_id": self.thread_id,
            "message_count": self.message_count,
            "time_range": self.time_range,
            "decisions": self.decisions,
            "open_tasks": self.open_tasks,
            "constraints": self.constraints,
            "participants": self.participants,
            "last_compacted_at": self.last_compacted_at,
            "last_compacted_seq": self.last_compacted_seq,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ThreadSummary":
        s = cls()
        s.thread_id = data.get("thread_id", "")
        s.message_count = data.get("message_count", 0)
        s.time_range = data.get("time_range", [])
        s.decisions = data.get("decisions", [])
        s.open_tasks = data.get("open_tasks", [])
        s.constraints = data.get("constraints", [])
        s.participants = data.get("participants", [])
        s.last_compacted_at = data.get("last_compacted_at", "")
        s.last_compacted_seq = data.get("last_compacted_seq", 0)
        return s

    def to_prompt(self) -> str:
        """Render the summary as a prompt-friendly string for kernel injection."""
        lines = [
            f"Thread Summary ({self.thread_id})",
            f"Messages: {self.message_count} | Range: {' to '.join(self.time_range) if self.time_range else 'N/A'}",
            f"Participants: {', '.join(self.participants)}",
        ]
        if self.decisions:
            lines.append("Decisions:")
            for d in self.decisions:
                lines.append(f"  - {d.get('agent', '?')}: {d.get('decision', '?')} ({d.get('message_id', '')})")
        if self.open_tasks:
            lines.append("Open Tasks:")
            for t in self.open_tasks:
                lines.append(f"  - {t}")
        if self.constraints:
            lines.append("Constraints:")
            for c in self.constraints:
                lines.append(f"  - {c}")
        return "\n".join(lines)


class ThreadTracker:
    """
    Tracks messages per thread and triggers compaction at threshold.

    Usage:
        tracker = ThreadTracker(summary_dir="path/to/summaries")
        tracker.add_message(thread_id, message_dict)
        if tracker.should_compact(thread_id):
            summary = tracker.compact(thread_id)
    """

    def __init__(
        self,
        summary_dir: str | Path = ".",
        threshold: int = DEFAULT_THRESHOLD,
    ):
        self.summary_dir = Path(summary_dir)
        self.threshold = threshold
        self.threads: dict[str, list[dict]] = {}  # thread_id -> [messages]

    def add_message(self, thread_id: str, message: dict):
        """Add a message to the tracked thread."""
        if thread_id not in self.threads:
            self.threads[thread_id] = []
        self.threads[thread_id].append(message)

    def get_count(self, thread_id: str) -> int:
        """Get the current message count for a thread."""
        return len(self.threads.get(thread_id, []))

    def should_compact(self, thread_id: str) -> bool:
        """Check if a thread has reached the compaction threshold."""
        return self.get_count(thread_id) >= self.threshold

    def compact(self, thread_id: str) -> ThreadSummary:
        """
        Generate a summary from the thread's messages and save as sidecar JSON.

        Returns the generated ThreadSummary.
        """
        messages = self.threads.get(thread_id, [])
        if not messages:
            raise ValueError(f"No messages in thread '{thread_id}'")

        summary = self._generate_summary(thread_id, messages)

        # Save sidecar JSON
        self.summary_dir.mkdir(parents=True, exist_ok=True)
        sidecar_path = self.summary_dir / f"{thread_id}.summary.json"
        sidecar_path.write_text(
            json.dumps(summary.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # Reset thread messages (keep only the summary reference)
        self.threads[thread_id] = []

        return summary

    def load_summary(self, thread_id: str) -> Optional[ThreadSummary]:
        """Load an existing summary from the sidecar file."""
        sidecar_path = self.summary_dir / f"{thread_id}.summary.json"
        if not sidecar_path.exists():
            return None
        data = json.loads(sidecar_path.read_text(encoding="utf-8"))
        return ThreadSummary.from_dict(data)

    def get_context(self, thread_id: str) -> str:
        """
        Get the best available context for a thread.

        If a summary exists, returns summary + recent messages.
        Otherwise returns all tracked messages as context.
        """
        summary = self.load_summary(thread_id)
        recent = self.threads.get(thread_id, [])

        parts = []
        if summary:
            parts.append(summary.to_prompt())
            parts.append("")

        if recent:
            parts.append(f"Recent messages ({len(recent)}):")
            for msg in recent:
                sender = msg.get("from", msg.get("$FROM", "?"))
                content = msg.get("content", msg.get("payload", ""))
                if len(content) > 200:
                    content = content[:197] + "..."
                parts.append(f"  [{sender}]: {content}")

        return "\n".join(parts)

    def _generate_summary(
        self, thread_id: str, messages: list[dict]
    ) -> ThreadSummary:
        """Extract summary data from messages."""
        summary = ThreadSummary()
        summary.thread_id = thread_id
        summary.message_count = len(messages)
        summary.last_compacted_at = datetime.now(timezone.utc).isoformat()

        # Time range
        times = []
        for m in messages:
            t = m.get("time", m.get("$TIME", m.get("timestamp", "")))
            if t:
                times.append(str(t))
        if times:
            summary.time_range = [times[0], times[-1]]

        # Participants
        participants = set()
        for m in messages:
            sender = m.get("from", m.get("$FROM", ""))
            if sender:
                participants.add(sender)
        summary.participants = sorted(participants)

        # Decisions — extract from messages that have $DECISION
        for m in messages:
            decision = m.get("decision", m.get("$DECISION", ""))
            if decision:
                summary.decisions.append({
                    "agent": m.get("from", m.get("$FROM", "?")),
                    "decision": decision,
                    "message_id": m.get("id", m.get("$ID", "")),
                })

        # Sequence tracking
        seqs = [m.get("seq", m.get("$SEQ", 0)) for m in messages]
        seqs = [s for s in seqs if isinstance(s, int) and s > 0]
        if seqs:
            summary.last_compacted_seq = max(seqs)

        # Open tasks — extract from messages with status OPEN or IN_PROGRESS
        for m in messages:
            status = (m.get("status", m.get("$STATUS", "")) or "").upper()
            if status in ("OPEN", "IN_PROGRESS"):
                task = m.get("task", m.get("$TASK", ""))
                if task and task not in summary.open_tasks:
                    summary.open_tasks.append(task)

        return summary
