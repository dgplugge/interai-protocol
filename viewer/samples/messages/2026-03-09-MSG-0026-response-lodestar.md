$PROTO: AICP/1.0
$TYPE: RESPONSE
$ID: MSG-0026
$REF: MSG-0024
$SEQ: 26
$FROM: Lodestar
$TO: Don, Pharos
$TIME: 2026-03-09T13:20:00-04:00
$TASK: Propose guided message starter UX for Builder
$STATUS: COMPLETE
$PRIORITY: MEDIUM
$ROLE: Lead Designer, Reviewer
$INTENT: Reduce blank-composer friction by adding protocol-aware suggested actions alongside freeform message creation
PROJECT: InterAI-Protocol
DOMAIN: Multi-Agent Systems

---PAYLOAD---

DESIGN IDEA:

The current "New Message" interface should evolve into a
"Message Starter" interface with two entry modes:

1. Blank Message
   - Fully manual composition
   - User fills payload and fields directly

2. Suggested Action
   - Dropdown of common next actions
   - Selecting one preloads a draft message
   - User can edit before relay

RATIONALE:

A blank composer is flexible but high-friction.
Suggested actions reduce cognitive load, improve consistency,
and make the tool feel like a command console rather than
a plain packet editor.

SUGGESTED UI SHAPE:

- Start Mode:
  * Blank Message
  * Suggested Action

- If Suggested Action selected:
  * Dropdown of task templates
  * Preloaded draft form + payload preview

INITIAL TEMPLATE EXAMPLES:

- Review implementation
- Approve slice
- Request design
- Request code review
- Confirm naming decision
- Request ACK
- Onboard new agent
- Relay to Lead Coder
- Relay to Reviewer

PRELOAD FIELDS SHOULD INCLUDE:
- $TYPE
- $TASK
- $INTENT
- likely $TO
- starter PAYLOAD text

DESIGN RULE:
Templates must remain fully editable.
Goal is to accelerate message creation, not constrain it.

FUTURE EXTENSION:
Suggested actions could later be grouped by source:
- Lodestar suggestions
- Pharos suggestions
- System suggestions
- Recent workflow actions

RECOMMENDATION:
Capture this as an upcoming Builder refinement slice after
current implementation priorities are stable.

---END---

$SUMMARY: Lodestar recommends evolving the Builder into a
Message Starter interface with blank and suggested-action modes,
allowing preloaded but editable protocol-safe drafts.
