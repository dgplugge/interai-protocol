"""
Background summarizer scheduler (Q2 auto-firing half).

One iteration ("tick") walks a fixed list of project keys, checks each
one against `is_summary_due`, and calls `update_project_summary` for any
that have crossed the threshold. Exceptions are swallowed per project so
one failure can't kill subsequent projects in the same tick.

The async loop (`run_scheduler`) is a thin wrapper around the tick —
tests exercise the tick directly and never need asyncio machinery.

Default state: OFF. The FastAPI startup event checks
`agent_config.scheduler.enabled` before launching the loop.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Iterable, Optional

from middleware.agent_config import AgentConfig, load_config
from middleware.summary_generator import (
    SummaryGenerationError,
    update_project_summary,
)
from middleware.summary_meta import is_summary_due


logger = logging.getLogger("aicp.summarizer.scheduler")


def projects_due(
    project_keys: Iterable[str],
    summaries_root: Path | str,
    config: Optional[AgentConfig] = None,
) -> list[str]:
    """Return the subset of project keys whose summary counter has crossed
    the configured threshold."""
    cfg = config or load_config()
    return [
        p for p in project_keys
        if is_summary_due(summaries_root, p, threshold=cfg.threshold)
    ]


def run_tick(
    project_keys: Iterable[str],
    journals_root: Path | str,
    summaries_root: Path | str,
    config: Optional[AgentConfig] = None,
    client: Any = None,
) -> dict:
    """One scheduler iteration. Returns a dict describing what happened.

    Swallows per-project exceptions so a single LLM failure can't starve
    the rest of the tick. The returned `errors` list lets tests and
    operators see which projects failed and why.
    """
    cfg = config or load_config()
    due = projects_due(project_keys, summaries_root, config=cfg)

    generated: list[str] = []
    errors: list[dict] = []

    for project in due:
        try:
            update_project_summary(
                project=project,
                journals_root=journals_root,
                summaries_root=summaries_root,
                config=cfg,
                client=client,
            )
            generated.append(project)
        except SummaryGenerationError as e:
            errors.append({"project": project, "code": "SUMMARY_GENERATION_FAILED", "detail": str(e)})
            logger.warning("summary generation failed for %s: %s", project, e)
        except Exception as e:  # noqa: BLE001 — intentional broad catch
            errors.append({"project": project, "code": "UNEXPECTED", "detail": str(e)})
            logger.exception("unexpected failure in scheduler tick for %s", project)

    return {
        "due_count": len(due),
        "generated": generated,
        "errors": errors,
    }


async def run_scheduler(
    project_keys: Iterable[str],
    journals_root: Path | str,
    summaries_root: Path | str,
    config: Optional[AgentConfig] = None,
    stop_event: Optional[asyncio.Event] = None,
) -> None:
    """Run `run_tick` in a loop at the configured interval until cancelled
    or `stop_event` is set. Each tick's blocking I/O runs in a worker
    thread so the event loop stays responsive."""
    cfg = config or load_config()
    interval = max(5, int(cfg.scheduler.interval_seconds))
    keys = list(project_keys)

    logger.info("scheduler loop starting — interval=%ss, projects=%s", interval, keys)

    while True:
        try:
            if stop_event is not None and stop_event.is_set():
                logger.info("scheduler loop stopping (stop_event set)")
                return

            await asyncio.to_thread(
                run_tick,
                keys,
                journals_root,
                summaries_root,
                cfg,
            )
        except asyncio.CancelledError:
            logger.info("scheduler loop cancelled")
            raise
        except Exception:  # noqa: BLE001
            # Keep the loop alive across unexpected errors.
            logger.exception("scheduler tick raised; continuing")

        try:
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            logger.info("scheduler loop cancelled during sleep")
            raise
