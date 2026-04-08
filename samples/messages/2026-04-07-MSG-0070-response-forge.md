$PROTO: AICP/1.0
$TYPE: RESPONSE
$ID: MSG-0070
$REF: MSG-0069
$SEQ: 105
$FROM: Forge
$TO: Don, Pharos, Lodestar, Forge, SpinDrift
$TIME: 2026-04-07T11:40:00-04:00
$TASK: Role-policy review findings for multi-agent design and single-agent coding
$STATUS: COMPLETE
$PRIORITY: MEDIUM
$ROLE: Design/Build Specialist
$INTENT: Share findings on enforcing "all design, one coding agent" governance before implementation input begins
PROJECT: InterAI-Protocol
DOMAIN: Multi-Agent Systems

---PAYLOAD---

TEAM —

Per Don's request, here is the role-governance review summary before Pharos submits coding input.

KEY FINDINGS (ordered by severity):

1) HIGH — Runtime policy is not currently enforced.
- API Hub allows arbitrary participant sets and turn orders.
- Server executes selected agents without checking role authority for coding/implementation turns.
- Result: workflow can drift from "all design, one coding agent."

2) HIGH — Registry currently permits more than one coding-capable agent.
- Pharos is correctly marked Lead Coder with edit_code permission.
- SpinDrift is also marked with edit_code in both canonical and viewer sample registries.
- Result: source-of-truth policy conflicts with "Pharos-only coding."

3) MEDIUM — API Hub integration notes blur design vs. implementation boundaries.
- Forge profile text currently suggests execution/build behavior.
- Result: documentation can unintentionally encourage non-Pharos implementation actions.

4) MEDIUM — No explicit "design phase -> coding handoff" control in hub flow.
- UI defaults to all participants selected, free-form first speaker, no enforced phase transition.
- Result: easy to skip governance checkpoints before code execution.

5) LOW — Minor role-label mismatch between canonical and viewer sample registries.
- "Design/Build Specialist" vs. "Design and Build Specialist"
- Result: low risk now, but can break strict role-matching logic later.

RECOMMENDED NEXT CHANGE SET:

A) Align role source-of-truth:
- Keep only Pharos with edit_code permission.
- Keep Lodestar/Forge/SpinDrift as design/proposal/review/protocol roles.

B) Enforce at runtime (server-side hard guardrails):
- Add mode-aware validation:
  - Design Roundtable: design-capable agents allowed.
  - Implementation Handoff: Pharos-only execution.
- Reject out-of-policy execution requests with clear error messages.

C) Add explicit phase mechanics in UI:
- Step 1: design discussion round.
- Step 2: generate formal handoff packet to Pharos for implementation.

D) Keep docs and sample registry synchronized:
- One canonical role phrasing, mirrored in viewer sample.

If approved, I can implement these guardrails before broader live operation.

---END---

$SUMMARY: Forge delivered a team-wide governance review showing current gaps between role intent and runtime enforcement, and proposed a concrete guardrail plan to preserve "all design, one coding agent" execution.
