$PROTO: AICP/1.0
$TYPE: REQUEST
$ID: MSG-0021
$REF: MSG-0019
$SEQ: 21
$FROM: Don
$TO: Pharos, Lodestar
$TIME: 2026-03-09T12:05:00-04:00
$TASK: Implement Slice 3 — Agent Registry
$STATUS: PENDING
$PRIORITY: MEDIUM
$ROLE: Orchestrator
$INTENT: Establish a visible and structured registry of participating agents to support identity, roles, routing, and future team expansion
PROJECT: InterAI-Protocol
DOMAIN: Multi-Agent Systems

---PAYLOAD---

Slice 3 Goal:
Create an Agent Registry that defines who is on the team,
their roles, capabilities, permissions, and current status.

This registry becomes the foundation for:
- message routing
- role governance
- permission boundaries
- team onboarding
- UI clarity

Scope (MVP — Read First, Edit Later):

1. Registry Data Model
   Create: /protocol-spec/agent-registry.json

2. Viewer Integration
   - Add "Agents" panel/tab in Viewer
   - Display agent name, type, roles, status indicator

3. Read-Only MVP
   - Registry is loaded and displayed
   - No editing UI yet
   - Manual JSON edits acceptable for now

4. Non-Goals (Not in Slice 3)
   - Role editing UI
   - Permission enforcement logic
   - Auto-routing
   - Authentication layer

5. Implementation Authority
   Lead Coder → Pharos
   Reviewer → Lodestar
   Orchestrator → Don

Awaiting implementation plan and readiness confirmation.

---END---

$SUMMARY: Orchestrator initiating Slice 3 to establish a foundational
Agent Registry supporting identity, roles, capabilities, and future
team expansion.
