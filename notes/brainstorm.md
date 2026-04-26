# Brainstorm Notes

Informal capture of ideas that aren't yet scoped slices. One section
per idea. Add newest at the bottom; don't edit older entries, just
respond to them below if revisiting.

---

## 2026-04-24 — Hub status checks from a phone (WhatsApp / other)

**Idea (Don):** remote status-check channel so Don can see what the Hub
is doing when he's away from the machine. First channel would probably
be WhatsApp, but the design should be pluggable so SMS, Telegram, Signal,
email, or a private web endpoint could slot in later.

**What counts as "status" worth reporting over phone:**

- Is the Python API up? (simple ping to `GET /`)
- Is the Hub up? (process check, or a heartbeat the Hub writes to the journal)
- Last journal entry: `$ID`, `$FROM`, `$TIME` — confirms writes are flowing.
- `messages_since_compact` per project — how close is the thread to a summary firing.
- `summary-due` state per project — is the scheduler about to act.
- Recent failures: OpenAI refusals, Gemini 429/503, Anthropic timeouts — anything from the dispatch error log in the last N minutes.
- Scheduler heartbeat: is the background task still alive, when did it last tick, what did it do.

**Read-only vs read-write:**

Start read-only. A `status` command returns a formatted summary of the
above. Later, optional commands like `pause`, `resume`, `generate <project>`
could trigger Hub actions — but that requires auth and confirmation that
a phone is a safe control surface for a multi-agent orchestration.

**Auth model (must decide before shipping):**

- Phone number whitelist (one entry: Don's number) — cheap, reasonable for single-user deploy.
- Shared secret in every message ("passcode: XXXX status") — simple, but phone displays leak it.
- Signed requests — correct but heavy.

**Plumbing options, cost/complexity ordered:**

1. **Email → IMAP poll.** Cheapest, no third-party API. Don emails a special
   mailbox; a poller watches inbox and replies. Works on any phone. Latency
   ~30s. No per-message cost.
2. **Telegram Bot API.** Free, zero-friction, excellent for structured
   replies with buttons. Bot token, webhook or long-poll. Downside: not the
   channel Don asked for.
3. **Twilio SMS.** ~$0.008/msg outbound. Works on every phone without an
   app. Well-trodden path. Paid.
4. **WhatsApp Business API.** Most complex — requires a business
   verification, a WhatsApp Business account, and typically a BSP
   (business solution provider) like Twilio or Meta Cloud API. Free-tier
   window (24h user-initiated messaging) is workable for status checks
   that Don kicks off. Not free to set up; ongoing cost is low.
5. **Private web endpoint with bookmarked URL.** Don just hits a URL on his
   phone browser. Requires the API to be reachable externally (tailscale,
   cloudflare tunnel, dynamic DNS, or deployed). Simplest technically if
   remote access is already solved.

**Cheapest viable v1:** a `GET /hub-status` endpoint (Python side) that
returns a one-screen JSON or plain-text summary, paired with a Cloudflare
tunnel or Tailscale link. Don bookmarks the URL on his phone. No new
protocol, no third-party integration. Two-day build.

**Richer v2:** Telegram bot. Don types `/status` or `/recent` and the bot
replies. Conversational, supports charts/images, free. Probably a
three-day build including auth.

**Richest v3:** WhatsApp Business via Twilio's API. Matches Don's stated
preference but carries the setup cost.

**Adjacent idea worth flagging:** a push channel — the Hub proactively
notifies Don when something interesting happens (budget-gate fires,
unrecoverable dispatch failure, scheduler generates a summary). That's
*alerts*, not *status checks*, and may be the more valuable feature —
easier to forget to pull than to push.

---

## 2026-04-26 — Project-scoped rag-prefix when the Hub broadcast doesn't carry AICP

**Observation (Don):** the viewer interface dispatches AICP messages
with a `$PROJECT` field, so the rag-prefix call knows which project's
SQLite chunk_index to query. The Hub broadcast UI doesn't use AICP —
Don pastes raw text. There's no `$PROJECT` to extract. Today,
`AgentHubPresenter.FetchRagContext` falls back to `Session.Project`,
defaulting to the hardcoded literal `"InterAI-Protocol"` if Session
hasn't set it. If Don ever runs a multi-project setup, the wrong
project's RAG could be pulled into a dispatch.

**Why this matters:**
- The chunk_index has a `project` column — retrieval is already
  isolated per project at the storage layer.
- The Hub session has a `Project` slot but no UI to set it; effectively
  always `"InterAI-Protocol"` today.
- As soon as a second project exists, the wrong-project RAG
  contamination is silent — the dispatch succeeds, the prefix block
  looks plausible, but the retrieved chunks are from the wrong corpus.

**Design options when this becomes a slice:**

1. **Project dropdown in the Hub UI.** Mirror the viewer interface.
   Operator picks the active project; Hub stores it in `Session.Project`
   and feeds it through to `FetchRagContext` (already wired). Most
   visible to the operator.
2. **Read from the loaded kernel.** Each kernel file targets a
   project (`kernel-mvp-build.md` → `InterAI-Protocol`). If the Hub
   tracks the active kernel, the project derives automatically. Fewer
   knobs, more magic.
3. **AICP framing on Hub broadcasts.** Make the Hub render an AICP
   envelope around Don's pasted text, with `$PROJECT` from a UI field.
   Largest change, gives the Hub broadcasts the same rigor as viewer
   dispatches — and a cleaner journal trail.
4. **Stay defaulted, surface a warning.** Keep
   `If(Session.Project, "InterAI-Protocol")`, but log a warning whenever
   a dispatch hits the fallback so the silent-wrong-project case becomes
   noisy.

**Recommendation:** Option 1 (dropdown) is the cheapest durable fix
and parallels the viewer. Option 4 is a one-line guardrail to add now
even before the dropdown lands. Option 3 is a real architectural
improvement worth queueing once the project list grows past one.

---

## 2026-04-26 — MVP architecture violation: frmCostLedger lives in the Presenter project

**Observation (Don):** the Model-View-Presenter split is broken by
`frmCostLedger.vb` living inside the `AgentHubPresenter` project
instead of `AgentHubView`. In strict MVP, all WinForms artifacts
(forms, designers, controls) belong in the View project; the Presenter
holds the orchestration logic and calls `view.OpenForm()` to surface UI.

**Current state:**
- `AgentHubPresenter/frmCostLedger.vb` — form definition lives here.
- `AgentHubView/frmAgentHub.vb`, `frmAgentSettings.vb`, `frmAgentCard.vb`
  — these correctly live in the View project.
- Result: the Presenter project compiles WinForms code, which couples
  the layer that should be UI-agnostic to System.Windows.Forms.

**Why this matters:**
- The Presenter loses its testability promise. Today
  `AgentHubTests` covers `BudgetGateService` and `LedgerAggregateCache`
  cleanly; if more Presenter logic gets paired with forms, that
  testability degrades.
- New View frameworks (WPF, WinUI, web) would require disentangling
  the Presenter from WinForms, harder than fixing it now.
- It's a discoverability tax for new contributors — the convention
  is "forms in View" everywhere except this one file.

**Down-the-road fix:**

1. Move `frmCostLedger.vb` and any associated `.Designer.vb` /
   `.resx` from `AgentHubPresenter/` to `AgentHubView/`.
2. Add a corresponding `OpenCostLedger()` method on `AgentHubView`
   that constructs and shows the form.
3. The Presenter calls `AgentHubView.OpenCostLedger(...)` with whatever
   data shape the form needs, instead of newing up the form directly.
4. Remove `System.Windows.Forms` reference from
   `AgentHubPresenter.vbproj` and verify the project still builds —
   the failing references will surface any other forms/controls
   leaking into the Presenter layer.
5. Re-run `AgentHubTests` (currently 24/24) — should still pass.

**Sizing:** half-day at most for the file move and the indirection.
Worth bundling with any other MVP-discipline cleanup; not urgent
enough to break in front of MVP shipping.
