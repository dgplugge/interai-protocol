"""
Tests for the tiered summary storage module (Q1 from the Summarizer-Role
design round).
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from middleware.summary_store import (
    Tier,
    TieredSummary,
    SummaryMetadata,
    validate_schema,
    read_summary,
    write_summary,
    summary_path,
)


class TestSchema:
    def test_empty_is_valid(self):
        assert validate_schema({}) == []

    def test_valid_full_dict(self):
        data = {
            "full": "long prose",
            "compressed": "short prose",
            "shorthand": "code",
            "metadata": {
                "last_updated": "2026-04-22T16:00:00+00:00",
                "entry_range": ["MSG-0100", "MSG-0169"],
            },
        }
        assert validate_schema(data) == []

    def test_non_string_tier_is_error(self):
        errors = validate_schema({"full": 123})
        assert any("'full' must be a string" in e for e in errors)

    def test_unknown_top_level_key(self):
        errors = validate_schema({"extra": "x"})
        assert any("unknown top-level keys" in e for e in errors)

    def test_entry_range_wrong_length(self):
        data = {"metadata": {"entry_range": ["only-one"]}}
        errors = validate_schema(data)
        assert any("0 or 2 elements" in e for e in errors)

    def test_entry_range_empty_ok(self):
        data = {"metadata": {"entry_range": []}}
        assert validate_schema(data) == []

    def test_metadata_not_mapping(self):
        errors = validate_schema({"metadata": "oops"})
        assert any("'metadata' must be a mapping" in e for e in errors)


class TestRoundtrip:
    def test_write_then_read(self):
        s = TieredSummary(
            full="full-tier content",
            compressed="compressed-tier content",
            shorthand="SH:1|2|3",
        )
        s.metadata.entry_range = ["MSG-0001", "MSG-0010"]
        s.touch()

        with tempfile.TemporaryDirectory() as tmp:
            path = write_summary(tmp, "TestProject", s)
            assert path.exists()
            assert path.name == "summary.yml"

            loaded = read_summary(tmp, "TestProject")
            assert loaded is not None
            assert loaded.full == "full-tier content"
            assert loaded.compressed == "compressed-tier content"
            assert loaded.shorthand == "SH:1|2|3"
            assert loaded.metadata.entry_range == ["MSG-0001", "MSG-0010"]
            assert loaded.metadata.last_updated  # set by touch()

    def test_read_missing_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            assert read_summary(tmp, "NoSuchProject") is None

    def test_path_layout(self):
        p = summary_path("/tmp/summaries", "InterAI-Protocol")
        assert p.parts[-2:] == ("InterAI-Protocol", "summary.yml")


class TestTierAccessor:
    def test_get_and_set_tier(self):
        s = TieredSummary()
        s.set_tier(Tier.FULL, "hello")
        s.set_tier(Tier.COMPRESSED, "hi")
        s.set_tier(Tier.SHORTHAND, "h")
        assert s.get_tier(Tier.FULL) == "hello"
        assert s.get_tier(Tier.COMPRESSED) == "hi"
        assert s.get_tier(Tier.SHORTHAND) == "h"


class TestValidationOnWrite:
    def test_refuses_invalid_schema(self):
        # We manually corrupt metadata to trigger a validation failure on write.
        s = TieredSummary()
        s.metadata.entry_range = ["only-one-element"]
        with tempfile.TemporaryDirectory() as tmp:
            try:
                write_summary(tmp, "TestProject", s)
            except ValueError as e:
                assert "0 or 2 elements" in str(e)
            else:
                raise AssertionError("write_summary should have raised")
