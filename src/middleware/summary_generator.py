"""
Summary generator (Q4 from the Summarizer-Role design).

Takes a set of raw AICP journal entries for a project and produces a
three-tier `TieredSummary` (full / compressed / shorthand) by calling
the Anthropic Claude API (Haiku tier per Round 6 budget discussion).

The generator is a pure function of (entries, config, client). The
orchestrator `update_project_summary` reads raw entries off disk, calls
the generator, writes the resulting summary.yml via summary_store, and
advances summary_meta via mark_summary_written. That side-effect chain is
kept out of the pure generator so the unit tests can exercise prompt /
parse logic with a mocked client.

Design trace:
  Q4 (Lodestar Round 6): three tier scopes — project snapshot / prompt-
    prefix / brainstorming — emitted on REVIEW/PLAN / RESPONSE / UPDATE
    respectively. The orchestrator's trigger is out of scope here; Q2 +
    this generator are the producer half.
  Q3 (Forge Round 5): fidelity checks run against the raw journal entries,
    not the summary. The generator does not validate; callers who want
    pre-flight validation run fidelity_check first.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

from middleware.agent_config import AgentConfig, load_config, resolve_api_key
from middleware.fidelity_check import parse_aicp_file
from middleware.summary_meta import mark_summary_written
from middleware.summary_store import SummaryMetadata, TieredSummary, write_summary


class SummaryGenerationError(Exception):
    """Raised on unrecoverable failures (no API key, API call failed, empty
    response). Callers catch and keep the prior summary in place."""


_TIER_OPEN = {
    "full":        "<FULL>",
    "compressed":  "<COMPRESSED>",
    "shorthand":   "<SHORTHAND>",
}
_TIER_CLOSE = {
    "full":        "</FULL>",
    "compressed":  "</COMPRESSED>",
    "shorthand":   "</SHORTHAND>",
}


def _build_prompt(entries_text: str, cfg: AgentConfig) -> str:
    budgets = cfg.summary_generator.tier_token_budgets
    return (
        "You are producing a rebuildable read model for an agent hub — a tiered "
        "summary of the AICP journal entries below. Output EXACTLY three "
        "sections, each delimited by its tags. Preserve factual accuracy; do "
        "not invent content not in the entries. If the entries are empty or "
        "unintelligible, emit empty sections rather than fabricating content.\n\n"
        f"Tier budgets (approximate tokens; do not exceed): "
        f"full={budgets.get('full', 2000)}, "
        f"compressed={budgets.get('compressed', 500)}, "
        f"shorthand={budgets.get('shorthand', 100)}.\n\n"
        "full — prose narrative of state, decisions, and open tasks.\n"
        "compressed — same content, terser; no decorative prose.\n"
        "shorthand — ACAL-style line codes (one claim per line, minimal "
        "punctuation, readable by agents rather than humans).\n\n"
        "FORMAT:\n"
        "<FULL>\n...\n</FULL>\n"
        "<COMPRESSED>\n...\n</COMPRESSED>\n"
        "<SHORTHAND>\n...\n</SHORTHAND>\n\n"
        "--- BEGIN JOURNAL ENTRIES ---\n"
        f"{entries_text}\n"
        "--- END JOURNAL ENTRIES ---"
    )


def _extract_tier(text: str, tier: str) -> str:
    open_tag = re.escape(_TIER_OPEN[tier])
    close_tag = re.escape(_TIER_CLOSE[tier])
    m = re.search(open_tag + r"\s*(.*?)\s*" + close_tag, text, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _default_anthropic_client(api_key: str):
    from anthropic import Anthropic
    return Anthropic(api_key=api_key)


def generate_summary(
    entries_text: str,
    entry_id_range: Optional[tuple[str, str]] = None,
    config: Optional[AgentConfig] = None,
    client: Any = None,
    env: Optional[dict] = None,
) -> TieredSummary:
    """Generate a three-tier summary from raw journal entries text.

    `entries_text` is the concatenated raw content of the journal entries
    (ideally with $ID headers intact so the model can cite them). If empty,
    returns a TieredSummary with empty tiers rather than calling the API.

    `entry_id_range` — optional (first_id, last_id) to stamp in the metadata
    block of the returned summary.
    """
    cfg = config or load_config()

    summary = TieredSummary()
    summary.metadata = SummaryMetadata()
    if entry_id_range is not None:
        summary.metadata.entry_range = [entry_id_range[0], entry_id_range[1]]
    summary.touch()

    if not entries_text.strip():
        return summary

    gen = cfg.summary_generator
    if gen.provider.lower() != "anthropic":
        raise SummaryGenerationError(
            f"summary_generator.provider '{gen.provider}' not supported; "
            "only 'anthropic' is wired"
        )

    if client is None:
        key = resolve_api_key("anthropic", cfg, env=env)
        client = _default_anthropic_client(key)

    prompt = _build_prompt(entries_text, cfg)

    try:
        resp = client.messages.create(
            model=gen.model,
            max_tokens=gen.max_output_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        raise SummaryGenerationError(f"anthropic messages call failed: {e}") from e

    # Anthropic SDK returns resp.content as a list of content blocks; text
    # lives in block.text. Concatenate any text blocks we find.
    blocks = getattr(resp, "content", None) or []
    text_parts: list[str] = []
    for b in blocks:
        t = getattr(b, "text", None)
        if t:
            text_parts.append(t)
    raw = "".join(text_parts).strip()

    if not raw:
        raise SummaryGenerationError("anthropic returned no text content")

    summary.full = _extract_tier(raw, "full")
    summary.compressed = _extract_tier(raw, "compressed")
    summary.shorthand = _extract_tier(raw, "shorthand")

    return summary


def _read_project_entries(
    journal_dir: Path | str,
    limit: Optional[int] = None,
) -> tuple[str, Optional[tuple[str, str]]]:
    """Read message files, return (concatenated_text, id_range_or_None).

    Files are sorted by name (date-prefixed), so `limit` keeps the most
    recent N entries.
    """
    messages_dir = Path(journal_dir) / "messages"
    if not messages_dir.is_dir():
        return "", None

    files = sorted(messages_dir.glob("*.md"))
    if limit is not None:
        files = files[-limit:]

    if not files:
        return "", None

    blocks: list[str] = []
    ids: list[str] = []
    for f in files:
        fields = parse_aicp_file(f)
        mid = fields.get("$ID", "")
        if mid:
            ids.append(mid)
        mtype = fields.get("$TYPE", "")
        sender = fields.get("$FROM", "")
        task = fields.get("$TASK", "")
        payload = fields.get("payload", "")
        blocks.append(
            f"[{mid} | {mtype} | from={sender}] {task}\n{payload}"
        )
    id_range = (ids[0], ids[-1]) if ids else None
    return "\n\n---\n\n".join(blocks), id_range


def update_project_summary(
    project: str,
    journals_root: Path | str,
    summaries_root: Path | str,
    limit: Optional[int] = None,
    config: Optional[AgentConfig] = None,
    client: Any = None,
    env: Optional[dict] = None,
) -> TieredSummary:
    """Orchestrate the full producer flow: read raw entries, generate tiers,
    write summary.yml, advance summary_meta.last_entry_id.

    Returns the generated TieredSummary. Raises SummaryGenerationError on
    provider failure; callers typically log and continue — the old summary
    file stays in place and entries_since_last_summary keeps growing.
    """
    journal_dir = Path(journals_root) / project
    entries_text, id_range = _read_project_entries(journal_dir, limit=limit)
    if not entries_text:
        # Nothing to summarize; leave existing summary (if any) untouched.
        summary = TieredSummary()
        summary.touch()
        return summary

    summary = generate_summary(
        entries_text=entries_text,
        entry_id_range=id_range,
        config=config,
        client=client,
        env=env,
    )

    # Persist
    write_summary(summaries_root, project, summary)
    if id_range is not None:
        mark_summary_written(summaries_root, project, id_range[1])

    return summary
