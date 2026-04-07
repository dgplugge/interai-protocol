# AICP API Hub Integration Notes

## Purpose

The API Hub provides a shared round-table channel between the orchestrator and multiple AI agents over HTTPS.
It complements AICP packet journaling by enabling near-real-time dialog and collecting each agent reply in one place.

## Flow

1. Orchestrator opens **API Hub** in the viewer.
2. Selects agents and speaking protocol.
3. Sends one prompt to `/api/agent-hub/roundtable`.
4. Relay server sends HTTPS calls per turn to configured agent endpoints.
5. Hub displays replies in a single transcript window.

## Agent API Profiles (Current)

### Pharos (Claude / Anthropic)
- Typical model role: implementation lead, technical delivery
- Expected API shape: JSON request/response over HTTPS
- Response extraction supports:
  - `content` arrays with text items
  - direct string fields like `reply`, `message`, or `content`

### Lodestar (ChatGPT / OpenAI)
- Typical model role: architecture and design review
- Expected API shape: JSON request/response over HTTPS
- Response extraction supports:
  - OpenAI-style `choices[0].message.content`
  - direct string fields (`reply`, `message`, `content`)

### Forge (Codex / OpenAI)
- Typical model role: design/build and integration execution
- Expected API shape: JSON request/response over HTTPS
- Response extraction supports:
  - OpenAI-style `choices[0].message.content`
  - direct string fields (`reply`, `message`, `content`)

### SpinDrift (Cursor)
- Typical model role: protocol navigation, guardrails, IDE/workflow bridge
- Expected API shape: JSON request/response over HTTPS
- Response extraction supports:
  - direct string fields (`reply`, `message`, `content`)
  - fallback to full JSON text when custom schema is used

## Speaking Protocol Rules

The API Hub enforces a deterministic speaking order per request:

- **Round robin**: selected starter first, then the rest.
- **Priority first**: priority speaker first, then the rest.
- **Alphabetical**: fixed lexical order.

Protocol guardrails:
- one active speaker per turn
- turn number attached to each outbound payload
- ordered transcript shown in the hub stream
- partial failures do not abort subsequent turns

## Endpoint Contract

### Request body sent by API Hub relay

```json
{
  "proto": "AICP/1.0",
  "type": "REQUEST",
  "from": "Don",
  "task": "Communicate with AI Agents via API",
  "project": "InterAI-Protocol",
  "domain": "Multi-Agent Systems",
  "turnMode": "round_robin",
  "turn": 1,
  "turnOrder": ["Pharos", "Lodestar", "Forge", "SpinDrift"],
  "agent": "Pharos",
  "prompt": "Orchestrator prompt text...",
  "priorReplies": []
}
```

### Accepted response formats

The relay attempts to extract reply text in this order:
- `reply`
- `message`
- `content`
- `output_text`
- `text`
- OpenAI: `choices[0].message.content` or `choices[0].text`
- Anthropic-style `content[].text`

If no known field exists, the relay returns the JSON payload as text.

## Configuration

`viewer/agent-api-config.json` controls:
- endpoint URL
- method
- headers
- enable/disable state
- mock reply text
- round-table timeout

Headers may use `${ENV:VAR_NAME}` placeholders.  
Example:

```json
"Authorization": "Bearer ${ENV:FORGE_API_TOKEN}"
```

## Security and Operations

- HTTPS is required by default (`http://` blocked unless explicitly allowed).
- API Hub config endpoint does not return secrets.
- When endpoint config is missing/disabled, the system falls back to mock mode.
