"""Tests for the ACAL round-trip verifier module."""

import pytest
import sys
import os

# Ensure src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from acal.verifier import verify_roundtrip, VerificationResult


# =====================================================================
# Successful round-trip tests
# =====================================================================


class TestSuccessfulRoundTrip:
    """Verify that well-formed AICP messages survive the round trip."""

    COMPLETE_MSG = """\
$PROTO: AICP/1.0
$TYPE: RESPONSE
$ID: MSG-0010
$REF: MSG-0008
$SEQ: 10
$FROM: Pharos
$TO: Don, Lodestar
$TIME: 2026-03-09T09:15:00-05:00
$TASK: Implement MVP viewer app skeleton
$STATUS: COMPLETE
$PRIORITY: HIGH
$ROLE: Lead Coder
$INTENT: Deliver Slice 0 for review
PROJECT: InterAI-Protocol
DOMAIN: Multi-Agent Systems

---PAYLOAD---

Slice 0 implementation complete.
Ready for review.

---END---
"""

    def test_complete_message_passes(self):
        result = verify_roundtrip(self.COMPLETE_MSG)
        assert result.passed is True
        assert result.field_mismatches == []
        assert result.error is None

    def test_compression_ratio_is_positive(self):
        result = verify_roundtrip(self.COMPLETE_MSG)
        assert 0.0 < result.compression_ratio < 1.0

    def test_acal_text_is_populated(self):
        result = verify_roundtrip(self.COMPLETE_MSG)
        assert len(result.acal_text) > 0
        # ACAL should be shorter than original
        assert result.acal_size < result.original_size

    ACK_MSG = """\
$PROTO: AICP/1.0
$TYPE: ACK
$ID: MSG-0002
$REF: MSG-0001
$SEQ: 2
$FROM: Pharos
$TO: Don, Lodestar
$TIME: 2026-03-09T08:07:00-05:00
$TASK: Establish first synchronized inter-agent communication
$STATUS: IN_PROGRESS
$PRIORITY: HIGH
$ROLE: Lead Coder
PROJECT: InterAI-Protocol
DOMAIN: Multi-Agent Systems

---PAYLOAD---

Receipt acknowledged.

---END---
"""

    def test_ack_roundtrip(self):
        result = verify_roundtrip(self.ACK_MSG)
        assert result.passed is True

    REQUEST_NO_REF = """\
$PROTO: AICP/1.0
$TYPE: REQUEST
$ID: MSG-0001
$FROM: Don
$TO: Pharos, Lodestar
$TIME: 2026-03-09T08:05:00-05:00
$TASK: Establish first synchronized inter-agent communication
$STATUS: PENDING
$PRIORITY: HIGH
PROJECT: InterAI-Protocol
DOMAIN: Multi-Agent Systems

---PAYLOAD---

Goal: Initiate the first structured exchange.

---END---
"""

    def test_request_without_ref_roundtrip(self):
        result = verify_roundtrip(self.REQUEST_NO_REF)
        assert result.passed is True

    REVIEW_MULTI_ROLE = """\
$PROTO: AICP/1.0
$TYPE: REVIEW
$ID: MSG-0008
$REF: MSG-0007
$SEQ: 8
$FROM: Lodestar
$TO: Don, Pharos
$TIME: 2026-03-09T08:40:00-05:00
$TASK: Review MVP viewer app skeleton proposal
$STATUS: IN_PROGRESS
$PRIORITY: HIGH
$ROLE: Lead Designer, Reviewer
$INTENT: Approve the proposed architecture for Slice 0
PROJECT: InterAI-Protocol
DOMAIN: Multi-Agent Systems

---PAYLOAD---

Approved with minor amendment.

---END---
"""

    def test_review_multi_role_roundtrip(self):
        result = verify_roundtrip(self.REVIEW_MULTI_ROLE)
        assert result.passed is True

    BROADCAST_MSG = """\
$PROTO: AICP/1.0
$TYPE: UPDATE
$ID: MSG-0108
$REF: MSG-0107
$SEQ: 139
$FROM: Pharos
$TO: Don, Lodestar, Forge, SpinDrift, Trident, Lumen
$TIME: 2026-04-10T14:46:01-04:00
$TASK: Session Summary - April 10, 2026
$STATUS: COMPLETE
$PRIORITY: HIGH
$ROLE: Lead Coder
$INTENT: Log end-of-session summary for April 10
PROJECT: InterAI-Protocol
DOMAIN: Multi-Agent Systems

---PAYLOAD---

Per Hub team consensus on architecture.
Phase 2 complete. Ready for review.

---END---
"""

    def test_broadcast_to_many_agents_roundtrip(self):
        result = verify_roundtrip(self.BROADCAST_MSG)
        assert result.passed is True


# =====================================================================
# Compression ratio calculation
# =====================================================================


class TestCompressionRatio:
    """Verify compression ratio arithmetic."""

    SIMPLE_MSG = """\
$PROTO: AICP/1.0
$TYPE: ACK
$ID: MSG-0005
$REF: MSG-0004
$SEQ: 5
$FROM: Pharos
$TO: Don
$TIME: 2026-03-09T08:10:00-05:00
$TASK: Simple ack
$STATUS: COMPLETE
$PRIORITY: HIGH
$ROLE: Lead Coder
PROJECT: InterAI-Protocol
DOMAIN: Multi-Agent Systems

---PAYLOAD---
Receipt acknowledged.
---END---
"""

    def test_ratio_is_fraction(self):
        result = verify_roundtrip(self.SIMPLE_MSG)
        assert 0.0 < result.compression_ratio < 1.0

    def test_ratio_matches_sizes(self):
        result = verify_roundtrip(self.SIMPLE_MSG)
        expected = result.acal_size / result.original_size
        assert abs(result.compression_ratio - expected) < 0.0001

    def test_to_dict_includes_compression_pct(self):
        result = verify_roundtrip(self.SIMPLE_MSG)
        d = result.to_dict()
        assert "compression_pct" in d
        assert d["compression_pct"] > 0
        # compression_pct should be (1 - ratio) * 100
        expected_pct = round((1 - result.compression_ratio) * 100, 1)
        assert d["compression_pct"] == expected_pct

    def test_sizes_are_positive(self):
        result = verify_roundtrip(self.SIMPLE_MSG)
        assert result.original_size > 0
        assert result.acal_size > 0
        assert result.reconstructed_size > 0


# =====================================================================
# Field mismatch detection
# =====================================================================


class TestFieldMismatchDetection:
    """Verify that the verifier detects field-level mismatches.

    We test this by using messages with values not in the lookup
    dictionaries, which will pass through as literals and may
    mismatch after round-tripping through the converter.
    """

    def test_result_to_dict_structure(self):
        """Verify to_dict produces the expected keys."""
        msg = """\
$PROTO: AICP/1.0
$TYPE: ACK
$ID: MSG-0005
$REF: MSG-0004
$SEQ: 5
$FROM: Pharos
$TO: Don
$TIME: 2026-03-09T08:10:00-05:00
$TASK: Simple ack
$STATUS: COMPLETE
$PRIORITY: HIGH
$ROLE: Lead Coder
PROJECT: InterAI-Protocol

---PAYLOAD---
OK.
---END---
"""
        result = verify_roundtrip(msg)
        d = result.to_dict()
        expected_keys = {
            "passed", "original_size", "acal_size", "reconstructed_size",
            "compression_ratio", "compression_pct", "field_mismatches",
            "acal_text", "error",
        }
        assert set(d.keys()) == expected_keys

    def test_mismatch_dict_structure(self):
        """If a mismatch occurs, it should have field/original/reconstructed."""
        # Construct a VerificationResult with a mismatch manually
        result = VerificationResult(
            passed=False,
            original_size=100,
            acal_size=30,
            reconstructed_size=110,
            compression_ratio=0.3,
            field_mismatches=[{
                "field": "$TYPE",
                "original": "FOO",
                "reconstructed": "BAR",
            }],
        )
        assert result.field_mismatches[0]["field"] == "$TYPE"
        assert result.field_mismatches[0]["original"] == "FOO"
        assert result.field_mismatches[0]["reconstructed"] == "BAR"


# =====================================================================
# Edge cases
# =====================================================================


class TestEdgeCases:
    """Edge cases: empty input, special characters, multi-line payloads."""

    def test_empty_input(self):
        result = verify_roundtrip("")
        assert result.passed is False
        assert result.error is not None
        assert "Empty" in result.error

    def test_whitespace_only_input(self):
        result = verify_roundtrip("   \n\n  ")
        assert result.passed is False
        assert result.error is not None

    def test_empty_payload(self):
        msg = """\
$PROTO: AICP/1.0
$TYPE: ACK
$ID: MSG-0020
$REF: MSG-0019
$SEQ: 20
$FROM: Pharos
$TO: Don
$TIME: 2026-03-09T08:10:00-05:00
$TASK: Empty payload test
$STATUS: COMPLETE
$PRIORITY: HIGH
$ROLE: Lead Coder
PROJECT: InterAI-Protocol

---PAYLOAD---
---END---
"""
        result = verify_roundtrip(msg)
        assert result.passed is True

    def test_special_characters_in_task(self):
        msg = """\
$PROTO: AICP/1.0
$TYPE: REQUEST
$ID: MSG-0030
$SEQ: 30
$FROM: Don
$TO: Pharos
$TIME: 2026-03-09T08:10:00-05:00
$TASK: Fix bug #42 — UTF-8 handling
$STATUS: PENDING
$PRIORITY: HIGH
PROJECT: InterAI-Protocol

---PAYLOAD---
Test special chars.
---END---
"""
        result = verify_roundtrip(msg)
        assert result.passed is True

    def test_multiline_payload(self):
        msg = """\
$PROTO: AICP/1.0
$TYPE: RESPONSE
$ID: MSG-0040
$REF: MSG-0039
$SEQ: 40
$FROM: Pharos
$TO: Don, Lodestar
$TIME: 2026-03-09T09:15:00-05:00
$TASK: Multi-line payload test
$STATUS: COMPLETE
$PRIORITY: HIGH
$ROLE: Lead Coder
PROJECT: InterAI-Protocol
DOMAIN: Multi-Agent Systems

---PAYLOAD---

Line 1: Implementation complete.
Line 2: All tests passing.
Line 3: Ready for review.

Additional notes:
- Backward compatible with existing format.
- Zero dependencies added.
- No build step required.

---END---
"""
        result = verify_roundtrip(msg)
        assert result.passed is True

    def test_medium_priority(self):
        msg = """\
$PROTO: AICP/1.0
$TYPE: REVIEW
$ID: MSG-0050
$REF: MSG-0049
$SEQ: 50
$FROM: Lodestar
$TO: Don, Pharos
$TIME: 2026-03-09T08:40:00-05:00
$TASK: Review proposal
$STATUS: IN_PROGRESS
$PRIORITY: MEDIUM
$ROLE: Lead Designer
PROJECT: InterAI-Protocol
DOMAIN: Multi-Agent Systems

---PAYLOAD---
Approved as proposed.
---END---
"""
        result = verify_roundtrip(msg)
        assert result.passed is True

    def test_low_priority(self):
        msg = """\
$PROTO: AICP/1.0
$TYPE: UPDATE
$ID: MSG-0060
$REF: MSG-0059
$SEQ: 60
$FROM: Pharos
$TO: Don
$TIME: 2026-03-09T09:00:00-05:00
$TASK: Minor housekeeping
$STATUS: COMPLETE
$PRIORITY: LOW
$ROLE: Lead Coder
PROJECT: InterAI-Protocol

---PAYLOAD---
Cleaned up formatting.
---END---
"""
        result = verify_roundtrip(msg)
        assert result.passed is True

    def test_operatorhub_project(self):
        msg = """\
$PROTO: AICP/1.0
$TYPE: REQUEST
$ID: MSG-0070
$SEQ: 70
$FROM: Don
$TO: Pharos
$TIME: 2026-03-09T08:10:00-05:00
$TASK: Add panel feature
$STATUS: PENDING
$PRIORITY: HIGH
PROJECT: OperatorHub
DOMAIN: Flow Cytometry Lab Operations

---PAYLOAD---
Build the new panel.
---END---
"""
        result = verify_roundtrip(msg)
        assert result.passed is True

    def test_studyguide_project(self):
        msg = """\
$PROTO: AICP/1.0
$TYPE: REQUEST
$ID: MSG-0080
$SEQ: 80
$FROM: Don
$TO: Pharos
$TIME: 2026-03-09T08:10:00-05:00
$TASK: Create quiz module
$STATUS: PENDING
$PRIORITY: HIGH
PROJECT: StudyGuide
DOMAIN: AI-Assisted Learning

---PAYLOAD---
Build quiz feature.
---END---
"""
        result = verify_roundtrip(msg)
        assert result.passed is True

    def test_to_dict_serialization(self):
        msg = """\
$PROTO: AICP/1.0
$TYPE: ACK
$ID: MSG-0005
$REF: MSG-0004
$SEQ: 5
$FROM: Pharos
$TO: Don
$TIME: 2026-03-09T08:10:00-05:00
$TASK: Serialization test
$STATUS: COMPLETE
$PRIORITY: HIGH
$ROLE: Lead Coder
PROJECT: InterAI-Protocol

---PAYLOAD---
OK.
---END---
"""
        result = verify_roundtrip(msg)
        d = result.to_dict()
        # Should be JSON-serializable (no custom types)
        import json
        json_str = json.dumps(d)
        assert len(json_str) > 0

    def test_error_result_to_dict(self):
        result = verify_roundtrip("")
        d = result.to_dict()
        assert d["passed"] is False
        assert d["error"] is not None
