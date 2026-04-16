"""
Tests for Slice 8.5 — Thread Cache Compaction
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from middleware.thread_compactor import (
    ThreadTracker,
    ThreadSummary,
    DEFAULT_THRESHOLD,
)


def make_message(msg_id, sender, task="Test task", status="OPEN",
                 decision="", seq=1, time="2026-04-16T10:00:00-04:00",
                 content="Test content"):
    """Helper to create a message dict."""
    msg = {
        "id": msg_id,
        "from": sender,
        "task": task,
        "status": status,
        "seq": seq,
        "time": time,
        "content": content,
    }
    if decision:
        msg["decision"] = decision
    return msg


class TestTracking:
    """Message count tracking per thread."""

    def test_empty_thread(self):
        tracker = ThreadTracker()
        assert tracker.get_count("T-001") == 0

    def test_add_message_increments(self):
        tracker = ThreadTracker()
        tracker.add_message("T-001", make_message("MSG-1", "Don"))
        assert tracker.get_count("T-001") == 1

    def test_multiple_messages(self):
        tracker = ThreadTracker()
        for i in range(5):
            tracker.add_message("T-001", make_message(f"MSG-{i}", "Don"))
        assert tracker.get_count("T-001") == 5

    def test_separate_threads(self):
        tracker = ThreadTracker()
        tracker.add_message("T-001", make_message("MSG-1", "Don"))
        tracker.add_message("T-002", make_message("MSG-2", "Pharos"))
        assert tracker.get_count("T-001") == 1
        assert tracker.get_count("T-002") == 1


class TestThreshold:
    """Should compact at threshold."""

    def test_below_threshold(self):
        tracker = ThreadTracker(threshold=10)
        for i in range(9):
            tracker.add_message("T-001", make_message(f"MSG-{i}", "Don"))
        assert not tracker.should_compact("T-001")

    def test_at_threshold(self):
        tracker = ThreadTracker(threshold=10)
        for i in range(10):
            tracker.add_message("T-001", make_message(f"MSG-{i}", "Don"))
        assert tracker.should_compact("T-001")

    def test_above_threshold(self):
        tracker = ThreadTracker(threshold=10)
        for i in range(15):
            tracker.add_message("T-001", make_message(f"MSG-{i}", "Don"))
        assert tracker.should_compact("T-001")

    def test_custom_threshold(self):
        tracker = ThreadTracker(threshold=3)
        for i in range(3):
            tracker.add_message("T-001", make_message(f"MSG-{i}", "Don"))
        assert tracker.should_compact("T-001")

    def test_default_threshold(self):
        assert DEFAULT_THRESHOLD == 10


class TestCompaction:
    """Summary generation and sidecar file creation."""

    def test_compact_creates_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ThreadTracker(summary_dir=tmpdir, threshold=3)
            for i in range(3):
                tracker.add_message("T-001", make_message(
                    f"MSG-{i}", ["Don", "Pharos", "Lodestar"][i],
                    seq=i+1, time=f"2026-04-16T1{i}:00:00-04:00"
                ))
            summary = tracker.compact("T-001")
            assert summary.thread_id == "T-001"
            assert summary.message_count == 3

    def test_compact_writes_sidecar(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ThreadTracker(summary_dir=tmpdir, threshold=2)
            tracker.add_message("T-001", make_message("MSG-1", "Don"))
            tracker.add_message("T-001", make_message("MSG-2", "Pharos"))
            tracker.compact("T-001")

            sidecar = Path(tmpdir) / "T-001.summary.json"
            assert sidecar.exists()
            data = json.loads(sidecar.read_text())
            assert data["thread_id"] == "T-001"

    def test_compact_resets_thread(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ThreadTracker(summary_dir=tmpdir, threshold=2)
            tracker.add_message("T-001", make_message("MSG-1", "Don"))
            tracker.add_message("T-001", make_message("MSG-2", "Pharos"))
            tracker.compact("T-001")
            assert tracker.get_count("T-001") == 0

    def test_compact_empty_thread_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ThreadTracker(summary_dir=tmpdir)
            try:
                tracker.compact("T-EMPTY")
                assert False, "Should have raised ValueError"
            except ValueError:
                pass

    def test_compact_extracts_participants(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ThreadTracker(summary_dir=tmpdir, threshold=3)
            tracker.add_message("T-001", make_message("MSG-1", "Don"))
            tracker.add_message("T-001", make_message("MSG-2", "Pharos"))
            tracker.add_message("T-001", make_message("MSG-3", "Lodestar"))
            summary = tracker.compact("T-001")
            assert "Don" in summary.participants
            assert "Pharos" in summary.participants
            assert "Lodestar" in summary.participants

    def test_compact_extracts_decisions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ThreadTracker(summary_dir=tmpdir, threshold=3)
            tracker.add_message("T-001", make_message("MSG-1", "Don"))
            tracker.add_message("T-001", make_message("MSG-2", "Pharos", decision="EXECUTE"))
            tracker.add_message("T-001", make_message("MSG-3", "Lodestar", decision="CHALLENGE"))
            summary = tracker.compact("T-001")
            assert len(summary.decisions) == 2
            assert summary.decisions[0]["agent"] == "Pharos"
            assert summary.decisions[0]["decision"] == "EXECUTE"

    def test_compact_extracts_open_tasks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ThreadTracker(summary_dir=tmpdir, threshold=2)
            tracker.add_message("T-001", make_message("MSG-1", "Don", task="Build middleware", status="OPEN"))
            tracker.add_message("T-001", make_message("MSG-2", "Pharos", task="Write tests", status="IN_PROGRESS"))
            summary = tracker.compact("T-001")
            assert "Build middleware" in summary.open_tasks
            assert "Write tests" in summary.open_tasks

    def test_compact_time_range(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ThreadTracker(summary_dir=tmpdir, threshold=2)
            tracker.add_message("T-001", make_message("MSG-1", "Don", time="2026-04-16T08:00:00-04:00"))
            tracker.add_message("T-001", make_message("MSG-2", "Pharos", time="2026-04-16T09:30:00-04:00"))
            summary = tracker.compact("T-001")
            assert summary.time_range[0] == "2026-04-16T08:00:00-04:00"
            assert summary.time_range[1] == "2026-04-16T09:30:00-04:00"


class TestSummaryLoadAndContext:
    """Loading summaries and generating context."""

    def test_load_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ThreadTracker(summary_dir=tmpdir, threshold=2)
            tracker.add_message("T-001", make_message("MSG-1", "Don"))
            tracker.add_message("T-001", make_message("MSG-2", "Pharos"))
            tracker.compact("T-001")

            loaded = tracker.load_summary("T-001")
            assert loaded is not None
            assert loaded.thread_id == "T-001"
            assert loaded.message_count == 2

    def test_load_missing_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ThreadTracker(summary_dir=tmpdir)
            assert tracker.load_summary("T-MISSING") is None

    def test_get_context_with_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ThreadTracker(summary_dir=tmpdir, threshold=2)
            tracker.add_message("T-001", make_message("MSG-1", "Don"))
            tracker.add_message("T-001", make_message("MSG-2", "Pharos"))
            tracker.compact("T-001")

            # Add a new message after compaction
            tracker.add_message("T-001", make_message("MSG-3", "Lodestar"))

            context = tracker.get_context("T-001")
            assert "Thread Summary" in context
            assert "Recent messages (1)" in context
            assert "Lodestar" in context

    def test_get_context_without_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ThreadTracker(summary_dir=tmpdir)
            tracker.add_message("T-001", make_message("MSG-1", "Don", content="Hello team"))
            context = tracker.get_context("T-001")
            assert "Don" in context
            assert "Hello team" in context


class TestSummarySerialization:
    """ThreadSummary serialization round-trip."""

    def test_to_dict_and_back(self):
        s = ThreadSummary()
        s.thread_id = "T-001"
        s.message_count = 10
        s.time_range = ["2026-04-16T08:00:00", "2026-04-16T12:00:00"]
        s.decisions = [{"agent": "Pharos", "decision": "EXECUTE", "message_id": "MSG-5"}]
        s.open_tasks = ["Build middleware"]
        s.constraints = ["API-only routing"]
        s.participants = ["Don", "Pharos"]

        d = s.to_dict()
        restored = ThreadSummary.from_dict(d)
        assert restored.thread_id == "T-001"
        assert restored.message_count == 10
        assert len(restored.decisions) == 1
        assert restored.decisions[0]["agent"] == "Pharos"

    def test_to_prompt(self):
        s = ThreadSummary()
        s.thread_id = "T-001"
        s.message_count = 5
        s.time_range = ["08:00", "12:00"]
        s.participants = ["Don", "Pharos"]
        s.decisions = [{"agent": "Pharos", "decision": "EXECUTE", "message_id": "MSG-5"}]
        s.open_tasks = ["Build middleware"]

        prompt = s.to_prompt()
        assert "Thread Summary" in prompt
        assert "Pharos: EXECUTE" in prompt
        assert "Build middleware" in prompt
