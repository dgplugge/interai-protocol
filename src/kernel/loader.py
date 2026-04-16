"""
AICP Context Kernel Loader

Discovers, loads, parses, and validates kernel .md files from the
kernels/ directory.  Returns kernel content ready for injection
into dispatch system prompts (8K token budget in ACAL format).

Kernel format reference: docs/context-kernel-spec.md
"""

import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("aicp.kernel")

# The six canonical sections, in required order
KERNEL_SECTIONS = ("PROTO", "ROSTER", "STATE", "MEMORY", "DICT", "NEXT_STEPS")

# Regex that matches a section delimiter like ---PROTO--- or ---NEXT_STEPS---
_SECTION_RE = re.compile(r"^---([A-Z_]+)---\s*$")

# Header line pattern:  # CONTEXT KERNEL: <label>
_HEADER_RE = re.compile(r"^#\s+CONTEXT KERNEL:\s*(.+)$", re.IGNORECASE)

# Version/meta line:  # Version: 1.0 | Updated: 2026-04-14 | Task: ...
_META_RE = re.compile(
    r"Version:\s*(?P<version>[^\|]+)"
    r"\|\s*Updated:\s*(?P<updated>[^\|]+)"
    r"\|\s*Task:\s*(?P<task>.+)",
    re.IGNORECASE,
)

# Default directory for kernel files, relative to project root
DEFAULT_KERNELS_DIR = "kernels"

# Maximum token budget for an injected kernel (ACAL format)
MAX_KERNEL_TOKENS = 8000

# Characters-per-token estimate (matches token_estimator defaults)
CHARS_PER_TOKEN = 4.0


@dataclass
class KernelData:
    """Parsed representation of a context kernel."""

    name: str                                 # e.g. "acal-dev"
    label: str = ""                           # e.g. "ACAL Development"
    version: str = ""                         # e.g. "1.0"
    updated: str = ""                         # e.g. "2026-04-14"
    task: str = ""                            # e.g. "ACAL Language Development"
    file_path: str = ""                       # absolute path to the .md file
    sections: dict[str, str] = field(default_factory=dict)
    raw: str = ""                             # full file content
    token_estimate: int = 0
    loaded_at: Optional[datetime] = None

    # --- Convenience accessors ---

    @property
    def proto(self) -> str:
        return self.sections.get("PROTO", "")

    @property
    def roster(self) -> str:
        return self.sections.get("ROSTER", "")

    @property
    def state(self) -> str:
        return self.sections.get("STATE", "")

    @property
    def memory(self) -> str:
        return self.sections.get("MEMORY", "")

    @property
    def dict_section(self) -> str:
        return self.sections.get("DICT", "")

    @property
    def next_steps(self) -> str:
        return self.sections.get("NEXT_STEPS", "")

    # --- Staleness ---

    def age_seconds(self) -> float:
        """Seconds since the kernel was loaded into memory."""
        if self.loaded_at is None:
            return float("inf")
        delta = datetime.now(timezone.utc) - self.loaded_at
        return delta.total_seconds()

    def is_stale(self, max_age_seconds: float = 300.0) -> bool:
        """True if the kernel was loaded more than *max_age_seconds* ago."""
        return self.age_seconds() > max_age_seconds

    # --- Injection payload ---

    def to_prompt(self) -> str:
        """
        Render the kernel as a string suitable for injection into a
        system prompt.  Returns the raw file content (already in ACAL
        prompt format).
        """
        return self.raw


class KernelLoader:
    """
    Discovers and loads kernel .md files.

    Usage::

        loader = KernelLoader("/path/to/project/kernels")
        kernel = loader.load("acal-dev")
        system_prompt = kernel.to_prompt()
    """

    def __init__(self, kernels_dir: str | Path | None = None):
        if kernels_dir is None:
            # Default: <project_root>/kernels
            project_root = Path(__file__).resolve().parent.parent.parent
            kernels_dir = project_root / DEFAULT_KERNELS_DIR
        self.kernels_dir = Path(kernels_dir)
        self._cache: dict[str, KernelData] = {}

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def list_kernels(self) -> list[str]:
        """Return sorted list of available kernel names (without extension)."""
        if not self.kernels_dir.is_dir():
            logger.warning("Kernels directory does not exist: %s", self.kernels_dir)
            return []
        names = []
        for f in sorted(self.kernels_dir.glob("kernel-*.md")):
            name = f.stem.removeprefix("kernel-")
            names.append(name)
        return names

    # ------------------------------------------------------------------
    # Loading & parsing
    # ------------------------------------------------------------------

    def load(self, name: str, *, force: bool = False) -> KernelData:
        """
        Load and parse a kernel by name.

        Args:
            name: Kernel identifier, e.g. ``"acal-dev"``.
            force: If True, bypass the in-memory cache.

        Returns:
            Parsed ``KernelData`` instance.

        Raises:
            FileNotFoundError: If the kernel file does not exist.
            ValueError: If the kernel is malformed.
        """
        # Cache hit?
        if not force and name in self._cache:
            cached = self._cache[name]
            if not cached.is_stale():
                return cached

        file_path = self.kernels_dir / f"kernel-{name}.md"
        if not file_path.is_file():
            raise FileNotFoundError(
                f"Kernel '{name}' not found at {file_path}"
            )

        raw = file_path.read_text(encoding="utf-8")
        kernel = self._parse(name, raw, str(file_path))
        self._cache[name] = kernel
        return kernel

    def _parse(self, name: str, raw: str, file_path: str) -> KernelData:
        """Parse raw kernel text into a KernelData instance."""
        kernel = KernelData(
            name=name,
            file_path=file_path,
            raw=raw,
            loaded_at=datetime.now(timezone.utc),
        )

        lines = raw.splitlines()

        # --- Header & meta ---
        for line in lines:
            hdr = _HEADER_RE.match(line)
            if hdr:
                kernel.label = hdr.group(1).strip()
                continue
            meta = _META_RE.search(line)
            if meta:
                kernel.version = meta.group("version").strip()
                kernel.updated = meta.group("updated").strip()
                kernel.task = meta.group("task").strip()
                break  # meta always follows header; stop scanning

        # --- Sections ---
        current_section: Optional[str] = None
        section_lines: dict[str, list[str]] = {}

        for line in lines:
            m = _SECTION_RE.match(line)
            if m:
                current_section = m.group(1)
                section_lines.setdefault(current_section, [])
                continue
            if current_section is not None:
                section_lines[current_section].append(line)

        # Strip leading/trailing blank lines from each section
        for sec, slines in section_lines.items():
            text = "\n".join(slines).strip()
            kernel.sections[sec] = text

        # --- Validation ---
        self._validate(kernel)

        # --- Token estimate ---
        kernel.token_estimate = max(1, int(len(raw) / CHARS_PER_TOKEN))

        return kernel

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate(kernel: KernelData) -> None:
        """
        Validate that the kernel has the required structure.

        Raises ``ValueError`` on problems.
        """
        missing = [s for s in KERNEL_SECTIONS if s not in kernel.sections]
        if missing:
            raise ValueError(
                f"Kernel '{kernel.name}' is missing sections: {', '.join(missing)}"
            )

        if not kernel.label:
            raise ValueError(
                f"Kernel '{kernel.name}' is missing the CONTEXT KERNEL header line"
            )

    # ------------------------------------------------------------------
    # Budget check
    # ------------------------------------------------------------------

    def check_budget(self, kernel: KernelData) -> dict:
        """
        Check whether the kernel fits within the 8K token budget.

        Returns a dict with ``within_budget``, ``token_estimate``,
        ``max_tokens``, and an optional ``warning``.
        """
        result: dict = {
            "within_budget": kernel.token_estimate <= MAX_KERNEL_TOKENS,
            "token_estimate": kernel.token_estimate,
            "max_tokens": MAX_KERNEL_TOKENS,
        }
        if not result["within_budget"]:
            result["warning"] = (
                f"Kernel '{kernel.name}' exceeds the {MAX_KERNEL_TOKENS}-token "
                f"budget ({kernel.token_estimate} estimated). Consider archiving "
                f"old MEMORY entries or compressing STATE."
            )
            logger.warning(result["warning"])
        return result

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    def invalidate(self, name: str) -> None:
        """Remove a kernel from the in-memory cache."""
        self._cache.pop(name, None)

    def invalidate_all(self) -> None:
        """Clear the entire cache."""
        self._cache.clear()
