$PROTO: AICP/1.0
$TYPE: RESPONSE
$ID: SG-MSG-0020
$REF: SG-MSG-0019
$SEQ: 75
$FROM: Pharos
$TO: Don, Lodestar
$TIME: 2026-03-31T01:05:00-04:00
$TASK: Assess feedback capture options for Study Guide UI
$STATUS: COMPLETE
$ROLE: Lead Coder
$INTENT: Evaluate the three implementation options and recommend a path that aligns with existing infrastructure
PROJECT: StudyGuide
DOMAIN: AI-Assisted Learning

---PAYLOAD---

Don —

Good capture. In-context feedback is the right direction — it preserves the connection between what the user experienced and what they're commenting on, which manual collection loses.

ASSESSMENT OF OPTIONS:

1. GITHUB ISSUES (PREFILLED)
Pros: Zero backend needed. Button opens a prefilled GitHub issue URL with case study ID, question number, and a template body. Feedback lives in the same system as the code. Searchable, taggable, assignable.
Cons: Requires the user to have a GitHub account. Not ideal for non-technical users (Ben would be fine, but this limits scalability to other architecture students).
Verdict: Best for internal/team feedback. Not ideal as the primary user-facing mechanism.

2. N8N WEBHOOK INTEGRATION
Pros: Aligns with existing n8n infrastructure. Feedback POST goes to an n8n webhook that can route, log, or forward. No user account required. Can generate AICP messages from feedback automatically. Could trigger a review workflow.
Cons: Requires n8n to be running and accessible. Adds a dependency on the orchestration layer for a simple input form.
Verdict: Best long-term option. Natural fit with the AICP ecosystem. Can start simple (webhook receives JSON, logs to file) and grow into a routed workflow.

3. EMAIL-BASED SUBMISSION
Pros: Universal — every user has email. No accounts, no infrastructure.
Cons: Unstructured. Difficult to parse, tag, or route. Creates a manual processing burden. No connection to the AICP system without additional tooling.
Verdict: Fallback only. Use if the other options are unavailable.

RECOMMENDATION:

Start with Option 1 (GitHub Issues) for Ben's current testing cycle — it's zero implementation cost and gives us structured, trackable feedback immediately. When the n8n integration matures (Phase 2-3), add Option 2 as the primary feedback channel for broader users.

PROPOSED UI:

A small "Feedback" button at the bottom of each case study page. Clicking it opens a modal or inline form with:
- Case Study (auto-filled from page context)
- Question Number (optional dropdown)
- Feedback Type (too easy / too hard / unclear / inaccurate / other)
- Comment (free text)
- Submit button

For the GitHub Issues version, "Submit" constructs a prefilled URL:
```
https://github.com/dgplugge/interai-protocol/issues/new?title=Feedback:+CS3+Q5&body=Type:+too+easy%0AComment:+...&labels=study-guide-feedback
```

For the n8n version, "Submit" POSTs JSON to the feedback webhook.

NOTED: No implementation now. Captured for post-refinement work.

---END---
