# CONTEXT KERNEL: MVP Build
# Version: 1.0 | Updated: 2026-04-17 | Task: interai-protocol MVP convergence

---PROTO---

Repo: interai-protocol  (H:\Code\interai-protocol)
Stack: Python 3 / FastAPI / pytest / Pydantic v2
NOT a Node.js repo. Do not propose Express, Winston, Supertest, or any
JavaScript toolchain. If a design requires a Node library, restate it
using the Python equivalent (FastAPI middleware, `logging`/structlog,
pytest + httpx.TestClient).

AICP envelope discipline:
  $PROTO: AICP/1.0
  $TYPE:  REQUEST | RESPONSE | ACK | ERROR | UPDATE
  $ID, $REF, $SEQ, $FROM, $TO, $STATUS, $TASK, $DECISION

$DECISION header — canonical values (enforced by decision_validator.py):
  CHALLENGE — disagree with a prior claim; state reason
  CLARIFY   — ask for missing information before committing
  EXECUTE   — commit to a concrete action
Only these three values are valid. Do NOT invent new states
(e.g. PROPOSED, APPROVED, DEFERRED — those are out of spec).

Every RESPONSE message MUST carry a $DECISION header. Missing or
invalid → rejected with DECISION_REQUIRED or INVALID_DECISION_STATE.

Open tasks use: $STATUS: OPEN  +  $TASK: <description>
  (Not $OPEN: — that form will not be parsed by the compactor.)

---ROSTER---

Active agents for this kernel:

D = Don       | OR  | Orchestrator          | Human operator
P = Pharos    | LC  | Lead Coder            | Anthropic / Claude Sonnet 4
L = Lodestar  | LD  | Lead Designer         | OpenAI / GPT-4o
F = Forge     | IL  | Design/Build Spec     | OpenAI / o3-mini
S = SpinDrift | RV  | Reviewer/Integrator   | OpenAI / GPT-4o
T = Trident   | AR  | Research/Synthesis    | Google / Gemini 2.5 Flash
U = Lumen     | ES  | Efficiency Specialist | Mistral / Devstral 2

Identity rule: agents must use their own code in all messages.
Never adopt another agent's code.

---STATE---

Repo state (as of 2026-04-17, commit ebf2654):

BUILT (in tree, tested, committed):
  api/server.py                          — FastAPI journal API (v2.3.0)
    Endpoints: /threads, /dispatch, /kernels, /health
    Dispatch supports PARALLEL | SEQUENTIAL | ROUND_ROBIN turn modes
    Optional ?kernel=<name> query injects a context kernel
  src/acal/converter.py                  — ACAL ↔ AICP bidirectional
  src/acal/verifier.py                   — round-trip verification
  src/kernel/loader.py                   — kernel discovery + 8K budget
  src/middleware/rate_limiter.py         — per-provider delays
  src/middleware/retry_handler.py        — per-provider retry config
  src/middleware/token_estimator.py      — char/token estimate
  src/middleware/decision_validator.py   — $DECISION enforcement (Slice 8.6)
  src/middleware/thread_compactor.py     — thread summaries at N=10 (Slice 8.5)
  src/hub/{cli,status}.py                — health dashboard + CLI
  viewer/server.py                       — AICP Viewer (filters, search, badges)
  kernels/kernel-acal-dev.md             — first live kernel

NOT YET BUILT (candidates for next work):
  Middleware wiring — decision_validator.py and thread_compactor.py exist
    but are not wired into the dispatch request path. See api/server.py
    dispatch_round(). Adding them is a small FastAPI middleware registration.
  Context Kernel update protocol — how Hub writes learnings back into
    STATE/MEMORY sections after a dispatch. Loader reads; nothing writes.
  CBOR compaction — thread_compactor.py currently emits JSON sidecars.
    CBOR optimization was explicitly deferred in Slice 8.5.

EXTERNAL (Hub VB.NET app, not in this repo):
  Provider API calls (Anthropic/OpenAI/Google/Mistral SDKs)
  Turn-mode orchestration (hourglass posting, dispatch rounds)

---MEMORY---

[2026-04-14] ACAL v0.1 approved with amendments (APR+, Hub consensus).
  AMD-1 delimiter escapes, AMD-2 edge tokens, AMD-3 identity anchoring.

[2026-04-14] Context Kernel v0.1 concept ratified. This file format.

[2026-04-16] Slices 8.5 ($DECISION enforcement) and 8.6 (thread
  compaction at N=10) committed (ebf2654).

[2026-04-16] Kernel loader wired into dispatch via ?kernel= query
  param (e8acbd4). Kernels inject as system-prompt preamble.

[2026-04-17] Hub transcript analysis revealed two bloat patterns:
  (a) Agents design against wrong stack (proposed Node.js for a
      Python repo) when stack not pinned in preamble.
  (b) Agents propose features that already exist in the tree when
      recent commits are not surfaced. This kernel is the corrective.

---DICT---

Task-specific tokens for MVP convergence:

MVP = Minimum viable product for the interai-protocol repo
WIRE = Register existing middleware into FastAPI request pipeline
MWR = Middleware registration (FastAPI .add_middleware call)
SOT = Source of truth (canonical spec/impl)
STALE = Agent claim that conflicts with current repo state
SKEW = Design proposed against the wrong stack

---NEXT_STEPS---

Candidate next moves (choose ONE per round, do not fan out):

1. [P,F] WIRE decision_validator + thread_compactor into api/server.py
   dispatch pipeline. Both modules exist; neither is currently invoked
   on live dispatches. Smallest high-value delta.
   Status: PROPOSED

2. [L]  Design kernel update protocol — how does Hub write agent
   decisions back into STATE/MEMORY sections of the active kernel?
   Currently kernels are read-only at runtime.
   Status: PROPOSED — architecture work

3. [U]  Propose token-budget enforcement at dispatch time (warn if
   kernel + prompt + expected response exceeds provider context).
   Status: PROPOSED

4. [S]  Integration test covering a full round: dispatch → validator
   → compactor → summary sidecar. End-to-end pytest.
   Status: PROPOSED

5. [T]  Research: do any providers support native structured output
   that could enforce $DECISION server-side? Report, don't implement.
   Status: PROPOSED

Do NOT propose:
  - Anything Node.js / Express / Winston / Supertest
  - Re-building decision_validator or thread_compactor (already shipped)
  - A new $DECISION value outside {CHALLENGE, CLARIFY, EXECUTE}
