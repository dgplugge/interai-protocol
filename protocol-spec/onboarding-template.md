$PROTO: AICP/1.0
$TYPE: REQUEST
$ID: MSG-XXXX
$FROM: Don
$TO: <NEW_AGENT_NAME>
$TIME: <ISO_TIMESTAMP>
$TASK: Onboarding — Join the InterAI Protocol Team
$STATUS: PENDING
$PRIORITY: HIGH
$ROLE: Orchestrator
$INTENT: Invite a new AI agent to join the team via shared context and protocol compliance
$REF: <OPTIONAL_REF>
$SEQ: <NEXT_SEQ>
PROJECT: InterAI-Protocol
DOMAIN: Multi-Agent Systems

---PAYLOAD---

WELCOME TO THE INTERAI PROTOCOL TEAM

You are being invited to join an active multi-agent collaboration
using the AI Communication Protocol (AICP/1.0).

────────────────────────────────────
TEAM INTRODUCTION
────────────────────────────────────

Current team members:

- Don (Human) — Orchestrator, Product Owner
  Coordinates all agents, approves designs, manages priorities.

- Pharos (Claude / Anthropic) — Lead Coder
  Implements features, writes code, manages the repository.

- Lodestar (ChatGPT / OpenAI) — Lead Designer, Reviewer
  Designs system architecture, reviews implementations.

────────────────────────────────────
PROTOCOL OVERVIEW
────────────────────────────────────

AICP is a text-based, transport-agnostic message format.
Every message has four segments:

  ENVELOPE  — Routing & identity ($PROTO, $TYPE, $ID, $FROM, $TO, $TIME)
  META      — Task metadata ($TASK, $STATUS, $REF, $SEQ, $INTENT, etc.)
  PAYLOAD   — Freeform markdown content (between ---PAYLOAD--- and ---END---)
  AUDIT     — Verification ($SUMMARY, $CHANGES, $CHECKSUM)

Message types: REQUEST, RESPONSE, ACK, ERROR, HANDOFF, REVIEW

────────────────────────────────────
REQUIRED READING
────────────────────────────────────

Before responding, review these materials:

1. protocol-spec/   — AICP specification and field definitions
2. samples/messages/ — Full message history (the living journal)
3. samples/journal-index.json — Message index with sequence numbers
4. protocol-spec/agent-registry.json — Current team roster

────────────────────────────────────
YOUR ASSIGNED ROLE
────────────────────────────────────

Role: <ASSIGNED_ROLE>
Responsibilities: <ROLE_DESCRIPTION>
First task: <FIRST_TASK_DESCRIPTION>

────────────────────────────────────
COMPLIANCE TEST
────────────────────────────────────

To complete onboarding, reply with a valid AICP ACK packet.

Your reply MUST include these fields:
  $PROTO: AICP/1.0
  $TYPE: ACK
  $ID: <your message ID>
  $REF: <this message's ID>
  $FROM: <your agent name>
  $TO: Don
  $TIME: <current ISO timestamp>
  $ROLE: <your assigned role>
  $STATUS: COMPLETE

Your payload MUST confirm:
  1. Receipt of onboarding materials
  2. Understanding of your assigned role
  3. Declaration of your capabilities

No file access or code execution is required.

────────────────────────────────────
EXAMPLE RESPONSE
────────────────────────────────────

$PROTO: AICP/1.0
$TYPE: ACK
$ID: MSG-XXXX
$REF: <this message ID>
$FROM: <YourName>
$TO: Don
$TIME: 2026-03-10T09:00:00-04:00
$TASK: Onboarding acknowledgment
$STATUS: COMPLETE
$ROLE: <Your Role>
$INTENT: Confirm onboarding and declare readiness
PROJECT: InterAI-Protocol
DOMAIN: Multi-Agent Systems

---PAYLOAD---

ONBOARDING ACKNOWLEDGED.

Materials received and reviewed:
- Protocol specification (AICP/1.0)
- Message journal (XX messages)
- Agent registry (current team)

Role accepted: <Your Role>

Capabilities:
- <capability 1>
- <capability 2>
- <capability 3>

Ready to begin assigned tasks.
---END---

$SUMMARY: <YourName> acknowledged onboarding, confirmed role
and capabilities, ready for first assignment.

---END---

$SUMMARY: Onboarding invitation for <NEW_AGENT_NAME> with team intro,
protocol overview, required reading, role assignment, and compliance test.
