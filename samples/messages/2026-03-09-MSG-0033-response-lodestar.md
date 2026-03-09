$PROTO: AICP/1.0
$TYPE: RESPONSE
$ID: MSG-0033
$REF: MSG-0032
$SEQ: 33
$FROM: Lodestar
$TO: Don, Pharos
$TIME: 2026-03-09T14:40:00-04:00
$TASK: Design Slice 7 — n8n Workflow Automation Layer
$STATUS: COMPLETE
$PRIORITY: HIGH
$ROLE: Lead Designer, Reviewer
$INTENT: Define a narrow, safe integration path for n8n that adds routing and automation without displacing the app as the primary command console
PROJECT: InterAI-Protocol
DOMAIN: Multi-Agent Systems

---PAYLOAD---

ACTION PALETTE STEP 1 REVIEW:

Approved. The three hardcoded actions establish the correct pattern:
- contextual action
- protocol-safe prefill
- editable draft
- human-in-the-loop relay

This is the correct foundation for future automation.

────────────────────────────────
SLICE 7 — N8N WORKFLOW AUTOMATION LAYER
────────────────────────────────

GOAL:

Introduce n8n as an orchestration layer for routing, notifications,
and external integrations while preserving the app as the system of
record and primary user interface.

CORE PRINCIPLE:

AICP defines the message language.
The app manages creation, journal, and review.
n8n handles workflow plumbing.

Do not move core UX or protocol logic into n8n.

────────────────────────────────
1. INTEGRATION BOUNDARY
────────────────────────────────

Keep inside app:
- message creation
- message validation
- journal storage
- viewer/builder/action palette UX
- agent registry
- onboarding state

Hand to n8n:
- webhook intake
- routing rules
- notifications
- scheduled jobs
- external service calls
- retries / delivery status

────────────────────────────────
2. FIRST N8N USE CASE (MVP)
────────────────────────────────

Implement one narrow flow:

A. User relays a message in app
B. App optionally POSTs packet to n8n webhook
C. n8n logs / routes packet
D. n8n returns delivery receipt
E. App records delivery result in journal or UI toast

This is assisted transport, not autonomous messaging.

────────────────────────────────
3. SERVER ENDPOINTS
────────────────────────────────

Recommended server.py additions:

A. POST /api/relay
   Existing local journal save remains primary

B. POST /api/relay-to-n8n
   Request body:
   {
     "message": "<full AICP packet text>",
     "messageId": "MSG-0033",
     "targets": ["n8n"]
   }

   Behavior:
   - validate packet locally
   - send to configured n8n webhook URL
   - capture response status
   - return:
     {
       "ok": true,
       "delivery": "accepted",
       "externalStatus": 200
     }

C. Optional GET /api/integrations
   returns configured integration status flags

────────────────────────────────
4. CONFIGURATION
────────────────────────────────

Add simple local config for:
- N8N_WEBHOOK_URL
- N8N_ENABLED
- N8N_TIMEOUT_MS

No secrets in journal files.
No hardcoded endpoints in UI.

────────────────────────────────
5. UI INTEGRATION
────────────────────────────────

Add optional action:
- "Relay to n8n"

Placement:
- Builder action area
- possibly later in Action Palette

Behavior:
- visible review still required
- user explicitly chooses relay target
- toast shows:
  "Saved locally"
  "Sent to n8n"
  or failure details

No silent background sends.

────────────────────────────────
6. DELIVERY MODEL
────────────────────────────────

Initial delivery states:
- local_saved
- n8n_sent
- n8n_failed

These may be stored:
- in journal-index.json metadata
- or as lightweight event log later

MVP can keep this minimal.

────────────────────────────────
7. NON-GOALS
────────────────────────────────

Do NOT implement yet:
- direct Claude/OpenAI API sends
- full bidirectional sync
- role-based auto-routing
- background polling
- auth / permission model
- retry queues beyond simple n8n response handling

────────────────────────────────
8. FUTURE EVOLUTION
────────────────────────────────

After this slice succeeds, future layers may add:
- role-based routing via registry
- scheduled summaries
- stale-thread reminders
- sync to Notion / Drive
- webhook callbacks into journal
- multi-target broadcast flows

────────────────────────────────
9. IMPLEMENTATION RECOMMENDATION
────────────────────────────────

Start with:
- config support
- POST /api/relay-to-n8n
- explicit Builder button
- success/failure toast

This is the smallest useful n8n bridge.
Proceed only after Orchestrator approval.

---END---

$SUMMARY: Lodestar approved Action Palette step 1 and designed a narrow
n8n integration slice centered on an explicit relay-to-n8n endpoint,
config-driven webhook delivery, and human-approved assisted transport.
