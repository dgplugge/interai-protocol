# AICP — AI Communication Protocol

A universal, transport-agnostic message format for structured inter-AI agent communication.

## What Is This?

AICP defines a standard message format that any AI agent can read, write, and respond to. It enables structured communication between multiple AI agents (e.g., Claude, ChatGPT, Gemini) through a shared protocol — without requiring direct API integration.

**The protocol is free and universal. The tools built on it are the product.**

## Protocol Overview

Every AICP message has four segments:

| Segment | Purpose | Required |
|---------|---------|----------|
| **ENVELOPE** | Routing & identity (`$PROTO`, `$TYPE`, `$ID`, `$FROM`, `$TO`, `$TIME`) | Yes |
| **META** | Task metadata (`$TASK`, `$STATUS`, `$REF`, `$SEQ`, `$INTENT`, etc.) | Partial |
| **PAYLOAD** | Freeform content (markdown) between `---PAYLOAD---` and `---END---` | No |
| **AUDIT** | Verification (`$SUMMARY`, `$CHANGES`, `$CHECKSUM`) | No |

### Quick Links (Forge onboarding)
- Cheat sheet: `notes/forge-aicp-cheatsheet.md`
- Sample messages (good patterns: MSG-0006…MSG-0010): `samples/messages/`
- API Hub integration guide: `protocol-spec/agent-api-hub.md`
- VB.NET-first API contract + DTO schema: `protocol-spec/agent-hub-vbnet-api-contract.md`

### Example Message

```
$PROTO: AICP/1.0
$TYPE: REQUEST
$ID: MSG-0001
$FROM: Don
$TO: Pharos, Lodestar
$TIME: 2026-03-09T08:05:00-05:00

$TASK: Establish first synchronized inter-agent communication
$STATUS: PENDING
$PRIORITY: HIGH

---PAYLOAD---
Goal:
Initiate the first structured exchange where both AI agents
respond using the shared Inter-AI Protocol format.
---END---
```

## Viewer

The `viewer/` folder contains a lightweight browser-based viewer for AICP message journals.

### Quick Start

```bash
# Start the relay server (serves viewer + enables message saving)
python3 viewer/server.py
# Open http://localhost:8080 in your browser
```

Or simply open `viewer/index.html` directly in a browser (messages must be embedded for file:// mode; relay disabled).

### API Hub (Round-table over HTTPS)

The viewer now includes an **API Hub** dialog for orchestrated multi-agent discussions:

- Select speaking participants (e.g., Pharos, Lodestar, Forge, SpinDrift)
- Choose speaking protocol (round-robin, priority-first, alphabetical)
- Send a single orchestrator prompt
- Receive replies per turn in one shared transcript

Configure real HTTPS endpoints in `viewer/agent-api-config.json`.
If endpoints are disabled or unset, the hub runs in deterministic mock mode.

## Repository Structure

```
interai-protocol/
├── viewer/              # Browser-based journal viewer + relay server
│   ├── server.py        # Python relay server (Slice 2)
│   ├── js/              # Client-side JavaScript modules
│   │   ├── model.js     # Message schema, validation, serialization
│   │   ├── parser.js    # AICP text parser
│   │   ├── loader.js    # Message loading (HTTP + embedded)
│   │   ├── builder.js   # Message composer with relay
│   │   ├── viewer.js    # Timeline UI renderer
│   │   └── registry.js  # Agent registry panel (Slice 3)
│   ├── css/viewer.css   # Dark theme styles
│   └── samples/         # Viewer's copy of journal data
├── protocol-spec/       # AICP specification + agent registry
├── samples/             # Canonical messages and journal index
└── README.md
```

## Team

- **Don Plugge** — Orchestrator, Product Owner
- **Pharos** (Claude) — Lead Coder
- **Lodestar** (ChatGPT) — Lead Designer, Reviewer

## License

TBD

## Status

MVP Slice 3 complete — Journal viewer, Message Builder, Assisted Relay, Agent Registry.  
API Hub round-table relay scaffolding added (HTTPS + mock fallback).
