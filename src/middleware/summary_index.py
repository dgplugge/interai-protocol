"""
RAG chunk index (Q9 + Q11 from the Summarizer-Role design).

Stores one row per $ID-tagged journal entry (Lumen's Q9 chunk boundary)
in a SQLite database (Pharos's Q11 storage substrate). The embedding
column is nullable BLOB — populated when the embedder (Trident's Q10:
sentence-transformers/all-MiniLM-L6-v2) is wired in a later slice.

This module is the storage + CRUD layer only. It does not:
  - Generate embeddings (TO ADD: embedding slice).
  - Compute similarity for retrieval (TO ADD: retrieval slice).
  - Subscribe to journal-write events (TO ADD: wire into the api/server.py
    post-commit path once CRUD is proven).

Design trace:
  Q9  (Lumen): chunk boundary is per $ID-tagged journal entry.
  Q10 (Trident): cosine similarity via sqlite-vss over MiniLM embeddings.
  Q11 (Pharos): SQLite file alongside summary_meta, single table with
       project column for multi-project isolation.
  Q12 (Lodestar): retrieval augments the compressed-tier prompt-prefix;
       the tier selection lives in the retrieval layer, not here.

See Forge's Round 7 failure modes:
  (1) last_indexed misalignment with summary_meta.last_entry_id — caller
      is expected to assert this after upsert.
  (2) anomalous embedding similarity — handled in the retrieval layer.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

from middleware.token_estimator import estimate_tokens


_SCHEMA = """
CREATE TABLE IF NOT EXISTS chunk_index (
    chunk_id     TEXT PRIMARY KEY,
    project      TEXT NOT NULL,
    entry_type   TEXT NOT NULL,
    from_agent   TEXT NOT NULL,
    content      TEXT NOT NULL,
    embedding    BLOB,
    token_count  INTEGER NOT NULL,
    last_indexed TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_chunk_project ON chunk_index(project);
CREATE INDEX IF NOT EXISTS idx_chunk_type    ON chunk_index(entry_type);
CREATE INDEX IF NOT EXISTS idx_chunk_from    ON chunk_index(from_agent);
"""


@dataclass
class Chunk:
    chunk_id: str
    project: str
    entry_type: str
    from_agent: str
    content: str
    token_count: int
    last_indexed: str
    embedding: Optional[bytes] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Chunk":
        return cls(
            chunk_id=row["chunk_id"],
            project=row["project"],
            entry_type=row["entry_type"],
            from_agent=row["from_agent"],
            content=row["content"],
            token_count=row["token_count"],
            last_indexed=row["last_indexed"],
            embedding=row["embedding"],
        )


@contextmanager
def _connect(db_path: Path | str) -> Iterator[sqlite3.Connection]:
    """Open a SQLite connection, commit on normal exit, always close.

    sqlite3.Connection's own context manager commits/rolls back a
    transaction but does NOT close the connection — on Windows that
    leaves the DB file locked against tempdir cleanup and any later
    unlink. We wrap explicitly.
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Path | str) -> None:
    """Create the chunk_index table and indexes if they do not exist."""
    with _connect(db_path) as conn:
        conn.executescript(_SCHEMA)


def upsert_chunk(
    db_path: Path | str,
    chunk_id: str,
    project: str,
    entry_type: str,
    from_agent: str,
    content: str,
    embedding: Optional[bytes] = None,
) -> Chunk:
    """Insert or replace a chunk. Token count is computed from content length."""
    if not chunk_id:
        raise ValueError("chunk_id is required")
    if not project:
        raise ValueError("project is required")

    token_count = estimate_tokens(content)
    last_indexed = datetime.now(timezone.utc).isoformat()

    with _connect(db_path) as conn:
        conn.executescript(_SCHEMA)
        conn.execute(
            """
            INSERT INTO chunk_index
                (chunk_id, project, entry_type, from_agent, content,
                 embedding, token_count, last_indexed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chunk_id) DO UPDATE SET
                project      = excluded.project,
                entry_type   = excluded.entry_type,
                from_agent   = excluded.from_agent,
                content      = excluded.content,
                embedding    = excluded.embedding,
                token_count  = excluded.token_count,
                last_indexed = excluded.last_indexed
            """,
            (chunk_id, project, entry_type, from_agent, content,
             embedding, token_count, last_indexed),
        )

    return Chunk(
        chunk_id=chunk_id,
        project=project,
        entry_type=entry_type,
        from_agent=from_agent,
        content=content,
        token_count=token_count,
        last_indexed=last_indexed,
        embedding=embedding,
    )


def get_chunk(db_path: Path | str, chunk_id: str) -> Optional[Chunk]:
    with _connect(db_path) as conn:
        conn.executescript(_SCHEMA)
        row = conn.execute(
            "SELECT * FROM chunk_index WHERE chunk_id = ?",
            (chunk_id,),
        ).fetchone()
    return Chunk.from_row(row) if row else None


def list_chunks(
    db_path: Path | str,
    project: Optional[str] = None,
    entry_type: Optional[str] = None,
    from_agent: Optional[str] = None,
) -> list[Chunk]:
    """Enumerate chunks with optional filters. Results ordered by chunk_id."""
    clauses: list[str] = []
    params: list[str] = []
    if project is not None:
        clauses.append("project = ?")
        params.append(project)
    if entry_type is not None:
        clauses.append("entry_type = ?")
        params.append(entry_type)
    if from_agent is not None:
        clauses.append("from_agent = ?")
        params.append(from_agent)

    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"SELECT * FROM chunk_index{where} ORDER BY chunk_id"

    with _connect(db_path) as conn:
        conn.executescript(_SCHEMA)
        rows = conn.execute(query, params).fetchall()
    return [Chunk.from_row(r) for r in rows]


def delete_chunk(db_path: Path | str, chunk_id: str) -> bool:
    """Remove a chunk by ID. Returns True if a row was deleted, False otherwise."""
    with _connect(db_path) as conn:
        conn.executescript(_SCHEMA)
        cur = conn.execute(
            "DELETE FROM chunk_index WHERE chunk_id = ?",
            (chunk_id,),
        )
        deleted = cur.rowcount > 0
    return deleted


def chunk_count(db_path: Path | str, project: Optional[str] = None) -> int:
    """Return the number of chunks, optionally filtered by project."""
    with _connect(db_path) as conn:
        conn.executescript(_SCHEMA)
        if project is None:
            row = conn.execute("SELECT COUNT(*) FROM chunk_index").fetchone()
        else:
            row = conn.execute(
                "SELECT COUNT(*) FROM chunk_index WHERE project = ?",
                (project,),
            ).fetchone()
    return int(row[0])
