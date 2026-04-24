"""
Backfill the chunk_index from existing journal files.

For every AICP .md file under <journals_root>/<project>/messages/, parse
the headers and payload and upsert a chunk row with embedding=NULL. Run
scripts/backfill_embeddings.py afterwards to populate the embeddings.

This is the one-time step that turns historical journal entries into a
searchable RAG corpus. Journal entries written before the indexer hook
was wired (commit 5734909) never got chunked; this script repairs that.

Idempotent: upsert uses ON CONFLICT DO UPDATE, so running this twice
produces the same end state as running it once.

Usage:
    python scripts/backfill_index_from_journals.py                       # all projects
    python scripts/backfill_index_from_journals.py --project InterAI-Protocol
    python scripts/backfill_index_from_journals.py --dry-run             # count only
    python scripts/backfill_index_from_journals.py --journals "H:/Code/Agent-Journals"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterator, Optional


REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from middleware.fidelity_check import parse_aicp_file
from middleware.summary_index import upsert_chunk


DEFAULT_JOURNALS_ROOT = Path("H:/Code/Agent-Journals")
DEFAULT_DB_PATH = REPO_ROOT / "summaries" / "index.db"


def walk_journal_files(
    journals_root: Path,
    project_filter: Optional[str] = None,
) -> Iterator[tuple[str, Path]]:
    """Yield (project_name, file_path) for every AICP .md file under
    <journals_root>/<project>/messages/."""
    if not journals_root.is_dir():
        return
    for project_dir in sorted(journals_root.iterdir()):
        if not project_dir.is_dir():
            continue
        if project_filter is not None and project_dir.name != project_filter:
            continue
        messages_dir = project_dir / "messages"
        if not messages_dir.is_dir():
            continue
        for f in sorted(messages_dir.glob("*.md")):
            yield project_dir.name, f


def backfill(
    journals_root: Path,
    db_path: Path,
    project_filter: Optional[str] = None,
    dry_run: bool = False,
) -> dict:
    files = list(walk_journal_files(journals_root, project_filter))

    if dry_run:
        by_project: dict[str, int] = {}
        for p, _ in files:
            by_project[p] = by_project.get(p, 0) + 1
        return {
            "dry_run": True,
            "total_files": len(files),
            "by_project": by_project,
            "journals_root": str(journals_root),
        }

    upserted = 0
    skipped = 0
    errors: list[dict] = []

    for project, fpath in files:
        try:
            fields = parse_aicp_file(fpath)
        except Exception as e:
            errors.append({"file": str(fpath), "reason": f"parse: {e}"})
            continue

        msg_id = fields.get("$ID", "")
        if not msg_id:
            skipped += 1
            errors.append({"file": str(fpath), "reason": "no $ID header"})
            continue

        entry_type = fields.get("$TYPE", "UNKNOWN").upper() or "UNKNOWN"
        from_agent = fields.get("$FROM", "UNKNOWN") or "UNKNOWN"
        content = fields.get("payload", "") or ""

        if not content:
            # Still upsert with empty content so the row exists; embedder
            # will skip empty content and the row stays with NULL embedding.
            # That's fine — retrieval filters out NULL-embedding rows anyway.
            pass

        try:
            upsert_chunk(
                db_path,
                chunk_id=msg_id,
                project=project,
                entry_type=entry_type,
                from_agent=from_agent,
                content=content,
            )
            upserted += 1
        except Exception as e:
            errors.append({"file": str(fpath), "reason": f"upsert: {e}"})

    return {
        "dry_run": False,
        "total_files": len(files),
        "upserted": upserted,
        "skipped": skipped,
        "errors_count": len(errors),
        "errors": errors[:10],  # cap for console sanity
        "journals_root": str(journals_root),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill chunk_index from journal files.")
    parser.add_argument("--journals", default=str(DEFAULT_JOURNALS_ROOT),
                        help=f"Journal root (default: {DEFAULT_JOURNALS_ROOT})")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH),
                        help=f"Index DB path (default: {DEFAULT_DB_PATH})")
    parser.add_argument("--project", default=None,
                        help="Limit to one project (default: all under journal root)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Count files by project; do not write")
    args = parser.parse_args()

    journals_root = Path(args.journals)
    db_path = Path(args.db)

    if not journals_root.is_dir():
        print(f"[ERROR] journal root not found: {journals_root}", file=sys.stderr)
        return 2

    result = backfill(
        journals_root=journals_root,
        db_path=db_path,
        project_filter=args.project,
        dry_run=args.dry_run,
    )

    for k, v in result.items():
        if k == "errors" and v:
            print(f"{k}:")
            for err in v:
                print(f"  - {err}")
        else:
            print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
