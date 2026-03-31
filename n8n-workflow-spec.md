# n8n Workflow Specification: AICP Ingress Parser

Build an n8n workflow JSON file that implements the AICP (AI Communication Protocol) message ingress, parsing, routing, and response system. The workflow receives raw AICP text protocol packets via webhook, parses them, routes by target agent, and returns a structured JSON response.

---

## Workflow Name

`AICP Ingress Parser`

## Workflow Shape

```
Webhook -> Code (Parser) -> Switch -> [5 Branch Stubs] -> Merge -> Respond to Webhook
```

Detailed fan-out:

```
Webhook
  -> Code (AICP Parser)
    -> Switch (Route by Agent)
      -> Output 0: Set Pharos Target    -> Merge
      -> Output 1: Set Lodestar Target  -> Merge
      -> Output 2: Set Multi Target     -> Merge
      -> Output 3: Set Don Target       -> Merge
      -> Output 4: Set Unknown Target   -> Merge
        -> Respond to Webhook
```

---

## Node 1: Webhook

- **Type:** Webhook
- **HTTP Method:** POST
- **Path:** `/aicp-ingress`
- **Response Mode:** `responseNode` (response handled by Respond to Webhook node)
- **Raw Body:** The webhook receives the raw AICP message text in the request body

---

## Node 2: Code (AICP Parser)

- **Type:** Code (JavaScript)
- **Mode:** Run Once for All Items
- **Purpose:** Parse the raw AICP text packet into structured JSON with headers, normalized fields, custom fields, routing, and validation

### JavaScript Code

```javascript
// AICP Ingress Parser — n8n Code Node
// Parses raw AICP/1.0 text protocol packets into structured JSON

const rawBody = $input.first().json.body;
const raw = typeof rawBody === 'string' ? rawBody : JSON.stringify(rawBody);

// Normalize CRLF
const text = raw.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
const lines = text.split('\n');

// --- Phase 1: Split headers from payload ---
const headers = {};
const payloadLines = [];
let inPayload = false;

for (const line of lines) {
  const trimmed = line.trim();

  if (trimmed === '---PAYLOAD---') {
    inPayload = true;
    continue;
  }
  if (trimmed === '---END---') {
    inPayload = false;
    continue;
  }

  if (inPayload) {
    payloadLines.push(line);
    continue;
  }

  // Parse key: value pairs (supports $KEY and plain KEY with spaces/hyphens)
  const kvMatch = trimmed.match(/^(\$?[A-Za-z][A-Za-z0-9_ .\-]*?)\s*:\s*(.*)$/);
  if (kvMatch) {
    const key = kvMatch[1].trim();
    const value = kvMatch[2].trim();
    headers[key] = value;
  }
}

const payloadText = payloadLines.join('\n').replace(/^\n+|\n+$/g, '');

// --- Phase 2: Normalize canonical fields ---
const toRaw = headers['$TO'] || '';
const targets = toRaw.split(',').map(t => t.trim()).filter(Boolean);

const normalized = {
  proto:    headers['$PROTO'] || '',
  type:     headers['$TYPE'] || '',
  id:       headers['$ID'] || '',
  ref:      headers['$REF'] || null,
  seq:      headers['$SEQ'] ? parseInt(headers['$SEQ'], 10) : null,
  from:     headers['$FROM'] || '',
  to:       targets,
  time:     headers['$TIME'] || '',
  task:     headers['$TASK'] || '',
  status:   headers['$STATUS'] || '',
  priority: headers['$PRIORITY'] || null,
  role:     headers['$ROLE'] || null,
  intent:   headers['$INTENT'] || null
};

// --- Phase 3: Extract custom (non-$) headers ---
const custom = {};
for (const [key, value] of Object.entries(headers)) {
  if (!key.startsWith('$')) {
    custom[key] = value;
  }
}

// --- Phase 4: Determine route from $TO ---
let route = 'route_unknown';
const lower = targets.map(t => t.toLowerCase());

if (targets.length > 1) {
  route = 'route_multi';
} else if (lower.includes('pharos')) {
  route = 'route_pharos';
} else if (lower.includes('lodestar')) {
  route = 'route_lodestar';
} else if (lower.includes('don')) {
  route = 'route_don';
}

// --- Phase 5: Build routing namespace ---
const routing = {
  targets: targets,
  route: route,
  isMulti: targets.length > 1,
  handlerMode: targets.length > 1 ? 'multi' : 'single',
  registry: null  // placeholder for Phase 2 registry-aware routing
};

// --- Phase 6: Validate required fields ---
const validation = {
  valid: true,
  errors: []
};

if (!normalized.proto) {
  validation.valid = false;
  validation.errors.push('Missing $PROTO');
}
if (!normalized.id) {
  validation.valid = false;
  validation.errors.push('Missing $ID');
}
if (!normalized.type) {
  validation.valid = false;
  validation.errors.push('Missing $TYPE');
}
if (targets.length === 0) {
  validation.valid = false;
  validation.errors.push('Missing or empty $TO');
}

// --- Phase 7: Build acknowledgment ---
const ack = {
  id: normalized.id,
  route: routing.route,
  received: new Date().toISOString()
};

// --- Assemble result ---
const result = {
  headers,
  normalized,
  custom,
  payloadLines,
  payloadText,
  routing,
  validation,
  ack
};

return [{ json: result }];
```

---

## Node 3: Switch (Route by Agent)

- **Type:** Switch
- **Mode:** Rules
- **Route on field:** `{{ $json.routing.route }}`
- **Data Type:** String
- **Rules (5 outputs):**

| Output | Rule                        | Output Name      |
|--------|-----------------------------|------------------|
| 0      | equals `route_pharos`       | route_pharos     |
| 1      | equals `route_lodestar`     | route_lodestar   |
| 2      | equals `route_multi`        | route_multi      |
| 3      | equals `route_don`          | route_don        |
| 4      | (fallback/default output)   | route_unknown    |

---

## Nodes 4a–4e: Set/Edit Fields (Branch Stubs)

Each branch gets an **Edit Fields (Set)** node. Critical configuration:

- **Mode:** Manual Mapping
- **Keep Only Set Fields:** OFF (merge with existing data, do NOT replace)
- **Action:** These nodes ADD fields to the existing parsed JSON flowing through

### Node 4a: Set Pharos Target

| Field                     | Value          |
|---------------------------|----------------|
| `routing.targetResolved`  | `Pharos`       |
| `routing.handlerMode`     | `single`       |
| `routing.handlerStatus`   | `stub`         |

### Node 4b: Set Lodestar Target

| Field                     | Value          |
|---------------------------|----------------|
| `routing.targetResolved`  | `Lodestar`     |
| `routing.handlerMode`     | `single`       |
| `routing.handlerStatus`   | `stub`         |

### Node 4c: Set Multi Target

| Field                     | Value              |
|---------------------------|--------------------|
| `routing.targetResolved`  | `Pharos+Lodestar`  |
| `routing.handlerMode`     | `multi`            |
| `routing.handlerStatus`   | `stub`             |

### Node 4d: Set Don Target

| Field                     | Value          |
|---------------------------|----------------|
| `routing.targetResolved`  | `Don`          |
| `routing.handlerMode`     | `orchestrator` |
| `routing.handlerStatus`   | `stub`         |

### Node 4e: Set Unknown Target

| Field                     | Value          |
|---------------------------|----------------|
| `routing.targetResolved`  | `Unknown`      |
| `routing.handlerMode`     | `unresolved`   |
| `routing.handlerStatus`   | `error`        |

---

## Node 5: Merge

- **Type:** Merge
- **Mode:** Append (all branch outputs converge here)
- **Purpose:** Collect the single output from whichever branch was activated by the Switch

---

## Node 6: Respond to Webhook

- **Type:** Respond to Webhook
- **Response Code:** 200
- **Response Body (expression):**

```json
{
  "ok": true,
  "delivery": "accepted",
  "id": "{{ $json.normalized.id }}",
  "route": "{{ $json.routing.route }}",
  "targetResolved": "{{ $json.routing.targetResolved }}",
  "handlerMode": "{{ $json.routing.handlerMode }}",
  "handlerStatus": "{{ $json.routing.handlerStatus }}",
  "validation": {
    "valid": "{{ $json.validation.valid }}",
    "errors": "{{ $json.validation.errors }}"
  }
}
```

---

## Node Connections Summary

```
Webhook                 -> Code (AICP Parser)
Code (AICP Parser)      -> Switch (Route by Agent)
Switch output 0         -> Set Pharos Target
Switch output 1         -> Set Lodestar Target
Switch output 2         -> Set Multi Target
Switch output 3         -> Set Don Target
Switch output 4         -> Set Unknown Target
Set Pharos Target       -> Merge
Set Lodestar Target     -> Merge
Set Multi Target        -> Merge
Set Don Target          -> Merge
Set Unknown Target      -> Merge
Merge                   -> Respond to Webhook
```

---

## Test Cases

Use these POST bodies against the webhook to verify routing:

### Test 1: Route to Pharos

```
$PROTO: AICP/1.0
$TYPE: REQUEST
$ID: MSG-TEST-001
$FROM: Don
$TO: Pharos
$TIME: 2026-03-27T12:00:00-04:00
$TASK: Test routing to Pharos
$STATUS: PENDING
PROJECT: InterAI-Protocol
---PAYLOAD---
This is a test message routed to Pharos.
---END---
```

**Expected:** `route: route_pharos`, `targetResolved: Pharos`, `handlerStatus: stub`

### Test 2: Route to Lodestar

```
$PROTO: AICP/1.0
$TYPE: REQUEST
$ID: MSG-TEST-002
$FROM: Don
$TO: Lodestar
$TIME: 2026-03-27T12:00:00-04:00
$TASK: Test routing to Lodestar
$STATUS: PENDING
PROJECT: InterAI-Protocol
---PAYLOAD---
This is a test message routed to Lodestar.
---END---
```

**Expected:** `route: route_lodestar`, `targetResolved: Lodestar`, `handlerStatus: stub`

### Test 3: Multi-target route

```
$PROTO: AICP/1.0
$TYPE: REQUEST
$ID: MSG-TEST-003
$FROM: Don
$TO: Pharos, Lodestar
$TIME: 2026-03-27T12:00:00-04:00
$TASK: Test multi-target routing
$STATUS: PENDING
PROJECT: InterAI-Protocol
---PAYLOAD---
This is a test message routed to both agents.
---END---
```

**Expected:** `route: route_multi`, `targetResolved: Pharos+Lodestar`, `handlerStatus: stub`

### Test 4: Route to Don (orchestrator)

```
$PROTO: AICP/1.0
$TYPE: RESPONSE
$ID: MSG-TEST-004
$FROM: Pharos
$TO: Don
$TIME: 2026-03-27T12:00:00-04:00
$TASK: Test orchestrator route
$STATUS: COMPLETE
PROJECT: InterAI-Protocol
---PAYLOAD---
Response routed back to orchestrator.
---END---
```

**Expected:** `route: route_don`, `targetResolved: Don`, `handlerMode: orchestrator`, `handlerStatus: stub`

### Test 5: Unknown target

```
$PROTO: AICP/1.0
$TYPE: REQUEST
$ID: MSG-TEST-005
$FROM: Don
$TO: Aurora
$TIME: 2026-03-27T12:00:00-04:00
$TASK: Test unknown agent routing
$STATUS: PENDING
PROJECT: InterAI-Protocol
---PAYLOAD---
This target is not in the registry.
---END---
```

**Expected:** `route: route_unknown`, `targetResolved: Unknown`, `handlerStatus: error`

### Test 6: Validation failure (missing $ID)

```
$PROTO: AICP/1.0
$TYPE: REQUEST
$FROM: Don
$TO: Pharos
$TIME: 2026-03-27T12:00:00-04:00
$TASK: Test validation
$STATUS: PENDING
---PAYLOAD---
This message is missing $ID.
---END---
```

**Expected:** `validation.valid: false`, `validation.errors: ["Missing $ID"]`

---

## AICP Protocol Reference

### Envelope Fields (required)

| Field    | Description                |
|----------|----------------------------|
| `$PROTO` | Protocol version (AICP/1.0)|
| `$TYPE`  | REQUEST, RESPONSE, ACK, UPDATE, REVIEW, ERROR, HANDOFF, BRAINSTORM |
| `$ID`    | Message ID (MSG-NNNN)      |
| `$FROM`  | Sender agent name          |
| `$TO`    | Target agent(s), comma-separated |
| `$TIME`  | ISO 8601 timestamp         |

### Meta Fields (optional)

| Field       | Description              |
|-------------|--------------------------|
| `$TASK`     | Task description         |
| `$STATUS`   | PENDING, IN_PROGRESS, COMPLETE, FAILED |
| `$REF`      | Reference to prior message ID |
| `$SEQ`      | Sequence number (integer)|
| `$PRIORITY` | LOW, NORMAL, MEDIUM, HIGH|
| `$ROLE`     | Sender's role            |
| `$INTENT`   | Purpose of this message  |

### Custom Fields

Any header without a `$` prefix is a custom field (e.g., `PROJECT: InterAI-Protocol`, `DOMAIN: Multi-Agent Systems`).

### Message Structure

```
$KEY: value
$KEY: value
CUSTOM-KEY: value
---PAYLOAD---
<freeform markdown content>
---END---
```

---

## Known Agents

| Name     | Role              |
|----------|-------------------|
| Don      | Orchestrator      |
| Pharos   | Architect         |
| Lodestar | Systems Architect |
| Forge    | Builder           |

---

## Future Upgrade Path

This workflow is designed for a 3-phase evolution. The Switch contract (`route_pharos`, `route_lodestar`, etc.) remains **stable across all phases** — only the resolution logic changes upstream.

- **Phase 1 (current):** Static name-based routing via hardcoded if/else in the Code node. Branch stubs return mock responses.
- **Phase 2:** Insert a Registry Lookup node between Code and Switch. Reads `agent-registry.json` to resolve agent metadata. Populates `routing.registry`. Switch values unchanged.
- **Phase 3:** Code node routing evolves from name-based to capability-matched. Switch contract remains the same.

When a stub is replaced with a live integration, change `routing.handlerStatus` from `stub` to `live` in that branch's Set node.
