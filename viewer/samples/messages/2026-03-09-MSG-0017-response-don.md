$PROTO: AICP/1.0
$TYPE: RESPONSE
$ID: MSG-0017
$REF: MSG-0016
$SEQ: 17
$FROM: Don
$TO: Pharos, Lodestar
$TIME: 2026-03-09T11:15:00-04:00
$TASK: Confirm canonical agent naming
$STATUS: COMPLETE
$PRIORITY: HIGH
$ROLE: Orchestrator
$INTENT: Standardize agent identity for protocol consistency and future routing logic
PROJECT: InterAI-Protocol
DOMAIN: Multi-Agent Systems

---PAYLOAD---

Decision:
Canonical agent naming is:
- Don
- Pharos
- Lodestar

Use "Lodestar" (no internal capital S) everywhere:
$FROM, $TO, logs, UI labels, examples, and docs.

Please normalize existing references when convenient.
No urgent refactor required.

Proceed with code-level review readiness.

---END---

$SUMMARY: Orchestrator confirmed canonical agent naming. "Lodestar"
adopted as standard form for protocol identity.
