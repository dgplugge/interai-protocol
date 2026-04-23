"""
Tiered summary storage (Q1 from the Summarizer-Role design round).

Stores a three-tier summary per project in a single YAML file at
`<summary_dir>/<project>/summary.yml`. Tier layout per Lumen's spec
(MSG-XXXX, Round 2): `full`, `compressed`, `shorthand`, plus `metadata`
with `last_updated` and `entry_range`.

This module is storage-only. It does not generate summaries, does not
trigger on message events, and does not retrieve. Those concerns belong
to the producer (blocked on Q2/Q3/Q4) and the retriever (blocked on Q5).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml


class Tier(str, Enum):
    FULL = "full"
    COMPRESSED = "compressed"
    SHORTHAND = "shorthand"


@dataclass
class SummaryMetadata:
    last_updated: str = ""
    entry_range: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "last_updated": self.last_updated,
            "entry_range": list(self.entry_range),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SummaryMetadata":
        m = cls()
        m.last_updated = str(data.get("last_updated", ""))
        er = data.get("entry_range", [])
        if isinstance(er, list):
            m.entry_range = [str(x) for x in er]
        return m


@dataclass
class TieredSummary:
    full: str = ""
    compressed: str = ""
    shorthand: str = ""
    metadata: SummaryMetadata = field(default_factory=SummaryMetadata)

    def to_dict(self) -> dict:
        return {
            "full": self.full,
            "compressed": self.compressed,
            "shorthand": self.shorthand,
            "metadata": self.metadata.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TieredSummary":
        s = cls()
        s.full = str(data.get("full", ""))
        s.compressed = str(data.get("compressed", ""))
        s.shorthand = str(data.get("shorthand", ""))
        meta = data.get("metadata", {})
        if isinstance(meta, dict):
            s.metadata = SummaryMetadata.from_dict(meta)
        return s

    def get_tier(self, tier: Tier) -> str:
        return getattr(self, tier.value)

    def set_tier(self, tier: Tier, content: str) -> None:
        setattr(self, tier.value, content)

    def touch(self) -> None:
        self.metadata.last_updated = datetime.now(timezone.utc).isoformat()


def validate_schema(data: dict) -> list[str]:
    """Return a list of schema errors. Empty list = valid."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["root must be a mapping"]

    for tier in ("full", "compressed", "shorthand"):
        if tier in data and not isinstance(data[tier], str):
            errors.append(f"'{tier}' must be a string")

    meta = data.get("metadata")
    if meta is not None:
        if not isinstance(meta, dict):
            errors.append("'metadata' must be a mapping")
        else:
            if "last_updated" in meta and not isinstance(meta["last_updated"], str):
                errors.append("'metadata.last_updated' must be a string")
            if "entry_range" in meta:
                er = meta["entry_range"]
                if not isinstance(er, list):
                    errors.append("'metadata.entry_range' must be a list")
                elif len(er) not in (0, 2):
                    errors.append("'metadata.entry_range' must have 0 or 2 elements")

    allowed = {"full", "compressed", "shorthand", "metadata"}
    extra = set(data.keys()) - allowed
    if extra:
        errors.append(f"unknown top-level keys: {sorted(extra)}")

    return errors


def summary_path(summary_dir: Path | str, project: str) -> Path:
    return Path(summary_dir) / project / "summary.yml"


def read_summary(summary_dir: Path | str, project: str) -> Optional[TieredSummary]:
    """Return the stored summary for the project, or None if the file is absent."""
    path = summary_path(summary_dir, project)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    errors = validate_schema(data)
    if errors:
        raise ValueError(f"Invalid summary at {path}: {'; '.join(errors)}")
    return TieredSummary.from_dict(data)


def write_summary(
    summary_dir: Path | str,
    project: str,
    summary: TieredSummary,
) -> Path:
    """Write the summary to disk as YAML. Returns the file path."""
    data = summary.to_dict()
    errors = validate_schema(data)
    if errors:
        raise ValueError(f"Refusing to write invalid summary: {'; '.join(errors)}")

    path = summary_path(summary_dir, project)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(
            data,
            fh,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        )
    return path
