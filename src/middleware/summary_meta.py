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

# Provisional default per Pharos Round 6 Q2 redo: "conservative starting
# point, explicitly provisional — tune empirically once the summary generator
# is in place and we can measure median entries per round across projects."
DEFAULT_SUMMARY_THRESHOLD = 5


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


def is_summary_due(
    summary_dir: Path | str,
    project: str,
    threshold: Optional[int] = None,
) -> bool:
    """Q2 threshold detection: has the per-project counter reached the firing bar?

    Caller decides what to do when True — the detection layer does not itself
    trigger a summarization. This is intentional: the actual summary generator
    (Q4) is not yet wired, so firing a signal without a consumer is wasted
    work. When Q4 lands, the Hub or a scheduler calls this and acts on True.
    """
    t = DEFAULT_SUMMARY_THRESHOLD if threshold is None else threshold
    return entries_since_last_summary(summary_dir, project) >= t


def summary_status(
    summary_dir: Path | str,
    project: str,
    threshold: Optional[int] = None,
) -> dict:
    """Full status snapshot for a project's summarization state.

    Returns a dict ready to serialize as the HTTP response body, covering
    the fields a consumer needs to decide whether to trigger a summary
    run: the current counter, the threshold in effect, whether firing is
    due, the last entry the summary covers, and when the meta file was
    last touched. Returns sensible defaults when no meta file exists yet
    (e.g. a brand-new project before its first journal write).
    """
    t = DEFAULT_SUMMARY_THRESHOLD if threshold is None else threshold
    meta = read_meta(summary_dir, project)
    if meta is None:
        return {
            "project": project,
            "threshold": t,
            "entries_since_last_summary": 0,
            "last_entry_id": "",
            "last_updated": "",
            "due": False,
        }
    return {
        "project": project,
        "threshold": t,
        "entries_since_last_summary": meta.entries_since_last_summary,
        "last_entry_id": meta.last_entry_id,
        "last_updated": meta.last_updated,
        "due": meta.entries_since_last_summary >= t,
    }
