TO ALL HUB AGENTS — CONTEXT KERNEL ARCHITECTURE INTRODUCTION

Following the successful ACAL v0.1 verification (APR+ consensus from Lodestar, Forge, and SpinDrift), Pharos is introducing the next architectural evolution: Context Kernels. Read the full AICP message and specification below, then complete the response task at the bottom.

== BEGIN MSG-0115 ==

$PROTO: AICP/1.0
$TYPE: REQUEST
$ID: MSG-0115
$REF: MSG-0110
$SEQ: 146
$FROM: Pharos
$TO: Don, Lodestar, Forge, SpinDrift, Trident, Lumen
$TIME: 2026-04-14T14:30:00-04:00
$TASK: Context Kernel Architecture — Shared Agent Memory via Living Prompt Files
$STATUS: IN_PROGRESS
$PRIORITY: HIGH
$ROLE: Lead Coder
$INTENT: Introduce the Context Kernel concept and request design feedback from all agents
PROJECT: InterAI-Protocol
DOMAIN: Multi-Agent Systems

---PAYLOAD---

TO ALL HUB AGENTS:

== THE PROBLEM ==

Every Hub API call is stateless. Agents have no memory between calls. Context must be reconstructed from scratch each time. This limits continuity, wastes tokens on repeated context, and prevents agents from building on prior decisions.

== THE SOLUTION: CONTEXT KERNELS ==

A Context Kernel is a self-contained prompt file that serves as shared memory across all agents. The Hub loads it into every agent's system prompt on every call for a given task. After each response, the Hub updates the kernel with new learnings.

Key properties:
- One kernel per task/workstream (multiple kernels run in parallel)
- Written in ACAL for maximum compression (~8K token budget)
- Six mandatory sections (see below)
- Versioned and archived via git
- Any agent can produce a status report from any kernel on demand

== SIX SECTIONS (mandatory, in this order) ==

1. PROTO — ACAL reference card and protocol rules. Ensures every agent can parse and generate ACAL regardless of provider.

2. ROSTER — Active agents for this task. Agent codes, roles, and any task-specific role overrides. Not every agent participates in every kernel.

3. STATE — Current status of the task. What is done, what is in progress, what is blocked. Updated after every round.

4. MEMORY — Key decisions, consensus outcomes, and amendments. Timestamped and append-only. Archived when old.

5. DICT — Task-specific ACAL tokens. New shorthand that agents agree upon during this task. May graduate to the global ACAL dictionary.

6. NEXT_STEPS — Planned actions, who owns them, and dependencies. Updated at the end of each round. Any agent can be asked to produce a status report from this section alone.

== LIFECYCLE ==

CREATE: Orchestrator or Lead Coder starts a new kernel for a new task.
LOAD: Hub injects the kernel into each agent's system prompt per API call.
UPDATE: After each agent response, Hub extracts learnings and updates the kernel.
REVIEW: Any agent can report on kernel state (read-only, no modifications).
ARCHIVE: Task complete, kernel moves to /archived/ with completion summary.
FORK: Task splits into subtasks, child kernel inherits parent PROTO/ROSTER/MEMORY.

== WHAT THIS ENABLES ==

- Agents behave as if they have persistent memory (the prompt IS the memory)
- ACAL compression means ~24K words of context fit in 8K tokens
- Decisions persist across sessions without agent-side storage
- Multiple independent workstreams run in parallel via separate kernels
- Status reports on demand from any agent on any kernel
- Recursive improvement: the kernel gets smarter with each cycle

== EXAMPLE: THE FIRST LIVE KERNEL ==

The first kernel is kernel-acal-dev.md, tracking ACAL language development. Its six sections contain:

PROTO: Full ACAL v0.1 reference card and grammar rules
ROSTER: All 7 agents with codes, roles, and identity anchoring rule
STATE: ACAL v0.1 APR+ with 3 amendments pending, converter built (39 tests passing)
MEMORY: Timeline of today's work — spec creation, verification broadcast, APR+ consensus, identity error finding
DICT: 9 task-specific tokens (CK, KLD, KUP, KRV, KAR, KFK, VPR, IDN, etc.)
NEXT_STEPS: 8 planned actions with owners and status

== THE KEY UNSOLVED DESIGN QUESTION ==

How should the Hub extract learnings from agent responses and fold them back into the kernel? Options include:
- Manual: Orchestrator (Don) edits the kernel after each round
- Semi-auto: Hub presents suggested updates for orchestrator approval
- Automated: A designated agent parses responses and proposes kernel patches
- Hybrid: Agents include a structured "KERNEL_UPDATE" section in their responses that the Hub can parse directly

This is the question we most need your input on.

---END---

== END MSG-0115 ==

== ACAL QUICK REFERENCE CARD (for context) ==

MESSAGE TYPES    AGENTS    STATUS    PRIORITY    ROLES
RQ = Request     D = Don   C = Done  ! = High    LC = Lead Coder
RS = Response    P = Phar  W = WIP   . = Med     LD = Lead Designer
AK = ACK         L = Lode  Q = Pend  _ = Low     RV = Reviewer
RV = Review      F = Forge A = Appr              OR = Orchestrator
UP = Update      S = Spin  X = Fail              AR = Architect
PL = Plan        T = Trid  H = Hold              ES = Efficiency Spec
ER = Error       U = Lumen
BS = Brainstorm  * = All

ACTIONS          LAYERS           PHRASES
+ = Add          V  = View        ACK = Acknowledged
~ = Modify       PR = Presenter   APR = Approved
- = Remove       M  = Model       APR+ = Approved w/ amendments
? = Review       SV = Service     AWO = Awaiting orchestrator
! = Approve      AD = Adapter     RFR = Ready for review
^ = Refactor     MW = Middleware   RFI = Ready for implementation
> = Deploy       DB = Database    NOE = No overlapping edits
# = Test         CF = Config      HTC = Hub team consensus
@ = Fix          IF = Interface   SCR = Success criteria
< = Migrate      TS = Test        SLC:N = Slice N
& = Route        PX = Parser      PHS:N = Phase N
                 WH = Webhook     BC = Backward compatible
                 RT = Router      BRK = Breaking change

HEADER: TYPE:ID>REF|FROM>TO|STATUS PRIORITY|ROLE|PROJECT|TASK|INTENT
PAYLOAD: ACTION LAYER target {params}; chain with semicolons
CONTEXT: $PROTO/$TIME/$SEQ/DOMAIN implicit. HIGH priority is default.

IDENTITY RULE: You MUST use YOUR agent code in all ACAL messages.
Never adopt another agent's code. Your response is FROM YOU.

== YOUR RESPONSE MUST INCLUDE ==

1. Do you understand the Context Kernel architecture? (Y/N with brief explanation)
2. What risks or failure modes do you see?
3. What section would you add, remove, or modify in the six-section format?
4. How should the Hub extract learnings from agent responses to update the kernel? (This is the key design question — propose a specific mechanism)
5. Write a short ACAL message using YOUR OWN agent code acknowledging this concept.

LODESTAR ADDITIONAL TASK: Provide a design review of the Context Kernel architecture. Focus on the update protocol — how learnings flow from agent responses back into the kernel. State APPROVED, APPROVED WITH AMENDMENTS, or NOT APPROVED with rationale.

Format your entire reply as a standard AICP RESPONSE message with $REF: MSG-0115.
