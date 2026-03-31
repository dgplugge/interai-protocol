$PROTO: AICP/1.0
$TYPE: REQUEST
$ID: OH-MSG-SKILLS-0001
$REF: NONE
$SEQ: 68
$FROM: Don
$TO: Pharos, Lodestar
$TIME: 2026-03-30T23:59:00-04:00
$TASK: Capture future enhancement ideas for integrating Skills into AICP
$STATUS: PENDING
$PRIORITY: MEDIUM
$ROLE: Orchestrator
$INTENT: Record design ideas for future exploration of how Skills-like capabilities could complement AICP without changing current priorities
PROJECT: InterAI-Protocol
DOMAIN: Multi-Agent Systems / Future Architecture

---PAYLOAD---

CONTEXT:
Current AICP work is focused on protocol structure, project registry, Study Guide, and n8n integration. This message is not a request for immediate implementation. It is intended to capture future design ideas so they can be reviewed later.

QUESTION:
How might "Skills" concepts be integrated into AICP in a way that complements rather than replaces the protocol?

WORKING ASSUMPTION:
Skills and AICP operate at different layers:
- Skills = reusable capability packages inside an agent
- AICP = communication and coordination protocol between agents

FUTURE ENHANCEMENT IDEAS TO EXPLORE:

1. SKILL-AWARE AGENTS
- Allow agent registry entries to declare supported skills
- Example:
  - Pharos supports: coding, refactoring, parser-design
  - Lodestar supports: architecture-review, protocol-design, system-planning
- Routing could later consider both agent identity and declared skill set

2. SKILL REGISTRY
- Add a lightweight registry of reusable skills
- Potential fields:
  - skillId
  - skillName
  - description
  - owningAgent
  - inputs
  - outputs
  - triggerHints
  - status
- This would be distinct from Project Registry and Agent Registry

3. MESSAGE-LEVEL SKILL HINTS
- Future optional fields could indicate desired skill usage without changing core protocol
- Examples:
  - SKILL: architecture-review
  - SKILLSET: protocol-design, workflow-analysis
- These would remain optional to preserve backward compatibility

4. ROUTING BY SKILL
- Future routing resolver could choose an agent based on:
  - canonical agent name
  - role
  - skill availability
- Example:
  - route any "refactor parser" request to an agent with parser-design + coding skills

5. SKILL INVOCATION AS INTERNAL AGENT BEHAVIOR
- AICP should coordinate agents, not replace their internal reasoning methods
- An agent may internally activate one or more skills while responding to a message
- Protocol remains focused on coordination, not internal implementation details

6. SKILL TEMPLATES
- Certain message/task categories could later map to recommended skills
- Examples:
  - REVIEW → architecture-review
  - REQUEST for coding → implementation
  - PLAN → system-planning
- This could improve consistency without hardcoding behavior

7. SKILL-TO-AICP BRIDGE
- Consider whether a skill could help:
  - generate valid AICP messages
  - validate message structure
  - propose routing options
  - draft ACK/REVIEW/PLAN responses
- This may be a practical first integration point

8. OBSERVABILITY / AUDIT
- If skills are ever invoked in a structured way, decide how much should be visible in journals
- Possible lightweight approach:
  - log only that a skill category was used
  - avoid excessive internal detail

9. BOUNDARY TO PRESERVE
- Do not allow Skills integration to blur the purpose of AICP
- AICP should remain:
  - transportable
  - tool-agnostic
  - protocol-centered
- Skills should be treated as optional capability layers, not protocol replacements

OPEN DESIGN QUESTIONS FOR LATER:
1. Should Skills be modeled as first-class registry objects, or simply metadata on agents?
2. Should skill hints appear in the core message envelope, payload, or not at all?
3. How much skill usage should be journaled?
4. Should n8n routing eventually use skill metadata?
5. Is there value in a dedicated Skill Registry before registry-aware routing is complete?

NOTES:
This is a future enhancement capture only.
No implementation is requested at this time.
Current priorities remain:
- active AICP workflow improvements
- Study Guide refinement
- n8n integration
- Project Registry usage

DELIVERABLE FOR FUTURE REVIEW:
When priorities allow, review these ideas and propose:
- whether Skills integration is worthwhile
- minimal first step
- architecture impact
- risks of overlap or unnecessary complexity

---END---
