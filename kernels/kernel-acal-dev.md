# CONTEXT KERNEL: ACAL Development
# Version: 1.0 | Updated: 2026-04-14 | Task: ACAL Language Development

---PROTO---

ACAL (AICP Compressed Agent Language) v0.1 — Reference Card

MESSAGE TYPES    AGENTS    STATUS    PRIORITY    ROLES
RQ = Request     D = Don   C = Done  ! = High    LC = Lead Coder
RS = Response    P = Phar  W = WIP   . = Med     LD = Lead Designer
AK = ACK         L = Lode  Q = Pend  _ = Low     RV = Reviewer
RV = Review      F = Forge A = Appr              OR = Orchestrator
UP = Update      S = Spin  X = Fail              AR = Architect
PL = Plan        T = Trid  H = Hold              DA = Design Advisor
ER = Error       U = Lumen                       IL = Impl Lead
BS = Brainstorm  * = All                         ES = Efficiency Spec

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
CONTEXT: $PROTO/$TIME/$SEQ/DOMAIN are implicit, never transmitted.
         HIGH priority is default — only mark non-HIGH.

---ROSTER---

Active agents for this kernel:

D = Don       | OR  | Orchestrator          | Human operator
P = Pharos    | LC  | Lead Coder            | Anthropic / Claude
L = Lodestar  | LD  | Lead Designer         | OpenAI / GPT-4o
F = Forge     | IL  | Design/Build Spec     | OpenAI / o3-mini
S = SpinDrift | RV  | Reviewer/Integrator   | OpenAI / GPT-4o
T = Trident   | AR  | Research/Synthesis     | Google / Gemini 2.5 Flash
U = Lumen     | ES  | Efficiency Specialist  | Mistral / mistral-large

All agents active. Identity rule: you MUST use YOUR agent code in
all ACAL messages. Never adopt another agent's code. If the message
you are decoding is FROM agent X, your response is FROM YOU, not X.

---STATE---

ACAL v0.1: APPROVED WITH AMENDMENTS (APR+)
  Spec: docs/aicp-compression-language-v0.1.md
  Converter: src/acal/converter.py (39 tests passing)
  Verification: L=PASS, F=PASS, S=PASS(identity err), T=PENDING, U=PENDING

Context Kernel v0.1: DRAFT
  Spec: docs/context-kernel-spec.md
  This file is the first live kernel.

Hub integration: NOT STARTED
  Kernel loader not yet built into Hub VB.NET code.

---MEMORY---

[2026-04-14] ACAL v0.1 spec created from analysis of 155 journal messages.
  Corpus: IP=95, OH=43, SG=15, PA=2 messages.
  Overall compression: 65-70% average reduction.

[2026-04-14] Verification probe broadcast to all agents (MSG-0110).
  Probe: RV:110|L>P,D|Q.|LD,RV|IP|?IF ACAL spec|Design review
  All responding agents decoded correctly.

[2026-04-14] Hub team consensus: APR+ (3/3 responding agents).
  Lodestar: APR+ (MSG-0112)
  Forge: APR+ (MSG-0114) — cleanest response, identity correct
  SpinDrift: APR+ (MSG-0113) — identity error: responded as Lodestar

[2026-04-14] Three amendments identified (unanimous across agents):
  AMD-1: Define escape sequences for delimiter chars (---, |) in payloads
  AMD-2: Edge-case testing for token disambiguation (RV, !)
  AMD-3: Identity anchoring — agents must echo own code in responses

[2026-04-14] Context Kernel concept proposed by Don.
  Architecture: self-contained prompt files, one per task/workstream.
  Hub loads kernel into system prompt per call. Updates after responses.
  Multiple kernels run in parallel. Any agent can report on any kernel.

[2026-04-14] Lumen provider changed from "Local" to "mistral" in Hub config.
  System prompt added for Lumen (Efficiency and Compression Specialist).

---DICT---

Task-specific tokens for ACAL development:

CK = Context Kernel (this concept)
CK:X = Reference to kernel X (e.g., CK:acal-dev)
KLD = Kernel load (inject into system prompt)
KUP = Kernel update (modify after agent response)
KRV = Kernel review (status report, read-only)
KAR = Kernel archive (task complete, move to archive)
KFK = Kernel fork (split into subtask kernels)
VPR = Verification probe (ACAL readiness test)
IDN = Identity anchoring (agent must assert own code)

---NEXT_STEPS---

1. [D] Review Context Kernel spec and this kernel file.
   Status: PENDING

2. [P] Implement AMD-1: escape sequences for ACAL delimiters.
   Add to converter.py + update spec. Status: PENDING

3. [P] Implement AMD-3: identity assertion validation in converter.
   Status: PENDING

4. [D] Test Lumen (Mistral) in Hub after restart.
   Status: PENDING — waiting for Hub restart

5. [T,U] Complete ACAL verification probe (MSG-0110).
   Trident and Lumen have not yet responded. Status: PENDING

6. [P] Build kernel loader for Hub VB.NET code.
   Read kernel file, inject into system prompt preamble.
   Status: NOT STARTED — requires Hub architecture discussion

7. [L] Design kernel update protocol — how does the Hub extract
   learnings from agent responses and fold into kernel?
   Status: NOT STARTED — design task for Lodestar

8. [*] Broadcast Context Kernel concept to all agents (MSG-0115).
   Status: IN PROGRESS — message being drafted
