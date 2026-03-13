$PROTO: AICP/1.0
$TYPE: RESPONSE
$ID: MSG-0043
$REF: MSG-0042
$SEQ: 45
$FROM: Pharos
$TO: Lodestar, Don
$TIME: 2026-03-10T18:10:00-04:00
$TASK: Architectural review of n8n AICP Ingress Parser and Switch routing plan
$STATUS: COMPLETE
$PRIORITY: HIGH
$ROLE: Architect
$INTENT: Provide concrete implementation guidance for Switch routing slice based on reviewed artifacts
PROJECT: InterAI-Protocol
DOMAIN: Multi-Agent Systems
---PAYLOAD---
LodeStar, Don —

I have reviewed all four artifacts. The parser is solid work — clean separation of concerns, correct normalization, and the routing resolution is exactly the right abstraction. Below is my review on each of your five questions, plus specific code changes.

========================================
REVIEW 1: SCHEMA COMPLETENESS BEFORE SWITCH
========================================

The parsed JSON output is 90% ready. Three additions before you wire the Switch:

A. Add a routing namespace object

Currently route sits at top level ($json.route). Nest it under a routing object so future fields (registry, fallback, fan-out) have a clean home. Replace the current route/ack block in the Code node with:

  result.routing = {
    targets: result.normalized.to,
    route: route,
    isMulti: targets.length > 1,
    handlerMode: targets.length > 1 ? 'multi' : 'single',
    registry: null
  };

The Switch node keys on $json.routing.route instead of $json.route. This costs nothing now and saves a migration later when registry-aware routing populates routing.registry.

B. Add a custom object for non-$ headers

The parser correctly stores PROJECT and DOMAIN in headers{} and extracts them into normalized. But any future custom fields (CALLBACK, TAGS, THREAD) would be stranded in headers{} with no structured access. After the normalized block, add:

  result.custom = {};
  for (const [key, value] of Object.entries(result.headers)) {
    if (!key.startsWith('$')) {
      result.custom[key] = value;
    }
  }

Now result.custom = { PROJECT: "InterAI-Protocol", DOMAIN: "Multi-Agent Systems" } and future custom fields appear automatically without parser changes.

C. Add a validation object

Before the Switch makes routing decisions, downstream nodes should know if the message is well-formed:

  result.validation = {
    valid: true,
    errors: []
  };
  if (!result.normalized.proto) {
    result.validation.valid = false;
    result.validation.errors.push('Missing $PROTO');
  }
  if (!result.normalized.id) {
    result.validation.valid = false;
    result.validation.errors.push('Missing $ID');
  }
  if (!result.normalized.type) {
    result.validation.valid = false;
    result.validation.errors.push('Missing $TYPE');
  }
  if (result.normalized.to.length === 0) {
    result.validation.valid = false;
    result.validation.errors.push('Missing or empty $TO');
  }

The Switch or a pre-Switch IF node can check $json.validation.valid to short-circuit malformed messages to an error branch before routing.

========================================
REVIEW 2: PARSING EDGE CASES TO HANDLE NOW
========================================

The parser handles the main cases well. Four edge cases worth fixing before Switch locks in the contract:

A. Blank lines between headers — Currently the regex skips blank lines before ---PAYLOAD--- because they do not match the header pattern. This is correct — no data loss. No fix needed.

B. Multiline header values — AICP does not currently define multiline headers, but if $INTENT ever wraps to a second line, the parser will silently drop the continuation. This is acceptable for now. Flag it as a known limitation.

C. Duplicate headers — If a message has $TO: Pharos twice, the second value overwrites the first silently. Add a warning to validation.errors if a key is seen twice.

D. route_don is missing from the Switch plan — The parser has a route_don case (for messages addressed to Don), but the Switch plan only lists 4 branches. Add route_don as the 5th branch — this is the route-back-to-orchestrator path, and it becomes the return channel when agents respond to Don through n8n. Stub behavior: targetResolved=Don, handlerMode=orchestrator, deliveryMethod=viewer-relay.

========================================
REVIEW 3: ROUTE STRING AS SWITCH CONTRACT
========================================

Yes — $json.routing.route (with the namespace change from Review 1) is the correct Switch key. Reasons:

- It is a clean string enum with predictable values
- It is computed in one place (the Code node) from normalized data
- Downstream branches do not need to re-parse $TO or do case logic
- When registry-aware routing arrives, you update the Code node resolution logic — the Switch values do not change, only HOW they are computed

The only adjustment: use the routing namespace ($json.routing.route) so the Switch contract reads as "I route on the routing decision" not "I route on a top-level field."

========================================
REVIEW 4: SET NODES AS BRANCH STUBS
========================================

The Set node approach is correct. Two refinements:

A. Merge, do not replace

Use Edit Fields (Set) node with Keep Only Set Fields turned OFF. Each stub should ADD its fields to the existing parsed JSON, not replace it. The full parsed object must flow through to Respond to Webhook. Each stub sets:

  route_pharos:    routing.targetResolved=Pharos,      routing.handlerMode=single,       routing.handlerStatus=stub
  route_lodestar:  routing.targetResolved=Lodestar,     routing.handlerMode=single,       routing.handlerStatus=stub
  route_multi:     routing.targetResolved=Pharos+Lodestar, routing.handlerMode=multi,     routing.handlerStatus=stub
  route_don:       routing.targetResolved=Don,           routing.handlerMode=orchestrator, routing.handlerStatus=stub
  route_unknown:   routing.targetResolved=Unknown,       routing.handlerMode=unresolved,   routing.handlerStatus=error

Adding routing.handlerStatus=stub means when you later replace a stub with a live HTTP Request node, you change that field to live and downstream logic (logging, response formatting) can adapt without knowing which branches are live vs stubbed.

B. Merge node before Respond to Webhook

All 5 branches must converge through a Merge node (mode: merge by position or passthrough) before Respond to Webhook. Otherwise n8n cannot determine which branch output to return.

Final workflow shape for this slice:

  Webhook -> Code -> Switch -> [5 branches] -> Merge -> Respond to Webhook

  Where Switch fans out to:
    route_pharos    -> Set Pharos Target    -> Merge
    route_lodestar  -> Set Lodestar Target  -> Merge
    route_multi     -> Set Multi Target     -> Merge
    route_don       -> Set Don Target       -> Merge
    route_unknown   -> Set Unknown Target   -> Merge

========================================
REVIEW 5: BRIDGE TO REGISTRY-AWARE ROUTING
========================================

The bridge path from current Switch routing to registry-aware routing is clean:

Phase 1 (this slice): Static Switch routing
  Code computes route from hardcoded if/else on $TO.
  Switch branches on route string. Stubs return mock responses.

Phase 2 (Slice 12): Registry lookup node
  Insert a Function node between Code and Switch:
  Code -> Registry Lookup -> Switch -> branches -> Merge -> Respond

  The Registry Lookup node reads agent-registry.json, resolves each target name to endpoint plus capabilities, populates routing.registry with resolved agent metadata. Does NOT change routing.route — the Switch contract stays the same.

  agent-registry.json format:
  {
    "agents": {
      "Pharos": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "endpoint": "https://api.anthropic.com/v1/messages",
        "capabilities": ["architecture","code-review","protocol-design"],
        "active": true
      },
      "Lodestar": {
        "provider": "openai",
        "model": "gpt-4o",
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "capabilities": ["systems-design","workflow-architecture","integration"],
        "active": true
      }
    }
  }

Phase 3 (future): Dynamic routing
  The Code node routing logic evolves from name-based to capability-based.
  The Switch values remain the same — only the resolution logic changes upstream.

Key principle: the Switch contract (route_pharos, route_lodestar, etc.) is STABLE across all three phases. What changes is how route values are computed (hardcoded -> registry-resolved -> capability-matched), not what the Switch branches on.

========================================
SUMMARY OF RECOMMENDED CHANGES
========================================

For the Code node (before Switch slice):
  1. Add routing namespace object (replaces top-level route)
  2. Add custom object for non-$ headers
  3. Add validation object for required field checks

For the Switch slice:
  4. Switch keys on $json.routing.route
  5. Five branches: route_pharos, route_lodestar, route_multi, route_don, route_unknown
  6. Each stub uses Edit Fields with Keep Only Set Fields OFF
  7. Each stub sets routing.targetResolved, routing.handlerMode, routing.handlerStatus
  8. Merge node before Respond to Webhook
  9. Update Respond to Webhook to return routing.route, routing.targetResolved, routing.handlerStatus

Success criteria for this slice:
  - POST $TO:Pharos -> route_pharos, targetResolved=Pharos, handlerStatus=stub
  - POST $TO:Lodestar -> route_lodestar, targetResolved=Lodestar, handlerStatus=stub
  - POST $TO:Pharos,Lodestar -> route_multi, targetResolved=Pharos+Lodestar, handlerStatus=stub
  - POST $TO:Don -> route_don, targetResolved=Don, handlerStatus=orchestrator
  - POST $TO:Aurora -> route_unknown, targetResolved=Unknown, handlerStatus=error
  - POST missing $ID -> validation.valid=false

This is clean, testable, and upgrades to live agents without rewiring.

— Pharos
---END---
