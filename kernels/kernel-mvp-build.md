# CONTEXT KERNEL: MVP Build
# Version: 1.4 | Updated: 2026-04-25 | Task: interai-protocol MVP convergence

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

NO-FABRICATION RULE (mandatory):
  If any input referenced in the prompt is missing from your context
  (e.g. "using the mvp-build kernel" but the kernel text is not present),
  you MUST respond with $DECISION: CLARIFY and name the missing input.
  You MUST NOT:
    - Infer, guess, or reconstruct kernel contents from memory
    - Propose candidates that are not visibly present in the prompt
    - Issue $DECISION: EXECUTE against inferred or fabricated options
    - Present hallucinated content inside a summary table or consensus frame
  Fabrication with a confident EXECUTE is the worst failure mode in
  this system — it manufactures false consensus. When blocked by
  missing input, one line of CLARIFY is the correct, complete response.
  Do not pad CLARIFY responses; ~30 tokens is sufficient.

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

Repo state (as of 2026-04-25, commit 0be3a72):

BUILT (in tree, tested, committed):
  api/server.py                          — FastAPI journal API (v2.3.0)
    Endpoints: /threads, /dispatch, /kernels, /agents, /health
    Dispatch supports PARALLEL | SEQUENTIAL | ROUND_ROBIN turn modes
    Optional ?kernel=<name> query injects a context kernel
    decision_validator + thread_tracker invoked on both /messages and
      /dispatch paths; responses carry messages_since_compact + compact_due
    GET /agents and GET /agents/{name}/card serve per-agent profile cards
    Summarizer endpoints: /summary-due, /retrieve, /generate-summary,
      /rag-prefix (text/plain prefix block for Hub splice)
  src/acal/converter.py                  — ACAL ↔ AICP bidirectional
  src/acal/verifier.py                   — round-trip verification
  src/kernel/loader.py                   — kernel discovery + 8K budget
  src/middleware/rate_limiter.py         — per-provider delays
  src/middleware/retry_handler.py        — per-provider retry config
  src/middleware/token_estimator.py      — char/token estimate
  src/middleware/decision_validator.py   — $DECISION enforcement (Slice 8.6)
  src/middleware/thread_compactor.py     — thread summaries at N=10 (Slice 8.5)
  src/middleware/summary_*.py            — TieredSummary store, meta counter,
    SQLite chunk_index, RAG retrieval, Haiku tier generator, fidelity
    check, opt-in background scheduler
  src/middleware/embedder.py             — OpenAI text-embedding-3-small
  scripts/backfill_embeddings.py         — CLI for NULL-embedding rows
  src/hub/{cli,status}.py                — health dashboard + CLI
  viewer/server.py                       — AICP Viewer (filters, search, badges)
  kernels/kernel-acal-dev.md             — first live kernel
  agents/*.md                            — per-agent profile cards (all 6:
    lumen, lodestar, spindrift, trident, pharos, forge). Each card
    includes Role, Response discipline, documented failure modes,
    Identity anchoring, and a unique canary string.

NOT YET BUILT (candidates for next work):
  Hub VB.NET card injection — this repo serves /agents/{name}/card;
    the Hub VB.NET app must fetch and prepend as system message before
    each provider call. Status as of 2026-04-25: PENDING VERIFICATION.
    Canary-based test prompt drafted; Don to broadcast and report results.
    Cards are latent until that wiring lands and is verified for all 6
    agents (including pharos and forge, added since the original 4-card
    deployment).
  Context Kernel update protocol — how Hub writes learnings back into
    STATE/MEMORY sections after a dispatch. Loader reads; nothing writes.
  CBOR compaction — thread_compactor.py currently emits JSON sidecars.
    CBOR optimization was explicitly deferred in Slice 8.5.
  Auto-compact on threshold — compact_due is surfaced but /compact must
    still be called explicitly. Consider auto-trigger in future slice.
  End-to-end integration test — dispatch → validator → compactor → summary
    covered per-module but no full-round pytest yet.
  Trident truncation in Hub Gemini client — MSG-0155 R5 truncated at
    $ROLE header; likely max_tokens or timeout misconfigured in Hub.
    Diagnosis and fix belongs in Hub VB.NET code.

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

[2026-04-17] NEXT_STEPS #1 [P,F] DONE: decision_validator and
  thread_tracker now invoked on /dispatch as well as /messages.
  Both endpoints return messages_since_compact + compact_due so Hub
  can trigger /compact when threshold reached. Tests: 175 passed.

[2026-04-17] NEXT_STEPS #6 [P,L] DONE (repo side): Agent profile card
  system. agents/ directory with four cards (lumen, lodestar, spindrift,
  trident) targeting documented failure modes. GET /agents and
  GET /agents/{name}/card endpoints serve cards. Tests: 199 passed.
  Hub VB.NET injection still pending — cards are latent until wired.

[2026-04-17] MSG-0155 round evidence: Lumen moved off fabrication floor
  (no invented $DECISION values, summary claims factually accurate).
  Lodestar still defaults to architectural platitudes. SpinDrift still
  echoes and cites other agents. Trident response truncated (infra).
  Card deployment expected to correct remaining behaviors once live.

[2026-04-22 — 04-23] Summarizer-Role feature shipped (Rounds 1–8).
  Three-tier YAML summary + SQLite chunk_index + RAG retrieval. New
  endpoints: /summary-due, /retrieve, /generate-summary, /rag-prefix.
  Opt-in background scheduler. Backfill CLI for NULL embeddings. See
  docs/summarizer-feature.md. Hub VB.NET RAG consumer (FetchRagContext
  in AgentHubPresenter.vb, interai-hub commit 42664a2) prepends the
  rag-prefix block to each dispatch.

[2026-04-25] Pharos and Forge profile cards added (agents/pharos.md,
  agents/forge.md). All 6 agents now carded. Test suite updated:
  test_pharos_now_carded / test_forge_now_carded replace the prior
  _not_carded_yet expectations; pharos and forge added to the
  parametrized content checks. 30 agent-card tests pass.

[2026-04-25] PROVIDERS table fix: Lumen role flipped from
  "Pending Setup" to "Efficiency Specialist" in api/server.py. Default-
  agent dispatches now include Lumen instead of silently excluding her.

[2026-04-25] Hub-side card injection PENDING VERIFICATION. Canary-based
  test prompt drafted: round-robin all 6 agents, ask each to report its
  canary string, expect either the exact card-defined canary or the
  literal NO-CARD-LOADED. Don to broadcast and report results; that
  result determines whether NEXT_STEPS #6 closes or remains open.

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
   Status: DONE (2026-04-17, MSG-0146) — see MEMORY.

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

6. [P,L] Agent profile card system. agents/*.md + /agents/{name}/card
   endpoint in this repo + Hub VB.NET fetch-and-prepend.
   Status: REPO-SIDE DONE for all 6 agents (2026-04-25 — pharos and
   forge added since the original 4-card deployment). Hub-side
   verification PENDING via canary test prompt.

7. [L,F] Fix Trident truncation in Hub's Gemini client (MSG-0155 R5).
   Investigate max_tokens, timeout, or stream parser. Hub VB.NET work.
   Status: PROPOSED

Do NOT propose:
  - Anything Node.js / Express / Winston / Supertest
  - Re-building decision_validator or thread_compactor (already shipped)
  - A new $DECISION value outside {CHALLENGE, CLARIFY, EXECUTE}
