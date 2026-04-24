"""
Tests for the journal-to-index backfill utility.

Builds a fake Agent-Journals layout on disk, runs the backfill, and
asserts the resulting chunk rows match the input files.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from middleware.summary_index import chunk_count, get_chunk

import backfill_index_from_journals as bj


def _write_aicp(path: Path, msg_id: str, msg_type: str = "UPDATE",
                from_agent: str = "Pharos", task: str = "t",
                status: str = "CLOSED", payload: str = "body") -> None:
    path.write_text(
        "$PROTO: AICP/1.0\n"
        f"$TYPE: {msg_type}\n"
        f"$ID: {msg_id}\n"
        f"$FROM: {from_agent}\n"
        "$TO: All\n"
        "$TIME: 2026-04-24T10:00:00-04:00\n"
        f"$TASK: {task}\n"
        f"$STATUS: {status}\n"
        "\n---PAYLOAD---\n\n"
        f"{payload}\n"
        "---END---\n",
        encoding="utf-8",
    )


def _seed_fake_journals(root: Path) -> None:
    """Two projects, three entries each."""
    for project, entries in [
        ("InterAI-Protocol", [
            ("MSG-0001", "UPDATE", "Pharos", "interai one"),
            ("MSG-0002", "RESPONSE", "Lumen", "interai two"),
            ("MSG-0003", "REPORT", "Forge", "interai three"),
        ]),
        ("OperatorHub", [
            ("MSG-0100", "UPDATE", "Don", "ophub one"),
            ("MSG-0101", "PLAN", "Lodestar", "ophub two"),
        ]),
    ]:
        messages_dir = root / project / "messages"
        messages_dir.mkdir(parents=True)
        for msg_id, msg_type, from_agent, payload in entries:
            _write_aicp(
                messages_dir / f"2026-04-24-{msg_id}-{msg_type.lower()}-{from_agent.lower()}.md",
                msg_id, msg_type, from_agent, payload=payload,
            )


class TestWalker:
    def test_yields_every_file_grouped_by_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_fake_journals(root)
            pairs = list(bj.walk_journal_files(root))
            assert len(pairs) == 5
            projects = {p for p, _ in pairs}
            assert projects == {"InterAI-Protocol", "OperatorHub"}

    def test_project_filter_narrows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_fake_journals(root)
            pairs = list(bj.walk_journal_files(root, project_filter="InterAI-Protocol"))
            assert len(pairs) == 3
            assert all(p == "InterAI-Protocol" for p, _ in pairs)

    def test_missing_root_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            # No subdirs, no messages dirs.
            assert list(bj.walk_journal_files(Path(tmp))) == []

    def test_project_dir_without_messages_subdir_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "BareProject").mkdir()  # no messages subdir
            pairs = list(bj.walk_journal_files(root))
            assert pairs == []


class TestBackfillDryRun:
    def test_dry_run_counts_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_fake_journals(root)
            db = Path(tmp) / "idx.db"

            result = bj.backfill(root, db, dry_run=True)
            assert result["dry_run"] is True
            assert result["total_files"] == 5
            assert result["by_project"] == {"InterAI-Protocol": 3, "OperatorHub": 2}

            # DB was not created by a dry-run.
            assert not db.exists()


class TestBackfillExecutes:
    def test_all_files_upserted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_fake_journals(root)
            db = Path(tmp) / "idx.db"

            result = bj.backfill(root, db, dry_run=False)
            assert result["upserted"] == 5
            assert result["skipped"] == 0
            assert result["errors_count"] == 0
            assert chunk_count(db) == 5

    def test_content_and_metadata_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_fake_journals(root)
            db = Path(tmp) / "idx.db"
            bj.backfill(root, db)

            c = get_chunk(db, "MSG-0002")
            assert c is not None
            assert c.project == "InterAI-Protocol"
            assert c.entry_type == "RESPONSE"
            assert c.from_agent == "Lumen"
            assert c.content == "interai two"
            assert c.embedding is None  # intentionally NULL — embedder runs later

    def test_project_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_fake_journals(root)
            db = Path(tmp) / "idx.db"
            bj.backfill(root, db, project_filter="OperatorHub")
            assert chunk_count(db, project="InterAI-Protocol") == 0
            assert chunk_count(db, project="OperatorHub") == 2

    def test_idempotent_rerun(self):
        """Running twice must produce the same row count — upsert not insert."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_fake_journals(root)
            db = Path(tmp) / "idx.db"
            bj.backfill(root, db)
            bj.backfill(root, db)
            assert chunk_count(db) == 5

    def test_missing_id_is_skipped_with_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            messages_dir = root / "InterAI-Protocol" / "messages"
            messages_dir.mkdir(parents=True)
            # Malformed AICP file — no $ID line
            (messages_dir / "bad.md").write_text(
                "$PROTO: AICP/1.0\n$TASK: t\n$STATUS: CLOSED\n", encoding="utf-8"
            )
            db = Path(tmp) / "idx.db"

            result = bj.backfill(root, db)
            assert result["upserted"] == 0
            assert result["skipped"] == 1
            assert result["errors_count"] == 1
            assert "no $ID header" in result["errors"][0]["reason"]

    def test_empty_payload_still_upserts(self):
        """An entry with empty payload still lands — retrieval filters on
        NULL embedding, not empty content."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            messages_dir = root / "P" / "messages"
            messages_dir.mkdir(parents=True)
            _write_aicp(messages_dir / "m.md", "MSG-0001", payload="")
            db = Path(tmp) / "idx.db"
            bj.backfill(root, db)
            c = get_chunk(db, "MSG-0001")
            assert c is not None
            assert c.content == ""
