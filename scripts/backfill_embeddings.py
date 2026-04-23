"""
Backfill embeddings for chunks that landed before the embedder was wired
(or while no API key was set). Walks chunk_index, gathers rows with
embedding IS NULL, batches them through the embedder, and upserts the
resulting vectors.

Usage:
    python scripts/backfill_embeddings.py                 # default batch=32
    python scripts/backfill_embeddings.py --batch 64
    python scripts/backfill_embeddings.py --project InterAI-Protocol
    python scripts/backfill_embeddings.py --dry-run       # report only

Prerequisites:
    OPENAI_API_KEY set in env (or openai_api_key in agent_config.json).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Let the script run from the repo root without install.
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from middleware.agent_config import load_config, MissingApiKey, resolve_api_key
from middleware.embedder import embed_text_batch, EmbedError
from middleware.summary_index import list_chunks, upsert_chunk


def find_missing(db_path: Path, project: str | None) -> list:
    chunks = list_chunks(db_path, project=project) if project else list_chunks(db_path)
    return [c for c in chunks if not c.embedding]


def backfill(
    db_path: Path,
    project: str | None,
    batch_size: int,
    dry_run: bool,
) -> dict:
    cfg = load_config()
    missing = find_missing(db_path, project)

    if dry_run:
        return {
            "dry_run": True,
            "missing_count": len(missing),
            "project_filter": project,
            "batch_size": batch_size,
        }

    if not missing:
        return {
            "dry_run": False,
            "missing_count": 0,
            "embedded": 0,
            "failed": 0,
            "project_filter": project,
        }

    # Probe the API key up front so we fail fast with a clear message.
    try:
        resolve_api_key("openai", cfg)
    except MissingApiKey as e:
        return {"error": str(e)}

    embedded = 0
    failed = 0
    for i in range(0, len(missing), batch_size):
        batch = missing[i : i + batch_size]
        texts = [c.content for c in batch]
        try:
            vectors = embed_text_batch(texts, config=cfg)
        except EmbedError as e:
            failed += len(batch)
            print(f"[WARN] batch {i // batch_size} failed: {e}")
            continue

        for chunk, vec in zip(batch, vectors):
            upsert_chunk(
                db_path,
                chunk_id=chunk.chunk_id,
                project=chunk.project,
                entry_type=chunk.entry_type,
                from_agent=chunk.from_agent,
                content=chunk.content,
                embedding=vec,
            )
            embedded += 1

    return {
        "dry_run": False,
        "missing_count": len(missing),
        "embedded": embedded,
        "failed": failed,
        "project_filter": project,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill missing chunk embeddings.")
    parser.add_argument(
        "--db",
        default=str(REPO_ROOT / "summaries" / "index.db"),
        help="Path to index.db (default: summaries/index.db at repo root)",
    )
    parser.add_argument(
        "--project",
        default=None,
        help="Limit to one project (default: all projects)",
    )
    parser.add_argument("--batch", type=int, default=32, help="Batch size (default 32)")
    parser.add_argument("--dry-run", action="store_true", help="Count only; do not call the API")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"[ERROR] index DB not found at {db_path}", file=sys.stderr)
        return 2

    result = backfill(
        db_path=db_path,
        project=args.project,
        batch_size=args.batch,
        dry_run=args.dry_run,
    )

    if "error" in result:
        print(f"[ERROR] {result['error']}", file=sys.stderr)
        return 1

    for k, v in result.items():
        print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
