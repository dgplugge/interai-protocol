"""
Tests for the Q3 fidelity check runner.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from middleware.fidelity_check import (
    EXPECTED_STATUS,
    FidelityIssue,
    FidelityReport,
    parse_aicp_file,
    check_message,
    check_file,
    check_project,
)
from middleware.summary_index import upsert_chunk


def _write_aicp(path: Path, fields: dict, payload: str = "body") -> None:
    lines = []
    for k, v in fields.items():
        lines.append(f"{k}: {v}")
    lines.append("")
    lines.append("---PAYLOAD---")
    lines.append("")
    lines.append(payload)
    lines.append("---END---")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _valid_headers(msg_id="MSG-0001", decision=None, task="t", status="CLOSED") -> dict:
    h = {
        "$PROTO": "AICP/1.0",
        "$TYPE": "UPDATE",
        "$ID": msg_id,
        "$FROM": "Pharos",
        "$TO": "All",
        "$TIME": "2026-04-23T13:00:00-04:00",
        "$TASK": task,
        "$STATUS": status,
    }
    if decision is not None:
        h["$DECISION"] = decision
    return h


class TestParse:
    def test_basic_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "test.md"
            _write_aicp(f, _valid_headers(), payload="hello world")
            parsed = parse_aicp_file(f)
            assert parsed["$ID"] == "MSG-0001"
            assert parsed["$TASK"] == "t"
            assert parsed["$STATUS"] == "CLOSED"
            assert parsed["payload"] == "hello world"

    def test_missing_payload_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "test.md"
            # Header only, no payload block
            f.write_text("$ID: MSG-0001\n$TASK: t\n$STATUS: CLOSED\n", encoding="utf-8")
            parsed = parse_aicp_file(f)
            assert parsed["payload"] == ""

    def test_multiline_payload_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "test.md"
            _write_aicp(f, _valid_headers(), payload="line one\nline two\nline three")
            parsed = parse_aicp_file(f)
            assert "line one" in parsed["payload"]
            assert "line three" in parsed["payload"]


class TestCheckMessage:
    def test_valid_message_has_no_issues(self):
        msg = _valid_headers() | {"payload": "body"}
        assert check_message(msg) == []

    def test_valid_decision_passes(self):
        msg = _valid_headers(decision="EXECUTE") | {"payload": "body"}
        assert check_message(msg) == []

    def test_invalid_decision_is_flagged(self):
        msg = _valid_headers(decision="APPROVED") | {"payload": "body"}
        issues = check_message(msg)
        assert any(i.code == "INVALID_DECISION" for i in issues)

    def test_empty_task_is_flagged(self):
        msg = _valid_headers(task="") | {"payload": "body"}
        issues = check_message(msg)
        assert any(i.code == "EMPTY_TASK" for i in issues)

    def test_missing_status_is_flagged(self):
        msg = _valid_headers() | {"payload": "body"}
        msg.pop("$STATUS")
        issues = check_message(msg)
        assert any(i.code == "MISSING_STATUS" for i in issues)

    def test_unknown_status_is_flagged(self):
        msg = _valid_headers(status="DONE_ISH") | {"payload": "body"}
        issues = check_message(msg)
        assert any(i.code == "UNKNOWN_STATUS" for i in issues)

    def test_all_expected_statuses_pass(self):
        for s in EXPECTED_STATUS:
            msg = _valid_headers(status=s) | {"payload": "body"}
            issues = check_message(msg)
            assert not any(i.code in ("MISSING_STATUS", "UNKNOWN_STATUS") for i in issues), s

    def test_payload_matches_baseline(self):
        msg = _valid_headers() | {"payload": "exact content"}
        assert check_message(msg, baseline="exact content") == []

    def test_payload_drift_is_flagged(self):
        msg = _valid_headers() | {"payload": "drifted content"}
        issues = check_message(msg, baseline="original content")
        assert any(i.code == "PAYLOAD_DRIFT" for i in issues)

    def test_baseline_trimming_is_tolerant(self):
        """Leading/trailing whitespace should not trip PAYLOAD_DRIFT."""
        msg = _valid_headers() | {"payload": "  body  \n"}
        assert check_message(msg, baseline="body") == []


class TestCheckFile:
    def test_file_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "msg.md"
            _write_aicp(f, _valid_headers(), payload="hi")
            assert check_file(f) == []

    def test_file_with_bad_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "msg.md"
            _write_aicp(f, _valid_headers(decision="WAT"), payload="hi")
            issues = check_file(f)
            assert any(i.code == "INVALID_DECISION" for i in issues)


class TestCheckProject:
    def _seed_journal(self, tmp: str, count: int = 3) -> Path:
        journal = Path(tmp) / "journals" / "TestProject"
        (journal / "messages").mkdir(parents=True)
        for i in range(1, count + 1):
            f = journal / "messages" / f"2026-04-23-MSG-{i:04d}-update-pharos.md"
            _write_aicp(f, _valid_headers(msg_id=f"MSG-{i:04d}"), payload=f"body {i}")
        return journal

    def test_all_valid_project_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = self._seed_journal(tmp, count=3)
            report = check_project(journal)
            assert report.messages_checked == 3
            assert report.passed is True

    def test_project_with_one_bad_message_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = self._seed_journal(tmp, count=2)
            bad = journal / "messages" / "2026-04-23-MSG-0003-update-pharos.md"
            _write_aicp(bad, _valid_headers(msg_id="MSG-0003", task=""))
            report = check_project(journal)
            assert report.messages_checked == 3
            assert report.passed is False
            assert any(i.message_id == "MSG-0003" and i.code == "EMPTY_TASK"
                       for i in report.issues)

    def test_missing_messages_dir_returns_empty_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = Path(tmp) / "empty_project"
            journal.mkdir()
            report = check_project(journal)
            assert report.messages_checked == 0
            assert report.passed is True

    def test_limit_caps_files_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = self._seed_journal(tmp, count=5)
            report = check_project(journal, limit=2)
            assert report.messages_checked == 2

    def test_payload_baseline_via_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = self._seed_journal(tmp, count=1)
            db = str(Path(tmp) / "index.db")
            # Seed the index with the exact payload the journal has
            upsert_chunk(db, "MSG-0001", "TestProject", "UPDATE", "Pharos", "body 1")
            report = check_project(journal, index_db=db)
            assert report.passed is True

    def test_index_mismatch_is_payload_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = self._seed_journal(tmp, count=1)
            db = str(Path(tmp) / "index.db")
            # Index says the content should be something different
            upsert_chunk(db, "MSG-0001", "TestProject", "UPDATE", "Pharos", "different")
            report = check_project(journal, index_db=db)
            assert report.passed is False
            assert any(i.code == "PAYLOAD_DRIFT" for i in report.issues)


class TestReport:
    def test_to_dict_round_trip(self):
        r = FidelityReport(messages_checked=2)
        r.issues.append(FidelityIssue("MSG-0001", "EMPTY_TASK", "missing"))
        d = r.to_dict()
        assert d["messages_checked"] == 2
        assert d["passed"] is False
        assert d["issues"][0]["code"] == "EMPTY_TASK"
