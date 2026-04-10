"""
AICP Phase 2 — Retry Handler

Exponential backoff retry logic for transient API errors:
- HTTP 429 (Rate Limited) — OpenAI, Mistral
- HTTP 529 (Overloaded) — Anthropic
- HTTP 503 (Service Unavailable) — Google/Gemini
"""

import time
import logging
from typing import Callable, Any, Optional

logger = logging.getLogger("aicp.retry")

# Status codes that should trigger a retry
RETRYABLE_STATUS_CODES = {429, 503, 529}


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 5.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
    ):
        """
        Args:
            max_retries: Maximum number of retry attempts.
            base_delay: Initial delay in seconds before first retry.
            max_delay: Maximum delay cap in seconds.
            backoff_factor: Multiplier for each subsequent retry.

        Delay pattern with defaults: 5s -> 10s -> 20s (then give up)
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor


# Default configs per provider
PROVIDER_RETRY_CONFIGS = {
    "anthropic": RetryConfig(max_retries=3, base_delay=5.0),
    "openai":    RetryConfig(max_retries=3, base_delay=5.0),
    "google":    RetryConfig(max_retries=3, base_delay=8.0),   # Gemini tends to have longer outages
    "mistral":   RetryConfig(max_retries=2, base_delay=3.0),
}


class RetryResult:
    """Result of a retryable operation."""

    def __init__(self, success: bool, result: Any = None, error: str = None,
                 attempts: int = 0, total_wait: float = 0.0, status_code: int = None):
        self.success = success
        self.result = result
        self.error = error
        self.attempts = attempts
        self.total_wait = total_wait
        self.status_code = status_code

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "attempts": self.attempts,
            "total_wait_seconds": round(self.total_wait, 1),
            "error": self.error,
            "status_code": self.status_code,
        }


def retry_with_backoff(
    func: Callable,
    provider: str,
    config: RetryConfig = None,
    on_retry: Optional[Callable] = None,
) -> RetryResult:
    """
    Execute a function with exponential backoff on retryable errors.

    Args:
        func: Callable that returns (status_code, result) or raises an exception.
              The function should return a tuple of (http_status_code, response_data).
        provider: Provider name for config lookup and logging.
        config: Optional RetryConfig override.
        on_retry: Optional callback(attempt, delay, error) called before each retry.

    Returns:
        RetryResult with success status, result data, and retry metadata.
    """
    if config is None:
        config = PROVIDER_RETRY_CONFIGS.get(provider.lower(), RetryConfig())

    total_wait = 0.0

    for attempt in range(1, config.max_retries + 2):  # +2 because first attempt isn't a retry
        try:
            status_code, result = func()

            if status_code is not None and status_code in RETRYABLE_STATUS_CODES:
                if attempt > config.max_retries:
                    logger.warning(
                        f"[{provider}] Max retries ({config.max_retries}) exhausted. "
                        f"Last status: {status_code}"
                    )
                    return RetryResult(
                        success=False,
                        error=f"Max retries exhausted after {attempt} attempts. Last HTTP {status_code}",
                        attempts=attempt,
                        total_wait=total_wait,
                        status_code=status_code,
                    )

                delay = min(
                    config.base_delay * (config.backoff_factor ** (attempt - 1)),
                    config.max_delay,
                )

                # Check for Retry-After header hint in result
                if isinstance(result, dict) and "retry_after" in result:
                    delay = max(delay, float(result["retry_after"]))

                logger.info(
                    f"[{provider}] HTTP {status_code} on attempt {attempt}. "
                    f"Retrying in {delay:.1f}s..."
                )

                if on_retry:
                    on_retry(attempt, delay, f"HTTP {status_code}")

                time.sleep(delay)
                total_wait += delay
                continue

            # Success or non-retryable status
            return RetryResult(
                success=True,
                result=result,
                attempts=attempt,
                total_wait=total_wait,
                status_code=status_code,
            )

        except Exception as e:
            error_msg = str(e)
            if attempt > config.max_retries:
                logger.error(
                    f"[{provider}] Exception on attempt {attempt}, no retries left: {error_msg}"
                )
                return RetryResult(
                    success=False,
                    error=f"Exception after {attempt} attempts: {error_msg}",
                    attempts=attempt,
                    total_wait=total_wait,
                )

            delay = min(
                config.base_delay * (config.backoff_factor ** (attempt - 1)),
                config.max_delay,
            )
            logger.info(
                f"[{provider}] Exception on attempt {attempt}: {error_msg}. "
                f"Retrying in {delay:.1f}s..."
            )

            if on_retry:
                on_retry(attempt, delay, error_msg)

            time.sleep(delay)
            total_wait += delay

    # Should never reach here, but just in case
    return RetryResult(success=False, error="Unexpected retry loop exit", attempts=0)
