"""Comprehensive tests for the ACAL converter module."""

import pytest
import sys
import os

# Ensure src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from acal.converter import (
    parse_acal,
    acal_to_aicp,
    aicp_to_acal,
    parse_operations,
    validate_roundtrip,
    MSG_TYPES,
    AGENTS,
    STATUS,
    PRIORITY,
    ROLES,
    PROJECTS,
    DOMAINS,
    ACTIONS,
    LAYERS,
    PHRASES,
    MSG_TYPES_REV,
    AGENTS_REV,
    STATUS_REV,
    PRIORITY_REV,
    ROLES_REV,
    PROJECTS_REV,
    PHRASES_REV,
)


# =====================================================================
# Reverse dictionary tests
# =====================================================================


class TestReverseDicts:
    """Verify that reverse-lookup dicts are correctly auto-generated."""

    def test_msg_types_reverse(self):
        assert MSG_TYPES_REV["REQUEST"] == "RQ"
        assert MSG_TYPES_REV["ACK"] == "AK"
        assert MSG_TYPES_REV["REVIEW"] == "RV"

    def test_agents_reverse(self):
        assert AGENTS_REV["Don"] == "D"
        assert AGENTS_REV["Pharos"] == "P"
        assert AGENTS_REV["Lodestar"] == "L"
        assert AGENTS_REV["ALL"] == "*"

    def test_status_reverse_includes_hyphen_variant(self):
        assert STATUS_REV["IN_PROGRESS"] == "W"
        assert STATUS_REV["IN-PROGRESS"] == "W"

    def test_phrases_reverse(self):
        assert PHRASES_REV["Receipt acknowledged"] == "ACK"
        assert PHRASES_REV["Approved as proposed"] == "APR"
        assert PHRASES_REV["Ready for review"] == "RFR"


# =====================================================================
# Parse operations tests
# =====================================================================


class TestParseOperations:
    """Tests for the payload operation parser."""

    def test_single_operation(self):
        ops = parse_operations("+IF IAgentConfig {read,display,verify}")
        assert len(ops) == 1
        assert ops[0]["action"] == "+"
        assert ops[0]["layer"] == "IF"
        assert ops[0]["target"] == "IAgentConfig"
        assert ops[0]["params"] == "read,display,verify"

    def test_multiple_operations_semicolon(self):
        payload = "+IF IAgentConfig; +M AgentConfigModel; ~PR AgentHubPresenter"
        ops = parse_operations(payload)
        assert len(ops) == 3
        assert ops[0]["layer"] == "IF"
        assert ops[1]["layer"] == "M"
        assert ops[2]["action"] == "~"
        assert ops[2]["layer"] == "PR"

    def test_multiple_operations_newline(self):
        payload = "+V frmSettings.vb\n~PR AgentHubPresenter\n#TS BackfillTest.vb"
        ops = parse_operations(payload)
        assert len(ops) == 3
        assert ops[0]["action"] == "+"
        assert ops[0]["layer"] == "V"
        assert ops[1]["action"] == "~"
        assert ops[2]["action"] == "#"

    def test_no_params(self):
        ops = parse_operations("@PX parser.js")
        assert len(ops) == 1
        assert ops[0]["params"] == ""

    def test_mixed_content_extracts_operations(self):
        payload = (
            "+IF ACAL v0.1\n"
            "Some natural language text here\n"
            "?SV server.py\n"
            "More text"
        )
        ops = parse_operations(payload)
        # Should find +IF and ?SV
        assert len(ops) == 2

    def test_deploy_action(self):
        ops = parse_operations(">WH /api/relay")
        assert len(ops) == 1
        assert ops[0]["action"] == ">"
        assert ops[0]["layer"] == "WH"


# =====================================================================
# ACAL Parser tests
# =====================================================================


class TestParseAcal:
    """Tests for the ACAL header parser."""

    def test_full_header(self):
        acal = "RQ:100>99|D>P|Q!|OR|IP|Add agent config|Enable config mgmt"
        result = parse_acal(acal)
        assert result["type"] == "RQ"
        assert result["id"] == "100"
        assert result["ref"] == "99"
        assert result["from_agent"] == "D"
        assert result["to_agents"] == ["P"]
        assert result["status"] == "Q"
        assert result["priority"] == "!"
        assert result["role"] == ["OR"]
        assert result["project"] == "IP"
        assert result["task"] == "Add agent config"
        assert result["intent"] == "Enable config mgmt"

    def test_no_ref(self):
        acal = "AK:93|P>D,L|W!|LC|IP|ACK Phase 1"
        result = parse_acal(acal)
        assert result["ref"] == ""
        assert result["id"] == "93"

    def test_broadcast_to_all(self):
        acal = "RQ:50|D>*|Q!|OR|IP|Broadcast task"
        result = parse_acal(acal)
        assert result["to_agents"] == ["*"]

    def test_multiple_to_agents(self):
        acal = "RS:10>8|P>D,L,F,S,T|C!|LC|IP|SLC 0|Deliver"
        result = parse_acal(acal)
        assert result["to_agents"] == ["D", "L", "F", "S", "T"]

    def test_multiple_roles(self):
        acal = "RV:11>10|L>D,P|C.|LD,RV|IP|Review|APR"
        result = parse_acal(acal)
        assert result["role"] == ["LD", "RV"]

    def test_medium_priority(self):
        acal = "RV:11>10|L>D,P|C.|LD|IP|Review"
        result = parse_acal(acal)
        assert result["priority"] == "."

    def test_low_priority(self):
        acal = "UP:50|P>D|W_|LC|IP|Minor update"
        result = parse_acal(acal)
        assert result["priority"] == "_"

    def test_default_high_priority(self):
        """When no explicit priority char, default is HIGH (!)."""
        acal = "AK:5|P>D|C|LC|IP|Done"
        result = parse_acal(acal)
        # Status is C, no priority char follows
        assert result["status"] == "C"
        assert result["priority"] == "!"  # default

    def test_with_payload(self):
        acal = (
            "RQ:100|D>P|Q!|OR|IP|Add IF|Config mgmt\n"
            "---\n"
            "+IF IAgentConfig {read,display,verify}\n"
            "+M AgentConfigModel {name,provider}\n"
            "---"
        )
        result = parse_acal(acal)
        assert len(result["operations"]) == 2
        assert result["raw_payload"] != ""

    def test_malformed_header_too_few_fields(self):
        with pytest.raises(ValueError, match="at least 5"):
            parse_acal("RQ:100|D>P|Q!")

    def test_malformed_type_id(self):
        with pytest.raises(ValueError, match="TYPE:ID"):
            parse_acal("BADFORMAT|D>P|Q!|OR|IP")


# =====================================================================
# Verification Probe from MSG-0110
# =====================================================================


class TestVerificationProbe:
    """Parse the verification probe from MSG-0110 and expand it."""

    PROBE = (
        "RV:110|L>P,D|Q.|LD,RV|IP|?IF ACAL spec|Design review of compression language\n"
        "---\n"
        "?IF ACAL v0.1 codebook: grammar, tokens, layer codes\n"
        "SCR: deterministic parse, no ambiguity, BC with AICP\n"
        "APR or APR+ expected. RFR.\n"
        "---"
    )

    def test_parse_probe(self):
        result = parse_acal(self.PROBE)
        assert result["type"] == "RV"
        assert result["id"] == "110"
        assert result["ref"] == ""  # no REF in this probe
        assert result["from_agent"] == "L"
        assert result["to_agents"] == ["P", "D"]
        assert result["status"] == "Q"
        assert result["priority"] == "."
        assert result["role"] == ["LD", "RV"]
        assert result["project"] == "IP"
        assert result["task"] == "?IF ACAL spec"
        assert result["intent"] == "Design review of compression language"

    def test_expand_probe_to_aicp(self):
        aicp = acal_to_aicp(
            self.PROBE,
            seq=141,
            timestamp="2026-04-14T10:15:00-04:00",
        )
        assert "$PROTO: AICP/1.0" in aicp
        assert "$TYPE: REVIEW" in aicp
        assert "$ID: MSG-0110" in aicp
        assert "$FROM: Lodestar" in aicp
        assert "Pharos" in aicp and "Don" in aicp
        assert "$STATUS: PENDING" in aicp
        assert "$PRIORITY: MEDIUM" in aicp
        assert "$ROLE: Lead Designer, Reviewer" in aicp
        assert "PROJECT: InterAI-Protocol" in aicp
        assert "DOMAIN: Multi-Agent Systems" in aicp
        assert "---PAYLOAD---" in aicp
        assert "---END---" in aicp

    def test_probe_payload_tokens_expanded(self):
        aicp = acal_to_aicp(self.PROBE, seq=141, timestamp="2026-04-14T10:15:00-04:00")
        # SCR should expand
        assert "Success criteria" in aicp
        # BC should expand
        assert "Backward compatible" in aicp
        # RFR should expand
        assert "Ready for review" in aicp


# =====================================================================
# AICP -> ACAL Compression
# =====================================================================


class TestAicpToAcal:
    """Test compressing real AICP messages to ACAL."""

    MSG_0001_AICP = """\
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

Goal:
Initiate the first structured exchange where both AI agents
respond using the shared Inter-AI Protocol format.

Instructions:
1. Acknowledge receipt.
2. Confirm understanding of protocol structure.
3. State your current role for this project.
4. Propose one improvement to the protocol.
5. Await further instruction.

Context:
We are using a shared journal until live agent communication exists.
Avoid overlapping edits. Follow role clarity rules.

---END---
"""

    def test_compress_msg_0001(self):
        acal = aicp_to_acal(self.MSG_0001_AICP)
        # Header should contain type, id, agents, status, project
        assert acal.startswith("RQ:1|D>P,L|Q!")
        assert "|IP|" in acal
        # Should have payload section
        assert "---" in acal

    MSG_0010_AICP = """\
$PROTO: AICP/1.0
$TYPE: RESPONSE
$ID: MSG-0010
$REF: MSG-0008
$SEQ: 10
$FROM: Pharos
$TO: Don, Lodestar
$TIME: 2026-03-09T09:15:00-05:00
$TASK: Implement MVP viewer app skeleton — Slice 0
$STATUS: COMPLETE
$PRIORITY: HIGH
$ROLE: Lead Coder
$INTENT: Deliver Slice 0 for review
PROJECT: InterAI-Protocol
DOMAIN: Multi-Agent Systems

---PAYLOAD---

1. SLICE 0 IMPLEMENTATION: COMPLETE.
2. READY FOR REVIEW.

---END---
"""

    def test_compress_msg_0010(self):
        acal = aicp_to_acal(self.MSG_0010_AICP)
        assert acal.startswith("RS:10>8|P>D,L|C!")
        assert "|LC|" in acal
        assert "|IP|" in acal
        # Payload should compress known phrases
        assert "SLC:0" in acal
        assert "RFR" in acal

    MSG_0008_REVIEW = """\
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
$INTENT: Approve the proposed architecture for Slice 0 while clarifying the next MVP step
PROJECT: InterAI-Protocol
DOMAIN: Multi-Agent Systems

---PAYLOAD---

1. ARCHITECTURE REVIEW RESULT:
   APPROVED WITH MINOR AMENDMENT.

2. IMPLEMENTATION AUTHORITY:
   Pharos remains Lead Coder for Slice 0.
   Lodestar remains Reviewer.
   No overlapping edits.

---END---

$SUMMARY: Lodestar approved the local web app viewer architecture.
"""

    def test_compress_msg_0008_review(self):
        acal = aicp_to_acal(self.MSG_0008_REVIEW)
        assert acal.startswith("RV:8>7|L>D,P|W!")
        assert "|LD,RV|" in acal
        # Phrase compressions
        assert "APR+" in acal  # APPROVED WITH MINOR AMENDMENT
        assert "NOE" in acal  # No overlapping edits

    MSG_0108_UPDATE = """\
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
$ROLE: Lead Coder
$INTENT: Log end-of-session summary for April 10
PROJECT: InterAI-Protocol

---PAYLOAD---

SESSION SUMMARY

Per Hub team consensus on architecture.
Phase 2 complete. Ready for review.

---END---
"""

    def test_compress_msg_0108_update(self):
        acal = aicp_to_acal(self.MSG_0108_UPDATE)
        assert acal.startswith("UP:108>107|P>D,L,F,S,T,U|C!")
        assert "|LC|" in acal
        # Phrase compressions in payload
        assert "HTC" in acal  # Per Hub team consensus
        assert "PHS:2" in acal  # Phase 2
        assert "RFR" in acal  # Ready for review


# =====================================================================
# Round-trip validation
# =====================================================================


class TestRoundTrip:
    """Round-trip AICP -> ACAL -> AICP validation."""

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

RECEIPT ACKNOWLEDGED.

---END---
"""

    REQUEST_MSG = """\
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

    REVIEW_MSG = """\
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

APPROVED WITH MINOR AMENDMENT.

---END---
"""

    def test_roundtrip_ack(self):
        is_eq, report = validate_roundtrip(self.ACK_MSG)
        assert is_eq, f"ACK round-trip failed: {report}"

    def test_roundtrip_request(self):
        is_eq, report = validate_roundtrip(self.REQUEST_MSG)
        assert is_eq, f"REQUEST round-trip failed: {report}"

    def test_roundtrip_review(self):
        is_eq, report = validate_roundtrip(self.REVIEW_MSG)
        assert is_eq, f"REVIEW round-trip failed: {report}"


# =====================================================================
# Edge cases
# =====================================================================


class TestEdgeCases:
    """Edge cases: missing REF, broadcast, default priority omission."""

    def test_missing_ref_in_acal(self):
        """ACAL header without >REF should parse with empty ref."""
        acal = "RQ:50|D>P|Q!|OR|IP|Some task"
        result = parse_acal(acal)
        assert result["ref"] == ""

    def test_broadcast_to_all(self):
        """Broadcast using * should expand to ALL."""
        acal = "RQ:50|D>*|Q!|OR|IP|Broadcast|Notify all"
        aicp = acal_to_aicp(acal, seq=50, timestamp="2026-04-14T12:00:00-04:00")
        assert "$TO: ALL" in aicp

    def test_default_high_priority_omission(self):
        """When priority is HIGH (default), ACAL still includes ! but
        the expander should produce $PRIORITY: HIGH."""
        acal = "AK:5>4|P>D|C!|LC|IP|Done|Confirmed"
        aicp = acal_to_aicp(acal, seq=5, timestamp="2026-04-14T12:00:00-04:00")
        assert "$PRIORITY: HIGH" in aicp

    def test_acal_no_priority_char_defaults_high(self):
        """Status char only (no priority char) should default to HIGH."""
        acal = "AK:5>4|P>D|C|LC|IP|Done"
        result = parse_acal(acal)
        assert result["priority"] == "!"
        aicp = acal_to_aicp(acal, seq=5, timestamp="2026-04-14T12:00:00-04:00")
        assert "$PRIORITY: HIGH" in aicp

    def test_missing_ref_in_aicp_compression(self):
        """AICP message without $REF should produce ACAL with no >REF."""
        aicp = """\
$PROTO: AICP/1.0
$TYPE: REQUEST
$ID: MSG-0001
$FROM: Don
$TO: Pharos
$TIME: 2026-03-09T08:00:00-05:00
$TASK: Test task
$STATUS: PENDING
$PRIORITY: HIGH
PROJECT: InterAI-Protocol

---PAYLOAD---
Hello.
---END---
"""
        acal = aicp_to_acal(aicp)
        # Should be RQ:1|D>P|... with no >REF
        assert acal.startswith("RQ:1|D>P|")
        assert ">|" not in acal.split("|")[0]  # no dangling >

    def test_empty_payload(self):
        """ACAL with no payload should still produce valid AICP."""
        acal = "AK:5|P>D|C!|LC|IP|Done"
        aicp = acal_to_aicp(acal, seq=5, timestamp="2026-04-14T12:00:00-04:00")
        assert "---PAYLOAD---" in aicp
        assert "---END---" in aicp

    def test_missing_domain_in_aicp_roundtrip(self):
        """AICP without explicit DOMAIN should derive it from PROJECT."""
        aicp = """\
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
ACK.
---END---
"""
        acal = aicp_to_acal(aicp)
        expanded = acal_to_aicp(acal, seq=5, timestamp="2026-03-09T08:10:00-05:00")
        assert "DOMAIN: Multi-Agent Systems" in expanded

    def test_operatorhub_project_domain(self):
        """OH project code should derive Flow Cytometry domain."""
        acal = "RQ:1|D>P|Q!|OR|OH|Some OH task"
        aicp = acal_to_aicp(acal, seq=1, timestamp="2026-04-14T12:00:00-04:00")
        assert "PROJECT: OperatorHub" in aicp
        assert "DOMAIN: Flow Cytometry Lab Operations" in aicp
