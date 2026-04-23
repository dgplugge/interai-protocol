"""
Summary metadata tracking (Q2 and Q8 from the Summarizer-Role design).

Tracks, per project:
- `last_entry_id`: the $ID of the newest journal entry covered by the current
  summary. Empty string when no summary has ever been written.
- `entries_since_last_summary`: counter incremented on every journal write;
  resets to 0 when a new summary is written. Used for threshold-based firing
  of the background summarizer.
- `last_updated`: ISO-8601 timestamp of the most recent meta mutation.

Stored as JSON at `<summary_dir>/<project>/summary_meta.json` — alongside
the `summary.yml` produced by `summary_store.py`.

This module is bookkeeping only. It does not generate summaries, does not
trigger LLM calls, and does not inject context into dispatches. Producer
and consumer concerns live elsewhere.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


_MSG_ID_TAIL = re.compile(r"-(\d+)$")


def _id_num(msg_id: str) -> int:
    """Extract the numeric tail of an AICP message ID for order-safe comparison.

    "MSG-0169" -> 169. Returns -1 for empty or malformed IDs so that missing
    coverage sorts below any real entry.
    """
    if not msg_id:
        return -1
    m = _MSG_ID_TAIL.search(msg_id)
    if m is None:
        return -1
    try:
        return int(m.group(1))
    except ValueError:
        return -1


@dataclass
class SummaryMeta:
    last_entry_id: str = ""
    entries_since_last_summary: int = 0
    last_updated: str = ""

    def to_dict(self) -> dict:
        return {
            "last_entry_id": self.last_entry_id,
            "entries_since_last_summary": self.entries_since_last_summary,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SummaryMeta":
        m = cls()
        m.last_entry_id = str(data.get("last_entry_id", ""))
        m.entries_since_last_summary = int(data.get("entries_since_last_summary", 0))
        m.last_updated = str(data.get("last_updated", ""))
        return m

    def touch(self) -> None:
        self.last_updated = datetime.now(timezone.utc).isoformat()


def meta_path(summary_dir: Path | str, project: str) -> Path:
    return Path(summary_dir) / project / "summary_meta.json"


def read_meta(summary_dir: Path | str, project: str) -> Optional[SummaryMeta]:
    path = meta_path(summary_dir, project)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    return SummaryMeta.from_dict(data)


def write_meta(
    summary_dir: Path | str,
    project: str,
    meta: SummaryMeta,
) -> Path:
    path = meta_path(summary_dir, project)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(meta.to_dict(), fh, indent=2, ensure_ascii=False)
    return path


def record_journal_entry(summary_dir: Path | str, project: str) -> SummaryMeta:
    """Post-commit hook: increment the counter for one newly-written journal entry.

    Called from the journal-write path after the entry is durably on disk.
    Creates the meta file on first use. Never raises — a metadata write
    failure must not break journal writes. (Caller wraps in try/except.)
    """
    meta = read_meta(summary_dir, project) or SummaryMeta()
    meta.entries_since_last_summary += 1
    meta.touch()
    write_meta(summary_dir, project, meta)
    return meta


def mark_summary_written(
    summary_dir: Path | str,
    project: str,
    last_entry_id: str,
) -> SummaryMeta:
    """Called when the summary file is updated. Advances coverage + resets counter."""
    meta = read_meta(summary_dir, project) or SummaryMeta()
    meta.last_entry_id = last_entry_id
    meta.entries_since_last_summary = 0
    meta.touch()
    write_meta(summary_dir, project, meta)
    return meta


def is_prefix_stale(
    summary_dir: Path | str,
    project: str,
    current_max_entry_id: str,
) -> bool:
    """Q8 staleness detection.

    Returns True when the journal has advanced past the summary's coverage —
    i.e. `current_max_entry_id` refers to a newer message than
    `meta.last_entry_id`. Uses numeric comparison on the ID tail so that
    MSG-0099 sorts below MSG-0100 regardless of string lexicography.

    When no summary has been written yet, any real journal entry counts as
    stale (there's no summary to cover it).
    """
    meta = read_meta(summary_dir, project)
    if meta is None or not meta.last_entry_id:
        return bool(current_max_entry_id)
    return _id_num(current_max_entry_id) > _id_num(meta.last_entry_id)


def entries_since_last_summary(summary_dir: Path | str, project: str) -> int:
    meta = read_meta(summary_dir, project)
    return meta.entries_since_last_summary if meta else 0
