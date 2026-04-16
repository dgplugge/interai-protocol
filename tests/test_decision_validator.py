"""
Tests for Slice 8.6 — $DECISION Header Validation Middleware
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from middleware.decision_validator import (
    validate_decision,
    extract_decision_from_content,
    VALID_DECISIONS,
    DecisionValidationError,
)


# --- validate_decision tests ---


class TestPassThrough:
    """Non-RESPONSE messages should pass through without validation."""

    def test_request_bypasses(self):
        msg = {"type": "REQUEST", "id": "MSG-001"}
        assert validate_decision(msg) is None

    def test_proposal_bypasses(self):
        msg = {"type": "PROPOSAL", "id": "MSG-002"}
        assert validate_decision(msg) is None

    def test_ack_bypasses(self):
        msg = {"type": "ACK", "id": "MSG-003"}
        assert validate_decision(msg) is None

    def test_notice_bypasses(self):
        msg = {"type": "NOTICE", "id": "MSG-004"}
        assert validate_decision(msg) is None

    def test_update_bypasses(self):
        msg = {"type": "UPDATE", "id": "MSG-005"}
        assert validate_decision(msg) is None

    def test_empty_type_bypasses(self):
        msg = {"type": "", "id": "MSG-006"}
        assert validate_decision(msg) is None

    def test_missing_type_bypasses(self):
        msg = {"id": "MSG-007"}
        assert validate_decision(msg) is None


class TestValidResponses:
    """RESPONSE messages with valid $DECISION should pass."""

    def test_execute(self):
        msg = {"type": "RESPONSE", "id": "MSG-010", "decision": "EXECUTE"}
        assert validate_decision(msg) is None

    def test_challenge(self):
        msg = {"type": "RESPONSE", "id": "MSG-011", "decision": "CHALLENGE"}
        assert validate_decision(msg) is None

    def test_clarify(self):
        msg = {"type": "RESPONSE", "id": "MSG-012", "decision": "CLARIFY"}
        assert validate_decision(msg) is None

    def test_lowercase_decision(self):
        msg = {"type": "RESPONSE", "id": "MSG-013", "decision": "execute"}
        assert validate_decision(msg) is None

    def test_mixed_case(self):
        msg = {"type": "RESPONSE", "id": "MSG-014", "decision": "Challenge"}
        assert validate_decision(msg) is None

    def test_envelope_style_keys(self):
        msg = {"$TYPE": "RESPONSE", "$ID": "MSG-015", "$DECISION": "EXECUTE"}
        assert validate_decision(msg) is None

    def test_lowercase_type(self):
        msg = {"type": "response", "id": "MSG-016", "decision": "CLARIFY"}
        assert validate_decision(msg) is None


class TestMissingDecision:
    """RESPONSE messages without $DECISION should fail."""

    def test_missing_decision(self):
        msg = {"type": "RESPONSE", "id": "MSG-020"}
        result = validate_decision(msg)
        assert result is not None
        assert result.code == "DECISION_REQUIRED"
        assert result.message_id == "MSG-020"

    def test_empty_decision(self):
        msg = {"type": "RESPONSE", "id": "MSG-021", "decision": ""}
        result = validate_decision(msg)
        assert result is not None
        assert result.code == "DECISION_REQUIRED"

    def test_whitespace_decision(self):
        msg = {"type": "RESPONSE", "id": "MSG-022", "decision": "   "}
        result = validate_decision(msg)
        assert result is not None
        assert result.code == "DECISION_REQUIRED"

    def test_none_decision(self):
        msg = {"type": "RESPONSE", "id": "MSG-023", "decision": None}
        result = validate_decision(msg)
        assert result is not None
        assert result.code == "DECISION_REQUIRED"


class TestInvalidDecision:
    """RESPONSE messages with invalid $DECISION values should fail."""

    def test_invalid_value(self):
        msg = {"type": "RESPONSE", "id": "MSG-030", "decision": "APPROVE"}
        result = validate_decision(msg)
        assert result is not None
        assert result.code == "INVALID_DECISION_STATE"

    def test_typo(self):
        msg = {"type": "RESPONSE", "id": "MSG-031", "decision": "CHALLANGE"}
        result = validate_decision(msg)
        assert result is not None
        assert result.code == "INVALID_DECISION_STATE"

    def test_random_text(self):
        msg = {"type": "RESPONSE", "id": "MSG-032", "decision": "YES"}
        result = validate_decision(msg)
        assert result is not None
        assert result.code == "INVALID_DECISION_STATE"


class TestErrorSerialization:
    """DecisionValidationError should serialize to dict."""

    def test_to_dict(self):
        err = DecisionValidationError("DECISION_REQUIRED", "MSG-040", "missing")
        d = err.to_dict()
        assert d["error"] == "DECISION_REQUIRED"
        assert d["message_id"] == "MSG-040"
        assert d["detail"] == "missing"


# --- extract_decision_from_content tests ---


class TestExtractDecision:
    """Extract $DECISION from message content text."""

    def test_simple_extract(self):
        content = "Some response text.\n\n$DECISION: EXECUTE"
        assert extract_decision_from_content(content) == "EXECUTE"

    def test_with_commentary(self):
        content = "$DECISION: CLARIFY (awaiting hourglass)"
        assert extract_decision_from_content(content) == "CLARIFY"

    def test_lowercase(self):
        content = "$decision: challenge"
        assert extract_decision_from_content(content) == "CHALLENGE"

    def test_embedded_in_payload(self):
        content = """Here is my analysis.

I propose we proceed.

$DECISION: EXECUTE

Thank you."""
        assert extract_decision_from_content(content) == "EXECUTE"

    def test_no_decision(self):
        content = "Just a regular message with no decision header."
        assert extract_decision_from_content(content) is None

    def test_empty_content(self):
        assert extract_decision_from_content("") is None

    def test_none_content(self):
        assert extract_decision_from_content(None) is None

    def test_decision_with_extra_spaces(self):
        content = "$DECISION:    EXECUTE   "
        assert extract_decision_from_content(content) == "EXECUTE"
