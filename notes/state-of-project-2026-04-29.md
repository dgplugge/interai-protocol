# State of the Project — 2026-04-29 readout

A synthesis of what shipped over the prior two weeks, what remains open in priority order, and a consolidated brainstorm catalog. Captured as a durable reference in `notes/` so future sessions can resume without rebuilding the picture from scratch.

---

## What we shipped over the prior two weeks (2026-04-15 → 2026-04-29)

Grouped by theme, with date markers. Each commit / journal entry can be cross-referenced for traceability.

### 1. Decision discipline + thread compaction (Apr 16–17)

- **`$DECISION` validation middleware** enforces CHALLENGE / CLARIFY / EXECUTE on every RESPONSE; rejects with `DECISION_REQUIRED` or `INVALID_DECISION_STATE` (commit `ebf2654`).
- **Thread compaction** at N=10 with summary sidecars (`ebf2654`, MSG-0146).
- Both wired into the `/dispatch` path so the validators actually fire on live broadcasts (`aa8e4c1`).

### 2. Context Kernel system (Apr 16–17)

- **Kernel loader** with section parsing, 8K budget enforcement, caching (`93c8788`).
- **`kernel-mvp-build.md`** — pinned stack/state/roster/dict/next-steps for Hub broadcasts (`ad9119c`).
- **No-fabrication rule** added after observing fabricated `EXECUTE` votes against missing input (`e74e1ab`, kernel v1.1).

> **Correction added 2026-04-29:** the Hub's broadcast flow does NOT actually inject the kernel today. The Python API's `/dispatch` endpoint accepts `?kernel=<name>`, but the Hub talks directly to provider APIs and skips that path. A new enhancement — *project-scoped kernel injection in the Hub* — is captured in the open enhancements list below.

### 3. Agent profile card system (Apr 17–22)

- **All 6 agents now carded**: Lumen, Lodestar, SpinDrift, Trident (Apr 17), then Forge and Pharos (Apr 21–22).
- **Hub-side card injection verified** via canary round 2026-04-26 — every agent returned its exact card-defined canary (MSG-0179, NEXT_STEPS #6 closed).
- **Card-tuning passes** after observed failure modes (`32e2742`, `7c172d8`, `e0cdc52`).
- **Edit Card button + modal editor** in Agent Settings (`bb4a8c4`).
- **Card injection before `Config.SystemPrompt`** so card content takes precedence (`06dca7b`).

### 4. Hub payload hygiene (Apr 20–22)

- **Card content used alone** when card exists (no legacy SystemPrompt concat) (`9a8afec`).
- **Journal context cap**: 5 msgs/project, 1500 chars/msg (`9d2f68b`).
- **Don's-prompt deduplication** in outgoing messages (`3000ad5`).
- **Summarizer-role guard** — only inject the summarizer instruction when there's >1 agent in the round (`928d5ce`).
- **Preview mode + payload logging** for verification dispatches (`9a8afec`).

### 5. Dispatch Cost Ledger (Apr 21–22)

- **Slice 1**: middleware + JSONL store + Hub button + viewer form (`842404b` → `9ec0f0c`).
- **Slice 2**: `LedgerAggregateCache` + `BudgetGateService` + system-prompt hash logging + 24 MSTest unit tests (`34d366b`, `491f4f5`).
- **Anthropic prompt caching** enabled in the adapter (`95c9dd6`).
- **Retry-exhaustion log + derived load window** (`a27e905`).

### 6. Summarizer-Role feature (Apr 22–24) — Q1 through Q8

- **Tiered summary storage** (`TieredSummary`: full / compressed / shorthand) — `803d72b`.
- **Post-commit hook** + staleness detection — `569221a`.
- **Threshold detection** + `summary-due` endpoint — `6fa4128`.
- **Fidelity check runner** for AICP journal entries — `a2e30fb`.
- **Indexer**: SQLite `chunk_index` + CRUD — `8c562aa`.
- **Indexer wired into journal post-commit path** — `5734909`.
- **Embedder** + auto-embed on journal write — `6b7494a`.
- **Similarity retrieval** + `/retrieve` endpoint — `3ba4534`.
- **Three-tier generator** via Claude Haiku — `701ede3`.
- **`agent_config` loader** with fallback chain + API-key resolver — `c9590e0`.
- **`/rag-prefix` text endpoint** for the Hub consumer — `f728b8a`.
- **Background scheduler** (off by default) — `332f73d`.
- **Backfill utility** for missing embeddings + chunk_index — `e507be8`, `6982239`.
- **Hub VB.NET RAG consumer** (`FetchRagContext`) — interai-hub@`42664a2`.
- **Integration tests** for the four new summarizer endpoints — `12964be`.

### 7. Hub UI controls (Apr 26–27)

- **Include RAG context checkbox** — per-dispatch RAG short-circuit (interai-hub@`ecd9881`).
- **Project selector dropdown** with ghost-project typo confirmation + history-clear on switch + title-bar indicator (interai-hub@`0f39546`, `0f7ea41`).

### 8. Exception handler stack (Apr 27)

- **Ported from OperatorHub** as `AgentHubHelpers` project — `Logger`, `AppPaths`, `AppSettings`, `VerInfo`, `UnhandledExceptionManager`, `HandledExceptionManager`, `ExceptionDialog`, `BugReporting` (interai-hub@`521b951`, `028071f`).
- **Activated in `Sub Main`** — `AddHandler()` runs before `OpenPresenter()` (interai-hub@`25099ab`).
- **Report-a-Bug button** in `grpControls` opens GitHub Issues with auto-filled body (version, OS, module GUID, log path).
- **Email path stripped** — replaced with public GitHub Issues URL baked in via `BugReporting.BugReportUrl`.

### 9. Licensing system (Apr 27)

- **ECDSA P-256 signed keys** with public key embedded in binary, private key out-of-repo (interai-hub@`336a5fc`).
- **30-day trial tracker** with registry + AppData defense-in-depth (interai-hub@`bba8f1f`).
- **`frmRegister`** — paste-and-activate modal dialog (interai-hub@`063fdb4`).
- **Degraded mode**: 10-second delay before each LLM dispatch when expired (interai-hub@`bf29ce8`).
- **`LicenseTool`** console exe — maintainer-only key generator (in solution, NOT shipped).

### 10. Public release + onboarding (Apr 27 → 29)

- **First public release v1.0.3.1** — `setup.exe`, manifest, all binaries committed to `dgplugge/interai-hub-clickonce` (clickonce@`23e4d72`).
- **`Setup-InterAI-Hub.ps1`** — interactive 4-provider setup script (clickonce@`b95abb8`).
- **`docs/QuickStart.md`** + **`docs/ApiKeys.md`** — public onboarding docs.

### 11. Cross-cutting docs and testing

- **AICP Viewer** filters, search, badges, keyboard shortcuts, auto-refresh (`8a3062a`, `57dc9a0`, `cf708a2`).
- **Hub health dashboard + CLI** (`ddf7696`).
- **ACAL round-trip verifier** with compression ratio and field mismatch detection (`7b3845e`).
- **Trident + Lumen onboarding** (Gemini, Mistral providers) (`ba52800`).
- **Mismatch v2 game** designed by 6-agent team across 5 rounds — `notes/games/mismatch.md` (`30c81f3`).
- **Hub config persistence to AppData** so API keys survive rebuilds (`52ae9e3`, `18cfd90`).

---

## Open enhancements — priority ordered

Priorities reflect "what unblocks real use vs. what's nice-to-have." Time estimates are at the recent sprint pace (with Pharos as Lead Coder).

### Tier 1 — Validation work, should happen before more coding

| # | Item | Estimate | Why this priority |
|---|---|---|---|
| 1 | **Real son dry-run** | 30 min – 2 hr (mostly his time) | The entire onboarding flow built so far is unvalidated. One real first-time install will surface things no design review catches |
| 2 | **Lodestar's existing docs** — find them and fold into `docs/` | 30 min once located | Referenced twice; finishing the public doc set means knowing what they cover |

### Tier 2 — Polish that makes the public release look complete

| # | Item | Estimate | Why |
|---|---|---|---|
| 3 | **GitHub Pages** for `interai-hub-clickonce` | 30–60 min | `dgplugge.github.io/interai-hub-clickonce/` — proper landing site instead of a README. Also unblocks ClickOnce auto-update via a stable HTTPS URL later |
| 4 | **Embedded first-run wizard inside the Hub** (replaces PowerShell script for non-terminal users) | 3–4 hr | Best UX. Same flow as `Setup-InterAI-Hub.ps1` but inside the app. Son never touches a terminal |
| 5 | **README screenshots + CHANGELOG.md** in the public repo | 1 hr | Cold-finder confidence boost |

### Tier 3 — Hub team quality

| # | Item | Estimate | Why |
|---|---|---|---|
| 6 | **Card-tightening for SpinDrift** (chronic non-delivery — 4+ rounds) and **Lodestar** (off-topic abstention preamble) | 1–2 hr | Hub rounds get noisy when these tics fire; tighter card text may bite |
| 7 | **o3-mini reasoning-token investigation** (Forge empty 2048-token responses) | 1–3 hr depending on root cause | Forge currently unreliable when his slice is critical-path under RAG-on |
| 8 | **Trident Gemini client truncation** (kernel item — `MSG-0155 R5`) | 1–2 hr | Old issue; possibly already self-resolved (canary round was clean) but worth verifying |

### Tier 4 — Mid-priority feature work

| # | Item | Estimate | Why |
|---|---|---|---|
| 9 | **Mismatch v3** — paused per MSG-0180 with 9 design questions answered awaiting overrides | 1–2 hr | Demo polish, not core. Resume when a creative session is wanted |
| 10 | **forms-in-presenter cleanup** — move `frmCostLedger` from Presenter to View | 4 hr | MVP architecture hygiene; testability of Presenter |
| 11 | **Project-scoped kernel injection in the Hub** | 2–3 hr | New as of 2026-04-29. Establish project→kernel mapping; in `BuildSystemPrompt`, prepend the active project's kernel preamble before the agent card. Order: kernel → card → journal → RAG → user message |
| 12 | **mJournalContext refresh on project switch** | 1 hr | Currently ships pre-loaded cross-project context on first dispatch after switch |
| 13 | **Sync-to-deploy for `summaries/` directory** | 1–2 hr | Journal writes sync to `aicp-journals` deploy repo; summaries are still local |

### Tier 5 — Future-version / aspirational

| # | Item | Estimate | Why deferred |
|---|---|---|---|
| 14 | **Online license activation (Phase 2)** — Cloudflare Worker / Vercel function | 3–5 days | Only needed if license abuse appears. Current Phase 1 is offline-perpetual |
| 15 | **Subscription billing (Phase 2.5)** | +2–3 days on top of #14 | Same gating |
| 16 | **Third-party licensing SaaS** (Cryptlex / LicenseSpring / KeyGen) | 1–2 days integration | Only if self-hosted ops > $30–100/mo SaaS cost |
| 17 | **Inter-agent language** (compression / shorthand for round transcripts) | 5–10 days | Shelved 2026-04-25 after the team round showed protocol-vs-encoding ambiguity. Future-version material |
| 18 | **Context Kernel update protocol** — Hub writes learnings back into kernel STATE/MEMORY (PROPOSED) | 2–3 days | Architectural. Loader reads; nothing writes. Lodestar's design item |
| 19 | **CBOR compaction** for thread summaries | 1 day | Explicitly deferred in Slice 8.5; JSON works fine for now |
| 20 | **Auto-compact on threshold** | 1 day | `compact_due` is surfaced; `/compact` still requires explicit call |
| 21 | **End-to-end integration test** — full dispatch → validator → compactor → summary | 1 day | Per-module covered; full-round pytest doesn't exist |

---

## What's currently project-scoped vs. not

A snapshot of the prompt-assembly stack as of 2026-04-29:

| Layer | Project-scoped? | Where it lives | Injected by Hub on dispatch? |
|---|---|---|---|
| Kernel (project-level prompt prefix) | Conceptually yes, but **not auto-injected by the Hub today** | `interai-protocol/kernels/<name>.md` | ❌ No. Hub's "View Kernel..." opens in Notepad. Python API's `/dispatch?kernel=` route is unused by the Hub broadcast |
| Agent cards | No (correctly — agent-scoped) | `agents/<name>.md` | ✅ Yes, fetched per agent and prepended to that agent's system prompt |
| RAG prefix | ✅ Yes (shipped 2026-04-27) | SQLite `chunk_index`, project column | ✅ Yes when Include RAG context checkbox is on |
| Journal context (`mJournalContext`) | ❌ Cross-project — `LoadJournalContext` walks all known project dirs | Built once at session start | First dispatch only (when history empty) |

**Architectural intent (Don's stated mental model, 2026-04-29):** kernels describe project-level prompt context; agent cards are appended per-agent. Half implemented today: the agent half is correct; the kernel half is missing the Hub-broadcast wiring (item #11 above).

---

## Brainstorm items — consolidated catalog

From `notes/brainstorm.md`. Each entry's status as of 2026-04-29.

### Hub status checks from a phone (posted 2026-04-24)

WhatsApp / SMS / Telegram / private web URL. Read-only first; later `pause`, `resume`, `generate <project>` commands behind auth. Cheapest v1: a `GET /hub-status` endpoint paired with a Cloudflare tunnel — Don bookmarks the URL on his phone. Telegram bot v2 is a richer 3-day build. WhatsApp Business v3 is the most setup-heavy.

**Adjacent idea worth flagging:** push-style alerts (Hub proactively notifies on budget-gate fires, dispatch failures, scheduler events). May be more valuable than pull-based status checks.

**Status:** open. ~2 days for v1, ~3 days for v2.

### Project-scoped rag-prefix (posted 2026-04-26)

✅ **SHIPPED** as the project dropdown 2026-04-27 (interai-hub@`0f39546`). Brainstorm note can be archived.

### MVP architecture violation: frmCostLedger lives in Presenter project (posted 2026-04-26)

The Model-View-Presenter split is broken by `frmCostLedger.vb` living in `AgentHubPresenter` instead of `AgentHubView`. Fix: move file, add `OpenCostLedger()` on `AgentHubView`, remove `System.Windows.Forms` reference from `AgentHubPresenter.vbproj`. Rerun `AgentHubTests`.

**Status:** open. Same as enhancement item #10. ~4 hours.

### Creative-arc retrospective: Mismatch parlor game (posted 2026-04-27)

Post-mortem reference, not a future item. Two operational lessons captured to memory:
- Convergent rounds → Hourglass; divergent rounds → Round Robin.
- o3-mini reasoning models anchor on RAG-retrieved content; turn RAG off when Forge is critical-path.

---

## Bottom line

The InterAI Hub MVP is shipped (v1.0.3.1) and onboarding-equipped (Setup-InterAI-Hub.ps1, QuickStart.md, ApiKeys.md). The remaining work splits into:

- **Validation** (~3 items, mostly other people's time): items #1, #2.
- **Polish to look professional** (~3 items, ~5 hrs): items #3, #4, #5.
- **Hub team quality** (~3 items, ~4–7 hrs): items #6, #7, #8.
- **Feature carryover** (~5 items, ~9–11 hrs): items #9–#13.
- **Future-version stack** (~8 items): not before validation + polish lands.

If a single next step had to be picked: **#1 (real son dry-run)** costs nothing on the maintainer's side and could shape #4 (embedded wizard) priority dramatically. If the son sails through the PowerShell script, the embedded wizard is just polish; if he stumbles, embedded becomes higher priority.
