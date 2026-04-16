"""
Slice 8.6 — $DECISION Header Validation Middleware

Enforces mandatory $DECISION header on all RESPONSE messages.
Valid values: CHALLENGE, CLARIFY, EXECUTE

Scope: Only fires on $TYPE: RESPONSE messages.
Non-RESPONSE messages pass through without validation.

Error codes:
  - DECISION_REQUIRED: $DECISION header missing on a RESPONSE
  - INVALID_DECISION_STATE: $DECISION value not in allowed set
"""

from typing import Optional

# Allowed $DECISION values
VALID_DECISIONS = {"CHALLENGE", "CLARIFY", "EXECUTE"}


class DecisionValidationError:
    """Represents a validation failure for $DECISION enforcement."""

    def __init__(self, code: str, message_id: str, detail: str = ""):
        self.code = code
        self.message_id = message_id
        self.detail = detail

    def to_dict(self) -> dict:
        return {
            "error": self.code,
            "message_id": self.message_id,
            "detail": self.detail,
        }


def validate_decision(message: dict) -> Optional[DecisionValidationError]:
    """
    Validates the $DECISION header on a message.

    Only enforces on $TYPE: RESPONSE messages.
    Returns None if valid (or not a RESPONSE), or a DecisionValidationError if invalid.

    Args:
        message: Dict with at minimum 'type' and optionally 'decision' keys.
                 Can also use envelope-style keys like '$TYPE', '$DECISION'.

    Returns:
        None if valid, DecisionValidationError if invalid.
    """
    # Normalize field access — support both flat and envelope-style keys
    msg_type = (
        message.get("type", "")
        or message.get("$TYPE", "")
        or ""
    ).upper().strip()

    # Only enforce on RESPONSE messages
    if msg_type != "RESPONSE":
        return None

    msg_id = (
        message.get("id", "")
        or message.get("$ID", "")
        or "UNKNOWN"
    )

    # Extract $DECISION value
    decision = (
        message.get("decision", "")
        or message.get("$DECISION", "")
        or ""
    ).upper().strip()

    # Missing check
    if not decision:
        return DecisionValidationError(
            code="DECISION_REQUIRED",
            message_id=msg_id,
            detail="RESPONSE messages must include a $DECISION header. "
                   f"Allowed values: {', '.join(sorted(VALID_DECISIONS))}",
        )

    # Invalid value check
    if decision not in VALID_DECISIONS:
        return DecisionValidationError(
            code="INVALID_DECISION_STATE",
            message_id=msg_id,
            detail=f"$DECISION value '{decision}' is not valid. "
                   f"Allowed: {', '.join(sorted(VALID_DECISIONS))}",
        )

    return None


def extract_decision_from_content(content: str) -> Optional[str]:
    """
    Extracts $DECISION value from message content text.

    Scans for a line matching '$DECISION: VALUE' pattern.
    Used when $DECISION is embedded in payload rather than headers.

    Args:
        content: Raw message content string.

    Returns:
        The decision value string if found, None otherwise.
    """
    if not content:
        return None

    for line in content.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith("$DECISION:"):
            value = stripped.split(":", 1)[1].strip().upper()
            # Strip any trailing commentary (e.g., "$DECISION: EXECUTE (awaiting hourglass)")
            if " " in value:
                value = value.split()[0]
            # Remove parenthetical
            if "(" in value:
                value = value.split("(")[0].strip()
            return value if value else None

    return None
