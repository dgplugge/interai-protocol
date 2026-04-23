"""
Tests for the Q4 summary generator. The Anthropic client is always mocked.
"""

import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from middleware.agent_config import AgentConfig, SummaryGeneratorConfig
from middleware.summary_generator import (
    SummaryGenerationError,
    _build_prompt,
    _extract_tier,
    _read_project_entries,
    generate_summary,
    update_project_summary,
)
from middleware.summary_store import read_summary
from middleware.summary_meta import read_meta


def _fake_anthropic_client(response_text: str):
    def create(model, max_tokens, messages):
        return SimpleNamespace(content=[SimpleNamespace(text=response_text)])
    return SimpleNamespace(messages=SimpleNamespace(create=create))


def _cfg() -> AgentConfig:
    c = AgentConfig()
    c.summary_generator = SummaryGeneratorConfig(
        provider="anthropic",
        model="claude-haiku-4-5-20251001",
        max_input_tokens=8192,
        max_output_tokens=2048,
        tier_token_budgets={"full": 2000, "compressed": 500, "shorthand": 100},
    )
    return c


def _write_journal_entry(messages_dir: Path, msg_id: str, payload: str) -> None:
    f = messages_dir / f"2026-04-23-{msg_id}-update-pharos.md"
    f.write_text(
        "$PROTO: AICP/1.0\n"
        "$TYPE: UPDATE\n"
        f"$ID: {msg_id}\n"
        "$FROM: Pharos\n"
        "$TO: All\n"
        "$TIME: 2026-04-23T12:00:00-04:00\n"
        "$TASK: test task\n"
        "$STATUS: CLOSED\n"
        "\n---PAYLOAD---\n\n"
        f"{payload}\n"
        "---END---\n",
        encoding="utf-8",
    )


class TestExtractTier:
    def test_roundtrip_all_three_tiers(self):
        response = (
            "<FULL>\nfull content here\n</FULL>\n"
            "<COMPRESSED>\ncompressed content\n</COMPRESSED>\n"
            "<SHORTHAND>\nsh:1|2|3\n</SHORTHAND>\n"
        )
        assert _extract_tier(response, "full") == "full content here"
        assert _extract_tier(response, "compressed") == "compressed content"
        assert _extract_tier(response, "shorthand") == "sh:1|2|3"

    def test_missing_tier_returns_empty(self):
        response = "<FULL>\nbody\n</FULL>"
        assert _extract_tier(response, "compressed") == ""

    def test_case_insensitive_tags(self):
        response = "<full>\nbody\n</Full>"
        assert _extract_tier(response, "full") == "body"


class TestBuildPrompt:
    def test_prompt_contains_tier_tags(self):
        cfg = _cfg()
        p = _build_prompt("some journal entries", cfg)
        assert "<FULL>" in p and "</FULL>" in p
        assert "<COMPRESSED>" in p and "</COMPRESSED>" in p
        assert "<SHORTHAND>" in p and "</SHORTHAND>" in p

    def test_prompt_contains_budgets(self):
        cfg = _cfg()
        p = _build_prompt("x", cfg)
        assert "full=2000" in p
        assert "compressed=500" in p
        assert "shorthand=100" in p

    def test_prompt_embeds_entries(self):
        cfg = _cfg()
        p = _build_prompt("MARKER-UNIQUE", cfg)
        assert "MARKER-UNIQUE" in p


class TestGenerateSummary:
    def test_all_three_tiers_populated(self):
        cfg = _cfg()
        client = _fake_anthropic_client(
            "<FULL>full text</FULL>"
            "<COMPRESSED>compressed text</COMPRESSED>"
            "<SHORTHAND>sh</SHORTHAND>"
        )
        s = generate_summary("some entries", config=cfg, client=client)
        assert s.full == "full text"
        assert s.compressed == "compressed text"
        assert s.shorthand == "sh"
        assert s.metadata.last_updated  # set by touch()

    def test_entry_id_range_stamped(self):
        cfg = _cfg()
        client = _fake_anthropic_client("<FULL>x</FULL>")
        s = generate_summary(
            "entries",
            entry_id_range=("MSG-0100", "MSG-0200"),
            config=cfg,
            client=client,
        )
        assert s.metadata.entry_range == ["MSG-0100", "MSG-0200"]

    def test_empty_entries_short_circuits_no_api_call(self):
        cfg = _cfg()

        class BoomClient:
            class messages:
                @staticmethod
                def create(**kwargs):
                    raise AssertionError("client must not be called on empty input")

        s = generate_summary("", config=cfg, client=BoomClient())
        assert s.full == ""
        assert s.compressed == ""
        assert s.shorthand == ""

    def test_non_anthropic_provider_raises(self):
        cfg = _cfg()
        cfg.summary_generator.provider = "openai"
        with pytest.raises(SummaryGenerationError):
            generate_summary("x", config=cfg, client=object())

    def test_api_failure_wraps(self):
        cfg = _cfg()

        class Bad:
            class messages:
                @staticmethod
                def create(**kwargs):
                    raise RuntimeError("network")

        with pytest.raises(SummaryGenerationError) as exc:
            generate_summary("x", config=cfg, client=Bad())
        assert "network" in str(exc.value)

    def test_empty_response_raises(self):
        cfg = _cfg()
        client = _fake_anthropic_client("")
        with pytest.raises(SummaryGenerationError):
            generate_summary("x", config=cfg, client=client)

    def test_partial_tiers_are_acceptable(self):
        """A response missing one tier still produces the others (not an error)."""
        cfg = _cfg()
        client = _fake_anthropic_client(
            "<FULL>has full</FULL><COMPRESSED>has compressed</COMPRESSED>"
            # no shorthand
        )
        s = generate_summary("x", config=cfg, client=client)
        assert s.full == "has full"
        assert s.compressed == "has compressed"
        assert s.shorthand == ""


class TestReadProjectEntries:
    def test_concatenates_and_tracks_range(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "P"
            (project_dir / "messages").mkdir(parents=True)
            _write_journal_entry(project_dir / "messages", "MSG-0001", "body one")
            _write_journal_entry(project_dir / "messages", "MSG-0002", "body two")
            text, id_range = _read_project_entries(project_dir)
            assert "body one" in text
            assert "body two" in text
            assert id_range == ("MSG-0001", "MSG-0002")

    def test_empty_project_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "P"
            (project_dir / "messages").mkdir(parents=True)
            text, id_range = _read_project_entries(project_dir)
            assert text == ""
            assert id_range is None

    def test_limit_takes_most_recent(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "P"
            (project_dir / "messages").mkdir(parents=True)
            for i in range(1, 6):
                _write_journal_entry(project_dir / "messages", f"MSG-{i:04d}", f"body {i}")
            text, id_range = _read_project_entries(project_dir, limit=2)
            assert "body 4" in text and "body 5" in text
            assert "body 1" not in text
            assert id_range == ("MSG-0004", "MSG-0005")


class TestUpdateProjectSummary:
    def _setup(self, tmp: str) -> dict:
        journals = Path(tmp) / "journals"
        summaries = Path(tmp) / "summaries"
        project_dir = journals / "InterAI-Protocol" / "messages"
        project_dir.mkdir(parents=True)
        _write_journal_entry(project_dir, "MSG-0001", "content one")
        _write_journal_entry(project_dir, "MSG-0002", "content two")
        return {"journals": journals, "summaries": summaries}

    def test_writes_summary_yml_and_advances_meta(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = self._setup(tmp)
            cfg = _cfg()
            client = _fake_anthropic_client(
                "<FULL>f</FULL><COMPRESSED>c</COMPRESSED><SHORTHAND>s</SHORTHAND>"
            )
            result = update_project_summary(
                "InterAI-Protocol",
                journals_root=paths["journals"],
                summaries_root=paths["summaries"],
                config=cfg,
                client=client,
            )
            # Persisted summary matches returned summary.
            loaded = read_summary(paths["summaries"], "InterAI-Protocol")
            assert loaded is not None
            assert loaded.full == "f"
            assert loaded.compressed == "c"
            assert loaded.shorthand == "s"

            # summary_meta advanced.
            meta = read_meta(paths["summaries"], "InterAI-Protocol")
            assert meta is not None
            assert meta.last_entry_id == "MSG-0002"
            assert meta.entries_since_last_summary == 0

    def test_empty_project_leaves_state_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            journals = Path(tmp) / "journals"
            summaries = Path(tmp) / "summaries"
            (journals / "Empty" / "messages").mkdir(parents=True)
            cfg = _cfg()
            # Client must not be called since there's nothing to summarize.
            class Boom:
                class messages:
                    @staticmethod
                    def create(**kwargs):
                        raise AssertionError("should not call")
            result = update_project_summary(
                "Empty",
                journals_root=journals,
                summaries_root=summaries,
                config=cfg,
                client=Boom(),
            )
            assert result.full == ""
            # No summary.yml written
            assert read_summary(summaries, "Empty") is None
