"""
Tests for the summary metadata tracker (Q2 + Q8 from the Summarizer-Role design).
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from middleware.summary_meta import (
    DEFAULT_SUMMARY_THRESHOLD,
    SummaryMeta,
    _id_num,
    meta_path,
    read_meta,
    write_meta,
    record_journal_entry,
    mark_summary_written,
    is_prefix_stale,
    is_summary_due,
    entries_since_last_summary,
    summary_status,
)


class TestIdNumeric:
    def test_basic(self):
        assert _id_num("MSG-0169") == 169
        assert _id_num("MSG-0001") == 1
        assert _id_num("MSG-99999") == 99999

    def test_empty_and_malformed(self):
        assert _id_num("") == -1
        assert _id_num("MSG-") == -1
        assert _id_num("not-a-message") == -1

    def test_numeric_order_survives_string_wraparound(self):
        # Lexicographic comparison would give "MSG-0099" > "MSG-0100"; numeric does not.
        assert _id_num("MSG-0099") < _id_num("MSG-0100")


class TestRoundtrip:
    def test_read_missing_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            assert read_meta(tmp, "NoSuchProject") is None

    def test_write_then_read(self):
        meta = SummaryMeta(
            last_entry_id="MSG-0150",
            entries_since_last_summary=3,
        )
        meta.touch()
        with tempfile.TemporaryDirectory() as tmp:
            path = write_meta(tmp, "TestProject", meta)
            assert path.exists()
            assert path.name == "summary_meta.json"

            loaded = read_meta(tmp, "TestProject")
            assert loaded is not None
            assert loaded.last_entry_id == "MSG-0150"
            assert loaded.entries_since_last_summary == 3
            assert loaded.last_updated  # set by touch()

    def test_meta_path_layout(self):
        p = meta_path("/tmp/summaries", "InterAI-Protocol")
        assert p.parts[-2:] == ("InterAI-Protocol", "summary_meta.json")


class TestHooks:
    def test_record_journal_entry_creates_file_on_first_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = record_journal_entry(tmp, "NewProject")
            assert meta.entries_since_last_summary == 1
            assert meta.last_entry_id == ""
            assert meta_path(tmp, "NewProject").exists()

    def test_record_journal_entry_increments(self):
        with tempfile.TemporaryDirectory() as tmp:
            record_journal_entry(tmp, "P")
            record_journal_entry(tmp, "P")
            record_journal_entry(tmp, "P")
            assert entries_since_last_summary(tmp, "P") == 3

    def test_mark_summary_written_resets_counter_and_sets_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            record_journal_entry(tmp, "P")
            record_journal_entry(tmp, "P")
            record_journal_entry(tmp, "P")
            meta = mark_summary_written(tmp, "P", "MSG-0200")
            assert meta.entries_since_last_summary == 0
            assert meta.last_entry_id == "MSG-0200"
            assert entries_since_last_summary(tmp, "P") == 0

    def test_record_after_mark_increments_from_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            mark_summary_written(tmp, "P", "MSG-0200")
            record_journal_entry(tmp, "P")
            record_journal_entry(tmp, "P")
            assert entries_since_last_summary(tmp, "P") == 2

    def test_projects_are_isolated(self):
        with tempfile.TemporaryDirectory() as tmp:
            record_journal_entry(tmp, "ProjectA")
            record_journal_entry(tmp, "ProjectA")
            record_journal_entry(tmp, "ProjectB")
            assert entries_since_last_summary(tmp, "ProjectA") == 2
            assert entries_since_last_summary(tmp, "ProjectB") == 1


class TestStalenessDetection:
    def test_no_meta_means_any_entry_is_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            assert is_prefix_stale(tmp, "P", "MSG-0001") is True

    def test_no_entry_id_and_no_current_means_not_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            assert is_prefix_stale(tmp, "P", "") is False

    def test_equal_ids_not_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            mark_summary_written(tmp, "P", "MSG-0100")
            assert is_prefix_stale(tmp, "P", "MSG-0100") is False

    def test_journal_ahead_is_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            mark_summary_written(tmp, "P", "MSG-0100")
            assert is_prefix_stale(tmp, "P", "MSG-0101") is True
            assert is_prefix_stale(tmp, "P", "MSG-0150") is True

    def test_journal_behind_not_stale(self):
        # This shouldn't happen in practice (summary covers an entry that
        # doesn't exist in the journal), but the detector must not misreport.
        with tempfile.TemporaryDirectory() as tmp:
            mark_summary_written(tmp, "P", "MSG-0100")
            assert is_prefix_stale(tmp, "P", "MSG-0099") is False

    def test_numeric_comparison_not_lexicographic(self):
        # "MSG-0099" > "MSG-0100" as strings; numerically MSG-0100 is newer.
        with tempfile.TemporaryDirectory() as tmp:
            mark_summary_written(tmp, "P", "MSG-0099")
            assert is_prefix_stale(tmp, "P", "MSG-0100") is True


class TestThresholdDetection:
    def test_fresh_project_is_not_due(self):
        with tempfile.TemporaryDirectory() as tmp:
            assert is_summary_due(tmp, "P") is False

    def test_due_when_counter_hits_default_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            for _ in range(DEFAULT_SUMMARY_THRESHOLD):
                record_journal_entry(tmp, "P")
            assert is_summary_due(tmp, "P") is True

    def test_not_due_one_short_of_default_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            for _ in range(DEFAULT_SUMMARY_THRESHOLD - 1):
                record_journal_entry(tmp, "P")
            assert is_summary_due(tmp, "P") is False

    def test_due_resets_after_mark_summary_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            for _ in range(DEFAULT_SUMMARY_THRESHOLD):
                record_journal_entry(tmp, "P")
            assert is_summary_due(tmp, "P") is True
            mark_summary_written(tmp, "P", "MSG-0100")
            assert is_summary_due(tmp, "P") is False

    def test_custom_threshold_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            record_journal_entry(tmp, "P")
            record_journal_entry(tmp, "P")
            assert is_summary_due(tmp, "P", threshold=2) is True
            assert is_summary_due(tmp, "P", threshold=3) is False


class TestSummaryStatus:
    def test_status_for_unknown_project_has_sensible_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = summary_status(tmp, "Unseen")
            assert s["project"] == "Unseen"
            assert s["threshold"] == DEFAULT_SUMMARY_THRESHOLD
            assert s["entries_since_last_summary"] == 0
            assert s["last_entry_id"] == ""
            assert s["due"] is False

    def test_status_reflects_counter_and_due(self):
        with tempfile.TemporaryDirectory() as tmp:
            record_journal_entry(tmp, "P")
            record_journal_entry(tmp, "P")
            s = summary_status(tmp, "P", threshold=2)
            assert s["entries_since_last_summary"] == 2
            assert s["threshold"] == 2
            assert s["due"] is True

    def test_status_reflects_last_entry_id_after_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            mark_summary_written(tmp, "P", "MSG-0050")
            s = summary_status(tmp, "P")
            assert s["last_entry_id"] == "MSG-0050"
            assert s["entries_since_last_summary"] == 0
            assert s["due"] is False


class TestSerialization:
    def test_json_is_human_readable(self):
        """File should be indented JSON, not a minified blob."""
        meta = SummaryMeta(last_entry_id="MSG-0050", entries_since_last_summary=2)
        meta.touch()
        with tempfile.TemporaryDirectory() as tmp:
            path = write_meta(tmp, "P", meta)
            text = path.read_text(encoding="utf-8")
            assert "\n" in text
            parsed = json.loads(text)
            assert parsed["last_entry_id"] == "MSG-0050"
            assert parsed["entries_since_last_summary"] == 2
