"""
AICP Phase 2 — Rate Limiter Middleware

Prevents HTTP 429/529 errors by pacing API calls to providers.
Implements per-provider delay tracking and configurable cooldowns.
"""

import time
import logging
from collections import defaultdict

logger = logging.getLogger("aicp.rate_limiter")


class ProviderRateLimiter:
    """
    Tracks per-provider call timing and enforces minimum delays
    between sequential API calls to the same provider.

    Usage:
        limiter = ProviderRateLimiter(default_delay=3.0)
        limiter.wait_if_needed("openai")   # blocks if called too soon
        # ... make API call ...
        limiter.record_call("openai", tokens_used=1500)
    """

    def __init__(self, default_delay: float = 3.0, provider_delays: dict = None):
        """
        Args:
            default_delay: Seconds between calls to the same provider.
            provider_delays: Optional per-provider overrides.
                             e.g. {"openai": 3.0, "anthropic": 2.0, "google": 4.0}
        """
        self.default_delay = default_delay
        self.provider_delays = provider_delays or {
            "anthropic": 2.0,
            "openai": 3.0,
            "google": 4.0,     # Gemini has tighter rate limits
            "mistral": 2.0,
        }
        self._last_call: dict[str, float] = defaultdict(float)
        self._call_counts: dict[str, int] = defaultdict(int)
        self._token_counts: dict[str, int] = defaultdict(int)
        self._window_start: float = time.time()
        self._window_seconds: float = 60.0  # 1-minute rolling window

    def get_delay(self, provider: str) -> float:
        """Get the configured delay for a provider."""
        return self.provider_delays.get(provider.lower(), self.default_delay)

    def wait_if_needed(self, provider: str) -> float:
        """
        Block until it's safe to call the provider.
        Returns the number of seconds waited (0.0 if no wait needed).
        """
        provider_key = provider.lower()
        delay = self.get_delay(provider_key)
        last = self._last_call[provider_key]

        if last == 0:
            return 0.0

        elapsed = time.time() - last
        if elapsed < delay:
            wait_time = delay - elapsed
            logger.info(f"Rate limiter: waiting {wait_time:.1f}s before calling {provider}")
            time.sleep(wait_time)
            return wait_time

        return 0.0

    def record_call(self, provider: str, tokens_used: int = 0):
        """Record that a call was made to a provider."""
        provider_key = provider.lower()
        self._last_call[provider_key] = time.time()
        self._call_counts[provider_key] += 1
        self._token_counts[provider_key] += tokens_used

        # Reset window if expired
        now = time.time()
        if now - self._window_start > self._window_seconds:
            self._reset_window()

    def get_stats(self, provider: str = None) -> dict:
        """Get rate limiting stats, optionally for a specific provider."""
        self._maybe_reset_window()

        if provider:
            pk = provider.lower()
            return {
                "provider": provider,
                "calls_this_window": self._call_counts[pk],
                "tokens_this_window": self._token_counts[pk],
                "last_call_ago_seconds": round(time.time() - self._last_call[pk], 1)
                    if self._last_call[pk] else None,
                "configured_delay": self.get_delay(pk),
            }

        return {
            "window_seconds": self._window_seconds,
            "providers": {
                pk: {
                    "calls": self._call_counts[pk],
                    "tokens": self._token_counts[pk],
                    "configured_delay": self.get_delay(pk),
                }
                for pk in set(list(self._call_counts.keys()) + list(self._token_counts.keys()))
            },
        }

    def _maybe_reset_window(self):
        if time.time() - self._window_start > self._window_seconds:
            self._reset_window()

    def _reset_window(self):
        self._call_counts.clear()
        self._token_counts.clear()
        self._window_start = time.time()
