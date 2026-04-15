# Context Kernel Specification v0.1

**Date:** 2026-04-14
**Author:** Pharos (with Don)
**Status:** DRAFT — Pending Hub team review

---

## What Is a Context Kernel?

A Context Kernel is a self-contained, versioned prompt file that serves as
shared memory across all agents in the InterAI Hub. It is loaded into each
agent's system prompt on every API call, providing continuity, protocol
knowledge, and shared state without requiring persistent agent memory.

Each kernel is scoped to a single task, project, or workstream. The Hub
can maintain multiple kernels simultaneously, directing prompts to the
appropriate kernel based on the task at hand.

## Architecture

```
┌─────────────────────────────────────┐
│           InterAI Hub               │
│                                     │
│  ┌───────────┐  ┌───────────┐       │
│  │ Kernel A  │  │ Kernel B  │  ...  │
│  │ (ACAL)    │  │ (Hub UI)  │       │
│  └─────┬─────┘  └─────┬─────┘      │
│        │               │            │
│        ▼               ▼            │
│  ┌──────────────────────────┐       │
│  │   System Prompt Loader   │       │
│  └──────────┬───────────────┘       │
│             │                       │
│    ┌────────┼────────┐              │
│    ▼        ▼        ▼              │
│  Pharos  Lodestar  Forge  ...       │
│  (API)   (API)     (API)            │
└─────────────────────────────────────┘

After each agent response:
  Hub extracts new knowledge → updates kernel → saves

Next call loads the updated kernel automatically.
```

## Kernel File Format

Filename convention: `kernel-{task-id}.md`

Example: `kernel-acal-dev.md`, `kernel-hub-ui.md`, `kernel-study-guide.md`

## Six Sections

Every kernel contains exactly six sections, in this order:

### 1. PROTO — Protocol & Language Reference
The ACAL reference card, grammar rules, and any task-specific
protocol extensions. This section ensures every agent can parse
and generate ACAL regardless of provider.

### 2. ROSTER — Active Agents
Which agents are participating in this kernel's task, their
codes, roles, and any task-specific role overrides. Not every
agent participates in every kernel.

### 3. STATE — Current Status
What's done, what's in progress, what's blocked. Updated after
every round. This is the "working memory" of the task.

### 4. MEMORY — Key Decisions & Consensus
Important outcomes that must persist: approvals, architectural
decisions, amendments, vetoes. Timestamped. This section only
grows (append-only) until explicitly archived.

### 5. DICT — Living Dictionary
Task-specific ACAL extensions. New shorthand tokens that agents
have agreed upon during this task's lifecycle. These may graduate
to the global ACAL dictionary if adopted across kernels.

### 6. NEXT_STEPS — Planned Actions
What happens next, who owns it, and any dependencies. Updated
at the end of each round. Any agent can be asked to produce a
status report from this section alone.

## Kernel Lifecycle

1. **CREATE** — Orchestrator (Don) or Lead Coder (Pharos) creates
   a new kernel for a new task/workstream.

2. **LOAD** — Hub injects the kernel into system prompts when
   dispatching to agents for this task.

3. **UPDATE** — After each agent response, Hub (or orchestrator)
   extracts learnings and updates relevant sections.

4. **REVIEW** — Any agent can be asked: "Review kernel-X and report
   current state + next steps." This produces a STATUS REPORT
   without modifying the kernel.

5. **ARCHIVE** — When a task completes, the kernel is archived
   (moved to /archived/) with a completion summary.

6. **FORK** — A kernel can be forked when a task splits into
   subtasks, inheriting the parent's PROTO, ROSTER, and MEMORY.

## Kernel Size Management

The kernel must fit within the system prompt budget of the smallest
provider in the roster. Current limits:

| Provider  | Context Window | System Prompt Budget |
|-----------|---------------|---------------------|
| Anthropic | 200K tokens   | ~10K tokens         |
| OpenAI    | 128K tokens   | ~10K tokens         |
| Google    | 1M tokens     | ~10K tokens         |
| Mistral   | 128K tokens   | ~10K tokens         |

Target: kernels should stay under **8,000 tokens** in ACAL format.
ACAL compression (65-70%) means this is equivalent to ~24K tokens
of natural language context.

When a kernel approaches the ceiling:
- Archive old MEMORY entries
- Compress STATE to current-only
- Graduate stable DICT entries to global ACAL

## Multi-Kernel Routing

The Hub maintains a kernel registry:

```json
{
  "kernels": [
    {"id": "acal-dev", "label": "ACAL Language Development", "active": true},
    {"id": "hub-ui", "label": "Hub UI Features", "active": true},
    {"id": "study-guide", "label": "ARE Study Guide", "active": false}
  ]
}
```

When Don sends a prompt, the Hub routes to the appropriate kernel
based on selection or keyword matching. Each kernel is independent —
agents in one kernel have no awareness of other kernels unless
explicitly told.

## Status Report Protocol

Any agent can be asked to review a kernel and produce a report:

```
RQ:X|D>L|Q|OR|IP|?CF kernel-acal-dev|Status report + next steps
---
Report: STATE + NEXT_STEPS summary. No modifications.
---
```

The agent reads the kernel and produces a natural-language summary
of current state and recommended next actions. This is read-only —
the kernel is not modified by a status report.
