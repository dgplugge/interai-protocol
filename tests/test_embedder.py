"""
Tests for the embedder module. Uses a mock OpenAI client — the real API is
never called in unit tests. The mock is injected via the `client` parameter.
"""

import struct
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from middleware.embedder import (
    EmbedError,
    embed_text,
    embed_text_batch,
    pack_float32,
    unpack_float32,
)
from middleware.agent_config import AgentConfig, EmbedderConfig


def _fake_openai_client(vectors: list[list[float]]):
    """Build a mock client whose embeddings.create returns the given vectors
    (one response item per vector). Raises if .create is called with input
    whose length does not match the vector list."""
    def create(model, input):
        # Normalize input to a list for comparison.
        items = input if isinstance(input, list) else [input]
        assert len(items) == len(vectors), \
            f"mock configured for {len(vectors)} vectors but got {len(items)} inputs"
        return SimpleNamespace(
            data=[SimpleNamespace(embedding=v) for v in vectors],
        )
    return SimpleNamespace(embeddings=SimpleNamespace(create=create))


class TestPackUnpack:
    def test_round_trip(self):
        vec = [0.1, -0.2, 3.14, -1.0, 0.0]
        packed = pack_float32(vec)
        assert len(packed) == len(vec) * 4
        unpacked = unpack_float32(packed)
        assert len(unpacked) == len(vec)
        for a, b in zip(vec, unpacked):
            assert abs(a - b) < 1e-6

    def test_1536_dim_length(self):
        """OpenAI text-embedding-3-small is 1536 dims → 6144 bytes."""
        vec = [0.001 * i for i in range(1536)]
        packed = pack_float32(vec)
        assert len(packed) == 1536 * 4

    def test_unpack_rejects_non_aligned_bytes(self):
        with pytest.raises(ValueError):
            unpack_float32(b"\x01\x02\x03")


class TestEmbedText:
    def _cfg(self):
        c = AgentConfig()
        c.embedder = EmbedderConfig(provider="openai", model="text-embedding-3-small", dims=1536)
        return c

    def test_single_vector_packs_correctly(self):
        cfg = self._cfg()
        vec = [0.5, -0.5, 0.25]
        client = _fake_openai_client([vec])
        blob = embed_text("hello", config=cfg, client=client)
        assert unpack_float32(blob) == pytest.approx(vec)

    def test_empty_text_raises(self):
        cfg = self._cfg()
        with pytest.raises(EmbedError):
            embed_text("", config=cfg, client=object())

    def test_non_openai_provider_raises(self):
        cfg = AgentConfig()
        cfg.embedder = EmbedderConfig(provider="google", model="something")
        with pytest.raises(EmbedError):
            embed_text("hi", config=cfg, client=object())

    def test_api_failure_wraps_as_embed_error(self):
        cfg = self._cfg()

        class BoomClient:
            class embeddings:
                @staticmethod
                def create(model, input):
                    raise RuntimeError("network down")

        with pytest.raises(EmbedError) as exc:
            embed_text("hi", config=cfg, client=BoomClient())
        assert "network down" in str(exc.value)


class TestEmbedBatch:
    def _cfg(self):
        c = AgentConfig()
        c.embedder = EmbedderConfig(provider="openai", model="text-embedding-3-small", dims=1536)
        return c

    def test_batch_returns_one_blob_per_input(self):
        cfg = self._cfg()
        vectors = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        client = _fake_openai_client(vectors)
        blobs = embed_text_batch(["a", "b", "c"], config=cfg, client=client)
        assert len(blobs) == 3
        for blob, vec in zip(blobs, vectors):
            assert unpack_float32(blob) == pytest.approx(vec)

    def test_empty_list_short_circuits(self):
        cfg = self._cfg()
        assert embed_text_batch([], config=cfg) == []

    def test_any_empty_string_rejected(self):
        cfg = self._cfg()
        with pytest.raises(EmbedError):
            embed_text_batch(["a", "", "c"], config=cfg, client=object())

    def test_mismatched_response_length_raises(self):
        cfg = self._cfg()

        class BadClient:
            class embeddings:
                @staticmethod
                def create(model, input):
                    # Respond with fewer vectors than requested.
                    return SimpleNamespace(data=[SimpleNamespace(embedding=[0.1, 0.2])])

        with pytest.raises(EmbedError) as exc:
            embed_text_batch(["a", "b"], config=cfg, client=BadClient())
        assert "1 embeddings for 2 inputs" in str(exc.value)
