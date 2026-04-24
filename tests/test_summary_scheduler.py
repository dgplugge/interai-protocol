"""
Tests for the background summary scheduler.

The tick logic (projects_due + run_tick) is exercised synchronously
against a temp filesystem; the async loop is tested with a short
interval and a stop_event to avoid long sleeps.
"""

import asyncio
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from middleware.agent_config import (
    AgentConfig,
    SchedulerConfig,
    SummaryGeneratorConfig,
)
from middleware.summary_meta import record_journal_entry
from middleware import summary_scheduler
from middleware.summary_scheduler import (
    projects_due,
    run_scheduler,
    run_tick,
)


def _cfg(threshold=2, interval=5):
    c = AgentConfig()
    c.threshold = threshold
    c.scheduler = SchedulerConfig(enabled=True, interval_seconds=interval)
    # Summary generator must have a provider that match; we monkeypatch
    # update_project_summary in tests anyway, but keep the config valid.
    c.summary_generator = SummaryGeneratorConfig(provider="anthropic")
    return c


class TestProjectsDue:
    def test_none_due_fresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            assert projects_due(["A", "B", "C"], tmp, config=_cfg()) == []

    def test_only_due_projects_returned(self):
        with tempfile.TemporaryDirectory() as tmp:
            record_journal_entry(tmp, "A")
            record_journal_entry(tmp, "A")  # A hits threshold=2
            record_journal_entry(tmp, "B")  # B below threshold
            due = projects_due(["A", "B", "C"], tmp, config=_cfg(threshold=2))
            assert due == ["A"]


class TestRunTick:
    def test_empty_projects_is_a_noop(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            summary_scheduler, "update_project_summary",
            lambda **kw: calls.append(kw),
        )
        with tempfile.TemporaryDirectory() as tmp:
            result = run_tick([], journals_root=tmp, summaries_root=tmp, config=_cfg())
        assert result["due_count"] == 0
        assert result["generated"] == []
        assert calls == []

    def test_only_due_projects_generate(self, monkeypatch):
        calls = []
        def fake_update(**kw):
            calls.append(kw["project"])
            # Return a falsy-but-truthy placeholder so upstream accepts it
            from middleware.summary_store import TieredSummary
            s = TieredSummary(full="fake"); s.touch(); return s
        monkeypatch.setattr(summary_scheduler, "update_project_summary", fake_update)

        with tempfile.TemporaryDirectory() as tmp:
            summaries = Path(tmp) / "summaries"
            journals = Path(tmp) / "journals"
            summaries.mkdir(); journals.mkdir()

            record_journal_entry(summaries, "A")
            record_journal_entry(summaries, "A")  # A due
            # B has no counter yet → not due

            result = run_tick(
                ["A", "B"], journals_root=journals, summaries_root=summaries,
                config=_cfg(threshold=2),
            )

        assert result["due_count"] == 1
        assert result["generated"] == ["A"]
        assert result["errors"] == []
        assert calls == ["A"]

    def test_generator_error_is_captured_not_fatal(self, monkeypatch):
        from middleware.summary_generator import SummaryGenerationError

        def always_fail(**kw):
            raise SummaryGenerationError(f"boom for {kw['project']}")

        monkeypatch.setattr(summary_scheduler, "update_project_summary", always_fail)

        with tempfile.TemporaryDirectory() as tmp:
            summaries = Path(tmp) / "summaries"
            journals = Path(tmp) / "journals"
            summaries.mkdir(); journals.mkdir()

            record_journal_entry(summaries, "A")
            record_journal_entry(summaries, "A")
            record_journal_entry(summaries, "B")
            record_journal_entry(summaries, "B")

            result = run_tick(
                ["A", "B"], journals_root=journals, summaries_root=summaries,
                config=_cfg(threshold=2),
            )

        assert result["due_count"] == 2
        assert result["generated"] == []
        assert len(result["errors"]) == 2
        assert {e["code"] for e in result["errors"]} == {"SUMMARY_GENERATION_FAILED"}

    def test_unexpected_error_captured(self, monkeypatch):
        def raises(**kw):
            raise RuntimeError("unexpected")
        monkeypatch.setattr(summary_scheduler, "update_project_summary", raises)

        with tempfile.TemporaryDirectory() as tmp:
            summaries = Path(tmp) / "summaries"
            journals = Path(tmp) / "journals"
            summaries.mkdir(); journals.mkdir()
            record_journal_entry(summaries, "A")
            record_journal_entry(summaries, "A")

            result = run_tick(
                ["A"], journals_root=journals, summaries_root=summaries,
                config=_cfg(threshold=2),
            )

        assert result["generated"] == []
        assert result["errors"][0]["code"] == "UNEXPECTED"
        assert "unexpected" in result["errors"][0]["detail"]


class TestRunScheduler:
    def test_stop_event_causes_exit(self, monkeypatch):
        """Run the async loop with a short interval and an immediate stop
        event; verify it exits cleanly."""
        monkeypatch.setattr(
            summary_scheduler, "update_project_summary",
            lambda **kw: None,  # tick is a noop
        )

        async def drive():
            with tempfile.TemporaryDirectory() as tmp:
                summaries = Path(tmp) / "summaries"
                journals = Path(tmp) / "journals"
                summaries.mkdir(); journals.mkdir()

                stop = asyncio.Event()
                stop.set()  # stop before the first await

                # Clamp interval to the 5s minimum; the loop checks stop_event
                # before sleeping, so the test completes without waiting.
                await run_scheduler(
                    project_keys=["A"],
                    journals_root=journals,
                    summaries_root=summaries,
                    config=_cfg(interval=5),
                    stop_event=stop,
                )

        asyncio.run(drive())

    def test_cancellation_is_clean(self, monkeypatch):
        monkeypatch.setattr(
            summary_scheduler, "update_project_summary",
            lambda **kw: None,
        )

        async def drive():
            with tempfile.TemporaryDirectory() as tmp:
                summaries = Path(tmp) / "summaries"
                journals = Path(tmp) / "journals"
                summaries.mkdir(); journals.mkdir()

                task = asyncio.create_task(run_scheduler(
                    project_keys=["A"],
                    journals_root=journals,
                    summaries_root=summaries,
                    config=_cfg(interval=5),
                ))
                # Let one tick happen, then cancel.
                await asyncio.sleep(0.05)
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task

        asyncio.run(drive())
