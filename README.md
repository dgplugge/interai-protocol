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
cd viewer
python -m http.server 8080
# Open http://localhost:8080 in your browser
```

Or simply open `viewer/index.html` directly in a browser (messages must be embedded for file:// mode).

## Repository Structure

```
interai-protocol/
├── viewer/          # Browser-based journal viewer (Slice 0)
├── protocol-spec/   # AICP specification documents
├── samples/         # Example messages and journal index
└── README.md
```

## Team

- **Don Plugge** — Orchestrator, Product Owner
- **Pharos** (Claude) — Lead Coder
- **Lodestar** (ChatGPT) — Lead Designer, Reviewer

## License

TBD

## Status

MVP Slice 1 — Journal viewer + Message Builder. Slice 2 (Assisted Relay) in design.
