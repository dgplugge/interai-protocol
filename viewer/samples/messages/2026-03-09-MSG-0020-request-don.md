$PROTO: AICP/1.0
$TYPE: REQUEST
$ID: MSG-0020
$REF: MSG-0019
$SEQ: 20
$FROM: Don
$TO: Pharos, Lodestar
$TIME: 2026-03-09T11:50:00-04:00
$TASK: Implement Slice 2 — Assisted Relay
$STATUS: PENDING
$PRIORITY: HIGH
$ROLE: Orchestrator
$INTENT: Reduce manual relay friction while preserving human-in-the-loop review and approval
PROJECT: InterAI-Protocol
DOMAIN: Multi-Agent Systems

---PAYLOAD---

Slice 2 Goal:
Enable assisted message relay from Builder to Journal and Viewer
without introducing full automation.

Scope (Narrow and Practical):

1. Builder → Relay Flow
   a. After packet preview, user can click:
      "Relay Message"
   b. Packet is saved to journal/messages as .md
   c. journal-index.json updates automatically
   d. Viewer refreshes and displays the new message

2. Human-in-the-loop preserved:
   - User still reviews packet before relay
   - No auto-sending to external agents
   - Clipboard copy remains available

3. Minimal UX Additions:
   - "Relay Message" button
   - Success confirmation toast
   - Viewer auto-refresh trigger

4. Non-Goals (Do NOT implement yet):
   - Direct API messaging between agents
   - Background automation
   - Role-based auto-routing
   - Authentication/permissions layer

5. Implementation Authority:
   Lead Coder → Pharos
   Reviewer → Lodestar
   Orchestrator → Don

Awaiting implementation plan and readiness confirmation.

---END---

$SUMMARY: Orchestrator initiating Slice 2 Assisted Relay to streamline
Builder-to-Journal workflow while preserving human oversight.
