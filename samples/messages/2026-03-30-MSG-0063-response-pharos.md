$PROTO: AICP/1.0
$TYPE: RESPONSE
$ID: MSG-0063
$REF: OH-MSG-SKILLS-0001
$SEQ: 69
$FROM: Pharos
$TO: Don, Lodestar
$TIME: 2026-03-30T23:59:00-04:00
$TASK: Acknowledge and assess Skills integration capture
$STATUS: COMPLETE
$ROLE: Lead Coder
$INTENT: Confirm receipt of future enhancement ideas, provide initial technical assessment, and identify the most natural first integration point
PROJECT: InterAI-Protocol
DOMAIN: Multi-Agent Systems / Future Architecture

---PAYLOAD---

Don —

Acknowledged. This is a well-structured capture. The layering model is correct: Skills operate inside agents, AICP operates between them. Keeping that boundary clean is the right instinct and should remain the guiding constraint for any future work here.

INITIAL ASSESSMENT:

The 9 ideas fall into three natural tiers:

TIER 1 — LOW COST, HIGH SIGNAL (worth doing when the time comes)
- Idea 1 (Skill-Aware Agents): Adding a `skills` array to existing agent registry entries is trivial. No new registry needed. No protocol changes. Just metadata that routing could optionally use later.
- Idea 7 (Skill-to-AICP Bridge): This is the most practical first integration point. A skill that can generate, validate, or template AICP messages would provide immediate value without touching the protocol itself. It's a tool that uses the protocol, not a change to the protocol.
- Idea 9 (Boundary Preservation): This isn't an implementation item — it's a design principle. Agreed completely. AICP must remain transport-layer and tool-agnostic.

TIER 2 — MODERATE VALUE, DEPENDS ON ROUTING MATURITY
- Idea 3 (Message-Level Skill Hints): Optional custom fields like `SKILL: architecture-review` are already possible in AICP — any non-`$` header is a custom field. No protocol change needed. The question is whether routing should read them, which is a Phase 3 / Slice 8+ concern.
- Idea 4 (Routing by Skill): Only valuable after registry-aware routing exists (n8n Phase 3). Premature before then. When the time comes, it's a resolver enhancement — the Switch contract stays the same.
- Idea 6 (Skill Templates): Interesting for consistency but risks over-constraining message composition. Better to let this emerge from usage patterns than to design it upfront.

TIER 3 — DEFER UNTIL CLEAR NEED
- Idea 2 (Skill Registry): A third registry (alongside Agent Registry and Project Registry) adds maintenance overhead. Recommendation: model skills as agent metadata first (Tier 1, Idea 1). Only promote to a standalone registry if the metadata approach proves insufficient.
- Idea 5 (Skill Invocation as Internal Behavior): Agreed this is internal to each agent. No AICP work needed. Each agent decides how to use its own capabilities.
- Idea 8 (Observability/Audit): Logging skill categories in journal entries is reasonable but only matters after skills are formally invoked. Defer until there's something to observe.

ANSWERS TO OPEN DESIGN QUESTIONS:

1. Skills as registry objects vs. agent metadata?
   → Start as agent metadata. A `skills` array on agent registry entries. Promote to first-class only if the list grows complex or cross-agent skill sharing emerges.

2. Skill hints in envelope, payload, or nowhere?
   → Custom fields (already supported). They live in the header section as non-`$` keys. No envelope change needed.

3. How much skill usage should be journaled?
   → Category only (e.g., "used: architecture-review"), not internal reasoning. One line in the payload, not a new header field.

4. Should n8n routing use skill metadata?
   → Yes, but only in Phase 3 when the resolver reads the agent registry. The Switch contract remains stable.

5. Dedicated Skill Registry before registry-aware routing?
   → No. Complete registry-aware routing first. Skills metadata on agents is sufficient until proven otherwise.

RECOMMENDED FIRST STEP (when priorities allow):
Add a `skills` array to each agent in `agent-registry.json`. No new files, no new endpoints, no protocol changes. Just structured metadata that future routing can optionally use.

Example:
```json
{
  "id": "pharos",
  "name": "Pharos",
  "skills": ["coding", "refactoring", "parser-design", "testing"],
  ...
}
```

This is a 5-minute change that makes the registry richer without adding complexity.

NOTED:
No implementation requested. Current priorities unchanged. This response is filed for future reference alongside the original capture.

---END---
