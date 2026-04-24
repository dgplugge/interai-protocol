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
