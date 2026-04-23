"""
Embedding generator for RAG retrieval (Q5 / Q10 / Round 7 Trident).

Uses the OpenAI embeddings API (text-embedding-3-small, 1536 dims) per the
API-based embedder decision — no sentence-transformers, no torch, no local
model download. Stores the vector as a float32 byte blob suitable for the
nullable `embedding BLOB` column of `chunk_index`.

Caller responsibility: the journal write is the source of truth. An
embedding failure must not regress the journal. The API server hook wraps
`embed_text` in try/except for this reason.
"""

from __future__ import annotations

import struct
from typing import Any, Optional

from middleware.agent_config import AgentConfig, load_config, resolve_api_key


_FLOAT32_FMT = "<f"


def pack_float32(vec: list[float]) -> bytes:
    """Pack a vector of Python floats into a little-endian float32 byte blob.

    numpy is available but stdlib `struct` is sufficient and keeps the storage
    format explicit. A 1536-dim embedding becomes 6144 bytes.
    """
    return b"".join(struct.pack(_FLOAT32_FMT, float(x)) for x in vec)


def unpack_float32(blob: bytes) -> list[float]:
    """Inverse of pack_float32. Returns a Python list of floats."""
    n = len(blob) // 4
    if n * 4 != len(blob):
        raise ValueError(f"blob length {len(blob)} not a multiple of 4 bytes")
    return list(struct.unpack(f"<{n}f", blob))


class EmbedError(Exception):
    """Raised when embedding generation fails. Callers usually swallow this."""


def _default_openai_client(api_key: str):
    """Lazy import so the module loads without `openai` installed at test-time
    if a caller injects a fake client via the `client` parameter."""
    from openai import OpenAI
    return OpenAI(api_key=api_key)


def embed_text(
    text: str,
    config: Optional[AgentConfig] = None,
    client: Any = None,
    env: Optional[dict] = None,
) -> bytes:
    """Embed a single string. Returns a float32 byte blob.

    `client` is a duck-typed OpenAI client exposing `.embeddings.create(...)`.
    Tests pass a mock; production omits it and the real SDK client is built.
    """
    if not text:
        raise EmbedError("refusing to embed empty text")

    cfg = config or load_config()
    provider = cfg.embedder.provider.lower()

    if provider != "openai":
        raise EmbedError(
            f"embedder provider '{cfg.embedder.provider}' is not supported yet; "
            "only 'openai' is wired"
        )

    if client is None:
        key = resolve_api_key("openai", cfg, env=env)
        client = _default_openai_client(key)

    try:
        resp = client.embeddings.create(
            model=cfg.embedder.model,
            input=text,
        )
    except Exception as e:
        raise EmbedError(f"openai embeddings call failed: {e}") from e

    if not resp.data or not resp.data[0].embedding:
        raise EmbedError("openai returned empty embedding")

    return pack_float32(resp.data[0].embedding)


def embed_text_batch(
    texts: list[str],
    config: Optional[AgentConfig] = None,
    client: Any = None,
    env: Optional[dict] = None,
) -> list[bytes]:
    """Batch version. OpenAI supports list input to the embeddings endpoint;
    this is significantly cheaper than one call per text when backfilling an
    index. Empty strings raise rather than silently skipping — the caller
    should filter before calling.
    """
    if not texts:
        return []
    if any(not t for t in texts):
        raise EmbedError("embed_text_batch refuses empty strings in the list")

    cfg = config or load_config()
    provider = cfg.embedder.provider.lower()
    if provider != "openai":
        raise EmbedError(
            f"embedder provider '{cfg.embedder.provider}' is not supported yet"
        )

    if client is None:
        key = resolve_api_key("openai", cfg, env=env)
        client = _default_openai_client(key)

    try:
        resp = client.embeddings.create(
            model=cfg.embedder.model,
            input=texts,
        )
    except Exception as e:
        raise EmbedError(f"openai embeddings call failed: {e}") from e

    if not resp.data or len(resp.data) != len(texts):
        raise EmbedError(
            f"openai returned {len(resp.data) if resp.data else 0} embeddings "
            f"for {len(texts)} inputs"
        )

    return [pack_float32(item.embedding) for item in resp.data]
