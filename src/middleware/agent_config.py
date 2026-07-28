"""
Agent configuration loader (Q6 fallback chain + Summarizer settings).

Reads `agent_config.json` at the repo root (or a path supplied by the caller),
exposes the summarizer fallback chain and tier budgets, and provides API-key
resolution that checks environment variables first and falls back to config
fields. The environment-variable-first pattern lets an installer choose:
either set permanent OS env vars, or drop keys into a gitignored config file.

Secrets policy: API keys should not be committed. The repo's agent_config.json
carries no key fields; an installer who wants file-based keys must add them
locally (suggested key names: `anthropic_api_key`, `openai_api_key`). This
module raises a clear error when a key is requested and absent from both
sources.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


_DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "agent_config.json"


@dataclass
class SummaryGeneratorConfig:
    provider: str = "anthropic"
    model: str = "claude-haiku-4-5-20251001"
    max_input_tokens: int = 8192
    max_output_tokens: int = 2048
    tier_token_budgets: dict = field(default_factory=lambda: {
        "full": 2000, "compressed": 500, "shorthand": 100,
    })

    @classmethod
    def from_dict(cls, data: dict) -> "SummaryGeneratorConfig":
        c = cls()
        if "provider" in data:
            c.provider = str(data["provider"])
        if "model" in data:
            c.model = str(data["model"])
        if "max_input_tokens" in data:
            c.max_input_tokens = int(data["max_input_tokens"])
        if "max_output_tokens" in data:
            c.max_output_tokens = int(data["max_output_tokens"])
        if "tier_token_budgets" in data and isinstance(data["tier_token_budgets"], dict):
            c.tier_token_budgets = {k: int(v) for k, v in data["tier_token_budgets"].items()}
        return c


@dataclass
class EmbedderConfig:
    provider: str = "openai"
    model: str = "text-embedding-3-small"
    dims: int = 1536

    @classmethod
    def from_dict(cls, data: dict) -> "EmbedderConfig":
        c = cls()
        if "provider" in data:
            c.provider = str(data["provider"])
        if "model" in data:
            c.model = str(data["model"])
        if "dims" in data:
            c.dims = int(data["dims"])
        return c


@dataclass
class RetrievalConfig:
    top_k: int = 5

    @classmethod
    def from_dict(cls, data: dict) -> "RetrievalConfig":
        c = cls()
        if "top_k" in data:
            c.top_k = int(data["top_k"])
        return c


@dataclass
class SchedulerConfig:
    """Background summarizer scheduler. Disabled by default — enable in
    agent_config.json when the summary generator is configured with an API
    key and you want automated firing on threshold crossings."""
    enabled: bool = False
    interval_seconds: int = 300  # 5 minutes; summaries are expensive, avoid frequent runs

    @classmethod
    def from_dict(cls, data: dict) -> "SchedulerConfig":
        c = cls()
        if "enabled" in data:
            c.enabled = bool(data["enabled"])
        if "interval_seconds" in data:
            c.interval_seconds = max(5, int(data["interval_seconds"]))
        return c


@dataclass
class DispatchBudgetConfig:
    """Pre-dispatch context-window guard.

    These are context-window limits, not rate limits. Keep them explicit so
    provider request pacing cannot accidentally change prompt-size behavior.
    """
    enabled: bool = True
    expected_response_tokens: int = 2048
    default_context_tokens: int = 32000
    provider_context_tokens: dict = field(default_factory=lambda: {
        "anthropic": 200000,
        "openai": 128000,
        "google": 1000000,
        "mistral": 128000,
        "cohere": 128000,
    })

    @classmethod
    def from_dict(cls, data: dict) -> "DispatchBudgetConfig":
        c = cls()
        if "enabled" in data:
            c.enabled = bool(data["enabled"])
        if "expected_response_tokens" in data:
            c.expected_response_tokens = max(0, int(data["expected_response_tokens"]))
        if "default_context_tokens" in data:
            c.default_context_tokens = max(1, int(data["default_context_tokens"]))
        if "provider_context_tokens" in data and isinstance(data["provider_context_tokens"], dict):
            c.provider_context_tokens = {
                str(k).lower(): max(1, int(v))
                for k, v in data["provider_context_tokens"].items()
            }
        return c

    def limit_for_provider(self, provider: str) -> int:
        return self.provider_context_tokens.get(
            provider.lower(),
            self.default_context_tokens,
        )


@dataclass
class AgentConfig:
    summarizer_role: str = "Lumen"
    summarizer_fallback_chain: list[str] = field(default_factory=list)
    summary_generator: SummaryGeneratorConfig = field(default_factory=SummaryGeneratorConfig)
    embedder: EmbedderConfig = field(default_factory=EmbedderConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    dispatch_budget: DispatchBudgetConfig = field(default_factory=DispatchBudgetConfig)
    threshold: int = 5
    # Raw key-value fallback for API keys loaded from the config file.
    # Env vars always win over these.
    _api_keys: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "AgentConfig":
        c = cls()
        c.summarizer_role = str(data.get("summarizer_role", "Lumen"))
        fallback = data.get("summarizer_fallback_chain", [])
        c.summarizer_fallback_chain = [str(a) for a in fallback] if isinstance(fallback, list) else []

        if isinstance(data.get("summary_generator"), dict):
            c.summary_generator = SummaryGeneratorConfig.from_dict(data["summary_generator"])
        if isinstance(data.get("embedder"), dict):
            c.embedder = EmbedderConfig.from_dict(data["embedder"])
        if isinstance(data.get("retrieval"), dict):
            c.retrieval = RetrievalConfig.from_dict(data["retrieval"])
        if isinstance(data.get("scheduler"), dict):
            c.scheduler = SchedulerConfig.from_dict(data["scheduler"])
        if isinstance(data.get("dispatch_budget"), dict):
            c.dispatch_budget = DispatchBudgetConfig.from_dict(data["dispatch_budget"])

        c.threshold = int(data.get("threshold", 5))

        for k in ("anthropic_api_key", "openai_api_key", "google_api_key", "mistral_api_key"):
            if isinstance(data.get(k), str) and data[k]:
                c._api_keys[k] = data[k]

        return c


class MissingApiKey(Exception):
    """Raised when an API key is requested but absent from both env and config."""


def load_config(path: Path | str | None = None) -> AgentConfig:
    """Read agent_config.json from `path` (default: repo root). Returns defaults
    when the file is absent so callers can rely on the returned object."""
    p = Path(path) if path else _DEFAULT_CONFIG_PATH
    if not p.exists():
        return AgentConfig()
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return AgentConfig()
    return AgentConfig.from_dict(data)


_ENV_VAR_BY_PROVIDER = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai":    "OPENAI_API_KEY",
    "google":    "GOOGLE_API_KEY",
    "mistral":   "MISTRAL_API_KEY",
}


def resolve_api_key(
    provider: str,
    config: Optional[AgentConfig] = None,
    env: Optional[dict] = None,
) -> str:
    """Env var first, config file fallback. Raises MissingApiKey if neither set.

    `env` is the environment mapping to consult; defaults to os.environ but
    accepting it as a parameter lets tests exercise the precedence rule
    without touching the real environment.
    """
    provider_lc = provider.lower()
    var_name = _ENV_VAR_BY_PROVIDER.get(provider_lc)
    if var_name is None:
        raise MissingApiKey(f"Unknown provider '{provider}' — no env var mapping")

    env_map = env if env is not None else os.environ
    v = env_map.get(var_name, "")
    if v:
        return v

    cfg = config if config is not None else load_config()
    config_key_name = f"{provider_lc}_api_key"
    if config_key_name in cfg._api_keys:
        return cfg._api_keys[config_key_name]

    raise MissingApiKey(
        f"{provider} API key not found. Set env var {var_name} or add "
        f"'{config_key_name}' to agent_config.json."
    )


def next_summarizer(current: str, config: AgentConfig) -> Optional[str]:
    """Return the next agent in the fallback chain after `current`.

    Used by the failover rule (Q6): when a summarizer dispatch fails, the
    caller advances one position. Returns None when the chain exhausts,
    signaling 'fall back to raw-last-N for this dispatch' per Q8.
    """
    chain = config.summarizer_fallback_chain
    if not chain:
        return None
    try:
        idx = chain.index(current)
    except ValueError:
        # Current agent isn't in the chain — start from the top of the chain.
        return chain[0] if chain else None
    if idx + 1 >= len(chain):
        return None
    return chain[idx + 1]
