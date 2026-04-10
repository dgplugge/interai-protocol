"""
AICP Phase 2 — Token Estimator

Estimates token counts before dispatch to help monitor and
prevent rate limit breaches. Uses a simple heuristic (4 chars
per token) since we don't want to add tiktoken as a dependency.
"""

import logging
from typing import Optional

logger = logging.getLogger("aicp.tokens")

# Average characters per token by provider/model family
# These are rough estimates — good enough for rate limit planning
CHARS_PER_TOKEN = {
    "anthropic": 3.8,   # Claude models
    "openai": 4.0,      # GPT-4 family
    "google": 4.0,      # Gemini family
    "mistral": 3.9,     # Mistral models
}

DEFAULT_CHARS_PER_TOKEN = 4.0


def estimate_tokens(text: str, provider: str = None) -> int:
    """
    Estimate the number of tokens in a text string.

    Args:
        text: The text to estimate tokens for.
        provider: Optional provider name for more accurate estimate.

    Returns:
        Estimated token count.
    """
    if not text:
        return 0

    chars_per_token = CHARS_PER_TOKEN.get(
        provider.lower() if provider else "", DEFAULT_CHARS_PER_TOKEN
    )
    return max(1, int(len(text) / chars_per_token))


def estimate_dispatch_tokens(
    system_prompt: str = "",
    conversation_history: list[str] = None,
    current_prompt: str = "",
    provider: str = None,
) -> dict:
    """
    Estimate total tokens for a dispatch request.

    Args:
        system_prompt: The system prompt text.
        conversation_history: List of prior message strings.
        current_prompt: The current message being sent.
        provider: Provider name for estimation tuning.

    Returns:
        Dict with breakdown and total estimate.
    """
    history = conversation_history or []

    system_tokens = estimate_tokens(system_prompt, provider)
    history_tokens = sum(estimate_tokens(msg, provider) for msg in history)
    prompt_tokens = estimate_tokens(current_prompt, provider)
    total = system_tokens + history_tokens + prompt_tokens

    result = {
        "system_prompt_tokens": system_tokens,
        "history_tokens": history_tokens,
        "history_message_count": len(history),
        "current_prompt_tokens": prompt_tokens,
        "estimated_total_input": total,
        "provider": provider or "default",
    }

    # Warn if approaching common limits
    if total > 20000:
        logger.warning(
            f"[{provider or 'unknown'}] High token estimate: {total}. "
            f"Consider trimming conversation history."
        )
        result["warning"] = "High token count — consider trimming history"
    elif total > 10000:
        logger.info(
            f"[{provider or 'unknown'}] Moderate token estimate: {total}."
        )

    return result


def suggest_history_trim(
    conversation_history: list[str],
    max_tokens: int = 8000,
    provider: str = None,
    keep_recent: int = 5,
) -> dict:
    """
    Suggest how to trim conversation history to stay under a token budget.

    Args:
        conversation_history: Full list of message strings.
        max_tokens: Target token budget for history.
        provider: Provider for estimation.
        keep_recent: Minimum number of recent messages to always keep.

    Returns:
        Dict with trim recommendation.
    """
    if not conversation_history:
        return {"action": "none", "reason": "No history to trim"}

    total = sum(estimate_tokens(msg, provider) for msg in conversation_history)

    if total <= max_tokens:
        return {
            "action": "none",
            "reason": f"History ({total} tokens) is within budget ({max_tokens})",
            "current_tokens": total,
            "message_count": len(conversation_history),
        }

    # Calculate how many messages to keep
    kept_tokens = 0
    keep_count = 0
    for msg in reversed(conversation_history):
        msg_tokens = estimate_tokens(msg, provider)
        if kept_tokens + msg_tokens > max_tokens and keep_count >= keep_recent:
            break
        kept_tokens += msg_tokens
        keep_count += 1

    drop_count = len(conversation_history) - keep_count

    return {
        "action": "trim",
        "current_tokens": total,
        "target_tokens": max_tokens,
        "total_messages": len(conversation_history),
        "keep_messages": keep_count,
        "drop_messages": drop_count,
        "estimated_tokens_after_trim": kept_tokens,
        "recommendation": f"Drop oldest {drop_count} messages, keep most recent {keep_count}",
    }
