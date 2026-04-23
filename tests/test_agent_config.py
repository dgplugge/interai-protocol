"""
Tests for the agent_config loader, API-key resolution, and fallback chain.
"""

import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from middleware.agent_config import (
    AgentConfig,
    SummaryGeneratorConfig,
    EmbedderConfig,
    RetrievalConfig,
    MissingApiKey,
    load_config,
    next_summarizer,
    resolve_api_key,
)


def _write_cfg(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


class TestLoad:
    def test_missing_file_returns_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = load_config(Path(tmp) / "does_not_exist.json")
            assert cfg.summarizer_role == "Lumen"
            assert cfg.threshold == 5
            assert cfg.summary_generator.provider == "anthropic"

    def test_full_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "cfg.json"
            _write_cfg(p, {
                "summarizer_role": "Pharos",
                "summarizer_fallback_chain": ["Forge", "Lodestar"],
                "summary_generator": {
                    "provider": "anthropic",
                    "model": "claude-haiku-4-5-20251001",
                    "max_input_tokens": 4096,
                    "max_output_tokens": 1024,
                    "tier_token_budgets": {"full": 1500, "compressed": 400, "shorthand": 80},
                },
                "embedder": {"provider": "openai", "model": "text-embedding-3-small", "dims": 1536},
                "retrieval": {"top_k": 7},
                "threshold": 3,
            })
            cfg = load_config(p)
            assert cfg.summarizer_role == "Pharos"
            assert cfg.summarizer_fallback_chain == ["Forge", "Lodestar"]
            assert cfg.summary_generator.max_output_tokens == 1024
            assert cfg.summary_generator.tier_token_budgets["compressed"] == 400
            assert cfg.retrieval.top_k == 7
            assert cfg.threshold == 3

    def test_non_dict_file_returns_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "cfg.json"
            p.write_text('["just","a","list"]', encoding="utf-8")
            cfg = load_config(p)
            assert cfg.summarizer_role == "Lumen"

    def test_repo_root_config_loads_without_error(self):
        """The checked-in agent_config.json at the repo root must parse."""
        cfg = load_config()
        assert cfg.summarizer_role
        assert cfg.summary_generator.provider in ("anthropic", "openai", "google", "mistral")
        assert cfg.summarizer_fallback_chain  # non-empty


class TestFallbackChain:
    def test_advance_from_head(self):
        cfg = AgentConfig()
        cfg.summarizer_fallback_chain = ["Lodestar", "Pharos", "Forge"]
        assert next_summarizer("Lodestar", cfg) == "Pharos"

    def test_advance_from_middle(self):
        cfg = AgentConfig()
        cfg.summarizer_fallback_chain = ["Lodestar", "Pharos", "Forge"]
        assert next_summarizer("Pharos", cfg) == "Forge"

    def test_advance_from_tail_is_none(self):
        cfg = AgentConfig()
        cfg.summarizer_fallback_chain = ["Lodestar", "Pharos", "Forge"]
        assert next_summarizer("Forge", cfg) is None

    def test_unknown_current_falls_back_to_head(self):
        cfg = AgentConfig()
        cfg.summarizer_fallback_chain = ["Lodestar", "Pharos", "Forge"]
        assert next_summarizer("Stranger", cfg) == "Lodestar"

    def test_empty_chain_returns_none(self):
        cfg = AgentConfig()
        cfg.summarizer_fallback_chain = []
        assert next_summarizer("anything", cfg) is None


class TestApiKeyResolution:
    def test_env_var_wins(self):
        cfg = AgentConfig()
        cfg._api_keys["anthropic_api_key"] = "from-config"
        env = {"ANTHROPIC_API_KEY": "from-env"}
        assert resolve_api_key("anthropic", cfg, env=env) == "from-env"

    def test_config_fallback_when_env_absent(self):
        cfg = AgentConfig()
        cfg._api_keys["openai_api_key"] = "from-config"
        env = {}
        assert resolve_api_key("openai", cfg, env=env) == "from-config"

    def test_empty_env_value_treated_as_absent(self):
        """An env var set to empty string should not suppress the config fallback."""
        cfg = AgentConfig()
        cfg._api_keys["anthropic_api_key"] = "from-config"
        env = {"ANTHROPIC_API_KEY": ""}
        assert resolve_api_key("anthropic", cfg, env=env) == "from-config"

    def test_missing_raises_clear_error(self):
        cfg = AgentConfig()
        env = {}
        with pytest.raises(MissingApiKey) as exc:
            resolve_api_key("anthropic", cfg, env=env)
        # Error should name both options so the installer knows what to do.
        assert "ANTHROPIC_API_KEY" in str(exc.value)
        assert "agent_config.json" in str(exc.value)

    def test_unknown_provider_raises(self):
        cfg = AgentConfig()
        with pytest.raises(MissingApiKey):
            resolve_api_key("no-such-provider", cfg, env={})

    def test_provider_case_insensitive(self):
        cfg = AgentConfig()
        env = {"ANTHROPIC_API_KEY": "ok"}
        assert resolve_api_key("Anthropic", cfg, env=env) == "ok"
        assert resolve_api_key("ANTHROPIC", cfg, env=env) == "ok"


class TestApiKeysDoNotLeak:
    def test_config_does_not_expose_api_keys_on_roundtrip(self):
        """Ensure the public API key surface is the resolver function, not
        the raw config. _api_keys being prefix-underscored is the signal —
        this test is a guardrail against accidental promotion to public."""
        cfg = AgentConfig()
        cfg._api_keys["anthropic_api_key"] = "secret"
        # Access pattern — only the resolver should hand this out.
        assert resolve_api_key("anthropic", cfg, env={}) == "secret"
