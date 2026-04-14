# AICP Compressed Agent Language (ACAL) v0.1

**Draft Specification**
**Date:** 2026-04-14
**Corpus:** ~155 AICP journal messages across 4 projects
**Purpose:** Define a compressed agent-to-agent communication language derived from empirical frequency analysis of the full AICP message corpus

---

## 1. Frequency Analysis Summary

### 1.1 Corpus Overview

| Project | Messages | Date Range |
|---------|----------|------------|
| InterAI-Protocol | ~95 | 2026-03-09 to 2026-04-09 |
| OperatorHub | ~43 | 2026-03-10 to 2026-04-02 |
| StudyGuide | ~15 | 2026-03-30 to 2026-03-31 |
| PortfolioAnalysis | ~2 | 2026-03-23 |
| **Total** | **~155** | |

### 1.2 Message Type Distribution

| $TYPE Value | Count | Frequency |
|-------------|-------|-----------|
| REQUEST | ~42 | 27% |
| RESPONSE | ~38 | 25% |
| ACK | ~30 | 19% |
| REVIEW | ~22 | 14% |
| UPDATE | ~16 | 10% |
| PLAN | ~3 | 2% |
| ERROR | ~2 | 1% |
| BRAINSTORM | ~1 | <1% |

**Key finding:** REQUEST, RESPONSE, and ACK account for 71% of all traffic. REVIEW is the fourth most common at 14%. UPDATE is used for status reports. PLAN, ERROR, and BRAINSTORM are rare.

### 1.3 Agent Name Frequency

| Agent | As $FROM | As $TO (recipient) | Total Mentions |
|-------|----------|--------------------|----------------|
| Pharos | ~58 | ~145 | ~203 |
| Don | ~42 | ~130 | ~172 |
| Lodestar | ~38 | ~140 | ~178 |
| Forge | ~2 | ~12 | ~14 |
| SpinDrift | ~3 | ~10 | ~13 |
| Trident | 0 | ~3 | ~3 |
| Lumen | 0 | ~1 | ~1 |

**Key finding:** Three agents (Pharos, Don, Lodestar) dominate all traffic. Forge, SpinDrift, Trident, and Lumen are peripheral agents that appear in later messages only.

### 1.4 Status Value Distribution

| $STATUS | Count | Frequency |
|---------|-------|-----------|
| COMPLETE | ~48 | 31% |
| IN_PROGRESS / IN-PROGRESS | ~38 | 25% |
| PENDING | ~35 | 23% |
| APPROVED | ~8 | 5% |
| ACTIVE | ~4 | 3% |
| OPEN | ~2 | 1% |
| Other/missing | ~20 | 13% |

**Key finding:** COMPLETE, IN_PROGRESS, and PENDING cover 79% of status values. APPROVED is used specifically in REVIEW messages.

### 1.5 Role Distribution

| $ROLE | Count | Agent |
|-------|-------|-------|
| Lead Coder | ~50 | Pharos |
| Orchestrator | ~40 | Don |
| Lead Designer / Lead Designer, Reviewer | ~30 | Lodestar |
| Reviewer | ~15 | Lodestar |
| Architect / Systems Architect | ~10 | Pharos, Lodestar |
| Design Advisor | ~5 | Lodestar |
| Implementation Lead | ~3 | Pharos |

**Key finding:** Roles are tightly bound to agents. Pharos is always a coder/implementer. Lodestar is always a designer/reviewer. Don is always the orchestrator.

### 1.6 Priority Distribution

| $PRIORITY | Count | Frequency |
|-----------|-------|-----------|
| HIGH | ~110 | 71% |
| MEDIUM | ~12 | 8% |
| Missing/unset | ~33 | 21% |

**Key finding:** HIGH is overwhelmingly dominant; MEDIUM is rare; LOW never appears.

### 1.7 Project Distribution

| PROJECT | Count |
|---------|-------|
| InterAI-Protocol | ~95 |
| OperatorHub | ~43 |
| StudyGuide | ~15 |
| Portfolio Analysis | ~2 |

### 1.8 Domain Values

| DOMAIN | Count |
|--------|-------|
| Multi-Agent Systems | ~80 |
| Flow Cytometry Lab Operations | ~40 |
| AI-Assisted Learning | ~15 |
| System Architecture / Protocol Core Migration | ~5 |
| Financial portfolio tooling | ~2 |
| Infrastructure / Message Relay | ~3 |

### 1.9 Top Repeated Phrases in Payloads (20+ occurrences)

| Phrase | Count |
|--------|-------|
| "RECEIPT ACKNOWLEDGED" / "ACKNOWLEDGED" | ~35 |
| "APPROVED" / "APPROVED WITH..." | ~20 |
| "Lead Coder -> Pharos" | ~15 |
| "Orchestrator -> Don" | ~15 |
| "Lead Designer -> Lodestar" / "Reviewer -> Lodestar" | ~15 |
| "AWAITING ORCHESTRATOR" / "AWAITING..." | ~18 |
| "Ready for review" / "READY FOR REVIEW" | ~14 |
| "No overlapping edits" | ~8 |
| "Implementation authority" | ~8 |
| "Per Hub team consensus" | ~6 |
| "Green light" / "green light" | ~10 |
| "Slice N" (numbered implementation phases) | ~40+ |
| "COMPLETE" / "STATUS: COMPLETE" | ~30 |
| "Approved as proposed" | ~5 |
| "READY FOR IMPLEMENTATION" | ~6 |
| "AWAITING NEXT ORCHESTRATION" | ~5 |
| "Phase N" (numbered phases) | ~20 |
| "REVIEW RESULT:" | ~12 |
| "REVIEW ACCEPTED" | ~10 |
| "will implement" / "WILL IMPLEMENT" | ~8 |
| "SUCCESS CRITERIA" | ~6 |
| "NON-GOALS" | ~8 |

### 1.10 Action Verb Frequency

| Verb | Count |
|------|-------|
| implement / build | ~45 |
| review | ~35 |
| approve / accept | ~25 |
| acknowledge / ack | ~30 |
| design / propose | ~25 |
| update / modify | ~20 |
| test / verify / validate | ~20 |
| fix / correct | ~12 |
| add / create | ~15 |
| refactor | ~5 |
| deploy / push | ~8 |
| migrate | ~10 |
| route / relay | ~12 |

### 1.11 Architecture Layer References

| Layer Term | Count |
|------------|-------|
| view / viewer / UI | ~40 |
| presenter | ~25 |
| model | ~20 |
| service / service layer | ~15 |
| adapter | ~10 |
| parser | ~15 |
| config / configuration | ~15 |
| database / DB / table | ~20 |
| middleware / relay | ~10 |
| interface / contract | ~8 |
| test / NUnit | ~8 |
| webhook / endpoint | ~12 |

---

## 2. The ACAL Codebook

### 2.A Protocol Header Compression

#### Message Type Codes (2-3 chars)

| Code | Full Value | Frequency |
|------|-----------|-----------|
| `RQ` | REQUEST | 27% |
| `RS` | RESPONSE | 25% |
| `AK` | ACK | 19% |
| `RV` | REVIEW | 14% |
| `UP` | UPDATE | 10% |
| `PL` | PLAN | 2% |
| `ER` | ERROR | 1% |
| `BS` | BRAINSTORM | <1% |

#### Agent Codes (1-2 chars)

| Code | Agent | Rationale |
|------|-------|-----------|
| `D` | Don | Orchestrator, most frequent human |
| `P` | Pharos | Lead Coder, most frequent AI sender |
| `L` | Lodestar | Lead Designer/Reviewer |
| `F` | Forge | Specialist agent |
| `S` | SpinDrift | Cursor-based agent |
| `T` | Trident | Gemini agent |
| `U` | Lumen | Mistral agent |
| `*` | ALL | Broadcast to all agents |

Multi-target: `P,L` = Pharos and Lodestar; `*` = all agents

#### Status Codes (1-2 chars)

| Code | Full Value |
|------|-----------|
| `C` | COMPLETE |
| `W` | IN_PROGRESS (Working) |
| `Q` | PENDING (Queued) |
| `A` | APPROVED |
| `X` | ERROR / FAILED |
| `H` | HOLD / DEFERRED |

#### Priority Codes (1 char)

| Code | Full Value |
|------|-----------|
| `!` | HIGH |
| `.` | MEDIUM |
| `_` | LOW |

#### Role Codes (2 chars)

| Code | Full Value |
|------|-----------|
| `LC` | Lead Coder |
| `LD` | Lead Designer |
| `RV` | Reviewer |
| `OR` | Orchestrator |
| `AR` | Architect |
| `DA` | Design Advisor |
| `IL` | Implementation Lead |

#### Project Codes (2-3 chars)

| Code | Project |
|------|---------|
| `IP` | InterAI-Protocol |
| `OH` | OperatorHub |
| `SG` | StudyGuide |
| `PA` | PortfolioAnalysis |

### 2.B Architecture Layer Codes (1-2 chars)

| Code | Layer | Examples from corpus |
|------|-------|---------------------|
| `V` | View / UI | viewer.js, frmAgentSettings, WinForms |
| `PR` | Presenter | MainPresenter, AgentHubPresenter |
| `M` | Model | model.js, AicpMessage, CsvMergeModel |
| `SV` | Service | project-registry.js, AicpValidator |
| `AD` | Adapter | ClaudeAdapter, OpenAIAdapter |
| `MW` | Middleware / Relay | server.py, relay endpoint |
| `DB` | Database | TableAdapters, SQL tables |
| `CF` | Configuration | agent-hub-config.json, n8n-config.json |
| `IF` | Interface / Contract | protocol spec, API contracts |
| `TS` | Test | NUnit tests, edge-case tests |
| `PX` | Parser | parser.js, AICP ingress parser |
| `WH` | Webhook / Endpoint | /api/relay, /aicp-ingress |
| `RT` | Router | Switch node, routing resolver |

### 2.C Action Verb Codes (1-2 chars)

| Code | Action | Covers |
|------|--------|--------|
| `+` | Add / Create | New file, feature, endpoint |
| `~` | Modify / Update | Change existing code |
| `-` | Remove / Delete | Remove code, deprecate |
| `?` | Review / Inspect | Code review, design review |
| `!` | Approve / Accept | Green-light, sign-off |
| `^` | Refactor | Restructure without behavior change |
| `>` | Deploy / Push | Ship to production or repo |
| `#` | Test / Verify | Unit test, integration test, validate |
| `@` | Fix / Correct | Bug fix, error correction |
| `<` | Migrate | Move between systems/architectures |
| `&` | Route / Relay | Message forwarding, dispatch |

### 2.D Common Phrase Compression

#### Coordination Phrases

| Token | Expands To |
|-------|-----------|
| `ACK` | Receipt acknowledged |
| `APR` | Approved as proposed |
| `APR+` | Approved with amendments |
| `AWO` | Awaiting orchestrator decision |
| `AWR` | Awaiting review |
| `AWG` | Awaiting green light |
| `RFR` | Ready for review |
| `RFI` | Ready for implementation |
| `NOE` | No overlapping edits |
| `HTC` | Per Hub team consensus |
| `NGA` | Non-goals (do not implement) |
| `SCR` | Success criteria |

#### Status Phrases

| Token | Expands To |
|-------|-----------|
| `SLC:N` | Slice N (implementation phase N) |
| `PHS:N` | Phase N |
| `MVP` | Minimum viable product |
| `P1` / `P2` / `P3` | Priority 1 / 2 / 3 |
| `BLK` | Blocked |
| `DEF` | Deferred to future iteration |

#### Role Assignment Phrases

| Token | Expands To |
|-------|-----------|
| `IA:X` | Implementation authority: agent X |
| `RA:X` | Review authority: agent X |
| `OA:X` | Orchestration authority: agent X |

#### Architectural Phrases

| Token | Expands To |
|-------|-----------|
| `BC` | Backward compatible |
| `ZD` | Zero dependencies |
| `NB` | No build step required |
| `FW` | Forward-compatible / future-ready |
| `BRK` | Breaking change |
| `TD` | Technical debt |

### 2.E Compressed Header Format

The full AICP envelope:

```
$PROTO: AICP/1.0
$TYPE: REQUEST
$ID: MSG-0094
$REF: MSG-0093
$SEQ: 125
$FROM: Pharos
$TO: Don, Lodestar, Forge, SpinDrift, Trident
$TIME: 2026-04-08T17:00:00-04:00
$TASK: Agent Settings Form
$STATUS: IN_PROGRESS
$PRIORITY: HIGH
$ROLE: Lead Coder
$INTENT: Build a settings form for managing AI agents
PROJECT: InterAI-Protocol
DOMAIN: Multi-Agent Systems
```

Compresses to a single-line ACAL header:

```
RQ:94>93|P>D,L,F,S,T|W!|LC|IP|Agent Settings Form|Build settings form for agent mgmt
```

Format: `TYPE:ID>REF|FROM>TO|STATUS PRIORITY|ROLE|PROJECT|TASK|INTENT`

- `$PROTO` is implicit (ACAL assumes AICP/1.0)
- `$TIME` is system-generated (omitted from wire format)
- `$SEQ` is auto-computed from message order (omitted)
- `DOMAIN` is derived from PROJECT code (omitted)

**Header compression ratio: ~75% reduction** (from ~350 chars to ~85 chars)

---

## 3. Composite Message Format

### Full ACAL Message Structure

```
HEADER_LINE
---
PAYLOAD (compressed or natural language)
---
AUDIT_LINE (optional)
```

Where:
- `HEADER_LINE` = `TYPE:ID>REF|FROM>TO|STATUS PRIORITY|ROLE|PROJECT|TASK|INTENT`
- `---` = payload delimiter (replaces `---PAYLOAD---` and `---END---`)
- `AUDIT_LINE` = `S:summary text` (replaces `$SUMMARY`)

### 3.1 Compressed Payload Operators

Within the payload, agents can use these operators:

| Operator | Meaning | Example |
|----------|---------|---------|
| `+V file.js` | Add to view layer: file.js | `+V frmSettings.vb` |
| `~PR presenter.vb` | Modify presenter layer | `~PR AgentHubPresenter.vb` |
| `+IF IAgentConfig` | Add interface: IAgentConfig | `+IF IAgentConfig` |
| `?SV service.py` | Review service layer | `?SV server.py` |
| `#TS test.vb` | Run/add tests | `#TS BackfillTest.vb` |
| `@PX parser.js` | Fix parser | `@PX parser.js` |

#### Multi-operation shorthand

```
+IF IAgentConfig; +M AgentConfigModel; ~PR AgentHubPresenter; +V frmAgentConfig; #TS AgentConfigTest
```

This reads as: "Add interface IAgentConfig, add model AgentConfigModel, modify AgentHubPresenter, add form frmAgentConfig, test with AgentConfigTest."

---

## 4. Worked Examples

### Example 1: Simple ACK

**Natural language (original AICP):**
```
$PROTO: AICP/1.0
$TYPE: ACK
$ID: MSG-0093
$REF: MSG-0092
$SEQ: 124
$FROM: Pharos
$TO: Don, Lodestar
$TIME: 2026-04-08T13:15:00-04:00
$TASK: ACK Lodestar Phase 1 Endorsement
$STATUS: IN_PROGRESS
$ROLE: Lead Coder
$INTENT: Accept Lodestar's phased plan and Phase 1.5 proposal
PROJECT: InterAI-Protocol
DOMAIN: Multi-Agent Systems

---PAYLOAD---
ACK. Lodestar's phased plan accepted in full.

AGREED:
  Phase 1: prompt + history fix (implemented, ready for test)
  Phase 1.5: hub-level guardrails
  Phase 2: distributed architecture (deferred, blueprint preserved)
---END---
```

**ACAL:**
```
AK:93>92|P>D,L|W!|LC|IP|ACK Phase 1 endorsement|Accept phased plan + P1.5
---
ACK. APR PHS:1+1.5. PHS:2 DEF.
---
```

**Reduction: ~520 chars to ~105 chars (80%)**

### Example 2: Implementation Complete Response

**Natural language (original AICP):**
```
$PROTO: AICP/1.0
$TYPE: RESPONSE
$ID: MSG-0010
$REF: MSG-0008
$SEQ: 10
$FROM: Pharos
$TO: Don, Lodestar
$TIME: 2026-03-09T09:15:00-05:00
$TASK: Implement MVP viewer app skeleton - Slice 0
$STATUS: COMPLETE
$PRIORITY: HIGH
$ROLE: Lead Coder
$INTENT: Deliver Slice 0 for review
PROJECT: InterAI-Protocol
DOMAIN: Multi-Agent Systems

---PAYLOAD---

1. SLICE 0 IMPLEMENTATION: COMPLETE.
   Files: index.html, viewer.css, model.js, parser.js, loader.js, viewer.js
2. FEATURES: timeline, detail panel, sender colors, REF nav, keyboard nav
3. SAMPLE DATA: MSG-0001 through MSG-0009
4. READY FOR REVIEW.

---END---
```

**ACAL:**
```
RS:10>8|P>D,L|C!|LC|IP|SLC:0 viewer skeleton|Deliver for review
---
SLC:0 C. +V index.html,viewer.css; +M model.js; +PX parser.js; +SV loader.js; +V viewer.js
Features: timeline, detail panel, sender colors, REF nav, kbd nav
Sample: MSG-0001..0009. RFR.
---
```

**Reduction: ~550 chars to ~230 chars (58%)**

### Example 3: Review with Approval

**Natural language (original AICP):**
```
$PROTO: AICP/1.0
$TYPE: REVIEW
$ID: MSG-0011
$REF: MSG-0010
$FROM: Lodestar
$TO: Don, Pharos
$TASK: Review MVP viewer app skeleton - Slice 0
$STATUS: COMPLETE
$ROLE: Lead Designer, Reviewer
$INTENT: Approve Slice 0, identify hardening items

---PAYLOAD---
1. REVIEW RESULT: APPROVED.
2. STRENGTHS: platform correct, model.js good addition, interaction useful
3. PARSER HARDENING: expand key parsing, normalize invalid $SEQ, duplicate keys, timestamp validation
4. UX SUGGESTIONS: copy packet, raw/formatted toggle, filters, validation badge
5. NEXT: Slice 1 = Message Builder
---END---
```

**ACAL:**
```
RV:11>10|L>D,P|C.|LD,RV|IP|Review SLC:0|APR+ hardening items
---
APR. Strengths: platform, model.js, interaction.
Harden: ?PX key-parse,seq-null,dup-keys,time-valid
UX: +V copy-packet,raw-toggle,filters,valid-badge
Next: SLC:1 = Message Builder
---
```

**Reduction: ~480 chars to ~210 chars (56%)**

### Example 4: Multi-step Implementation Request (Agent Config Interface)

**User's requested scenario:** "How would the language tell an agent to make a change to the code involving an interface addition to allow the agent config to be read, displayed and verified working for each agent?"

**Natural language (original AICP equivalent):**
```
$PROTO: AICP/1.0
$TYPE: REQUEST
$ID: MSG-0100
$FROM: Don
$TO: Pharos
$TIME: 2026-04-14T10:00:00-04:00
$TASK: Add agent configuration interface with read, display, and verification
$STATUS: PENDING
$PRIORITY: HIGH
$ROLE: Orchestrator
$INTENT: Create an interface layer allowing each agent's configuration to be read from storage, displayed in the UI, and verified as operational
PROJECT: InterAI-Protocol
DOMAIN: Multi-Agent Systems

---PAYLOAD---

Requirements:
1. Create an IAgentConfig interface defining the contract for agent configuration access
2. Implement a concrete AgentConfigReader that loads config from agent-hub-config.json
3. Add a UI panel (frmAgentConfig or tab in existing settings) that displays each agent's:
   - Name, provider, model, endpoint, enabled status
   - System prompt preview
4. Add a "Test Connection" button per agent that sends a minimal prompt and verifies a valid response
5. Display verification result (pass/fail with latency) next to each agent row
6. Follow MVP pattern: separate View, Presenter, Model projects
7. TableAdapter pattern if any DB access is needed

Success criteria:
- All registered agents appear in the config panel
- Each agent shows its current configuration values
- Test Connection returns pass/fail within timeout
- No manual JSON editing required for configuration review

---END---
```

**ACAL:**
```
RQ:100|D>P|Q!|OR|IP|+IF IAgentConfig: read,display,verify|Enable agent config mgmt without JSON editing
---
+IF IAgentConfig {read,display,verify}
+M AgentConfigModel {name,provider,model,endpoint,enabled,sysPrompt}
+SV AgentConfigReader < agent-hub-config.json
+V frmAgentConfig {grid: agent rows + config fields; btn: TestConnection per agent}
~PR AgentHubPresenter {LoadConfigEvent, TestAgentEvent}
#TS verify: all agents visible, config values correct, TestConnection pass/fail+latency
MVP: V/PR/M separation. NOE.
SCR: no manual JSON for config review; all agents display; test returns pass/fail < timeout
---
```

**Reduction: ~950 chars to ~420 chars (56%)**

**How to read this ACAL message:**
- `RQ:100` = REQUEST, message ID 100
- `D>P` = from Don to Pharos
- `Q!` = status PENDING, priority HIGH
- `OR` = role Orchestrator
- `IP` = project InterAI-Protocol
- `+IF IAgentConfig {read,display,verify}` = add interface named IAgentConfig supporting read, display, verify operations
- `+M AgentConfigModel {...}` = add model with these fields
- `+SV AgentConfigReader < agent-hub-config.json` = add service reading from config file
- `+V frmAgentConfig {...}` = add view/form with grid and buttons
- `~PR AgentHubPresenter {...}` = modify presenter, add events
- `#TS verify:` = test criteria
- `MVP: V/PR/M separation. NOE.` = follow MVP pattern, no overlapping edits
- `SCR:` = success criteria

### Example 5: Compressing the Original Prompt for This Task

**Natural language (the user's original request):**
```
You are analyzing the entire AICP journal message corpus to design a
compressed agent-to-agent communication language. Read all journal
messages across 4 projects (~160 messages). Perform frequency analysis
on headers, phrases, agents, types, tasks, statuses, roles, architecture
terms, action verbs, and project references. Design a codebook with
header compression, layer codes, verb codes, phrase compression, and
composite examples. Include an example of adding an interface for agent
config read/display/verify. Write the spec to docs/aicp-compression-
language-v0.1.md.
```

**ACAL:**
```
RQ:X|D>P|Q!|OR|IP|Design ACAL from corpus analysis|Compressed agent language spec
---
?PX all journals: IP,OH,SG,PA (~160 msgs)
Analyze: headers,phrases,agents,types,tasks,status,roles,arch-terms,verbs,project-xref
+IF ACAL codebook {header-compress,layer-codes,verb-codes,phrase-compress}
+5 examples: AK simple, RS impl-complete, RV approval, RQ +IF agent-config, RQ self-ref
Output: >docs/aicp-compression-language-v0.1.md
---
```

**Reduction: ~580 chars to ~330 chars (43%)**

---

## 5. Size Reduction Estimates

| Message Type | Avg Original Size | Avg ACAL Size | Reduction |
|-------------|-------------------|---------------|-----------|
| ACK (simple) | ~350 chars | ~80 chars | 77% |
| ACK (with detail) | ~600 chars | ~150 chars | 75% |
| REQUEST (simple) | ~500 chars | ~180 chars | 64% |
| REQUEST (complex) | ~1200 chars | ~450 chars | 63% |
| RESPONSE (impl report) | ~800 chars | ~300 chars | 63% |
| REVIEW (approval) | ~600 chars | ~220 chars | 63% |
| UPDATE (status) | ~400 chars | ~120 chars | 70% |

**Overall average reduction: ~65-70%**

The greatest savings come from:
1. **Header compression** (~75% reduction): eliminating redundant keywords ($PROTO, $TIME, $SEQ, DOMAIN) and using single-character agent/status codes
2. **Phrase tokens** (~80% reduction per phrase): replacing multi-word coordination phrases with 2-4 character tokens
3. **Layer+action shorthand** (~60% reduction): `+IF IAgentConfig` vs "Create an IAgentConfig interface defining the contract for agent configuration access"

---

## 6. What Makes ACAL Different from Abbreviation

ACAL is not just shorter AICP. It is a **semantic language** with these distinguishing properties:

### 6.1 Composable Grammar

ACAL has grammar rules, not just substitution tables:

- **Header line** follows a fixed positional format: `TYPE:ID>REF|FROM>TO|STATUS PRIORITY|ROLE|PROJECT|TASK|INTENT`
- **Payload operations** follow `ACTION LAYER target {params}` syntax
- **Operations compose**: `+IF X; +M Y; ~PR Z; #TS W` is a valid multi-step instruction parsed left to right

This means an agent can GENERATE valid ACAL without a lookup table -- it learns the grammar.

### 6.2 Implicit Protocol Knowledge

ACAL encodes domain-specific assumptions that pure abbreviation cannot:

- `$PROTO` is never transmitted because ACAL IS the protocol indicator
- `$TIME` is never transmitted because the transport layer timestamps
- `$SEQ` is never transmitted because message ordering is transport-level
- `DOMAIN` is never transmitted because it is derived from the PROJECT code
- `$PRIORITY: HIGH` is the default (71% of corpus) -- only non-HIGH priority is marked

This is **semantic compression**: knowledge about the system's actual usage patterns reduces what must be stated explicitly.

### 6.3 Layered Addressing

The `ACTION LAYER target` syntax (`+V frmSettings.vb`) encodes THREE pieces of information in a single expression:
1. What to do (add)
2. Where in the architecture (view layer)
3. What artifact is affected (frmSettings.vb)

Natural language would require a full sentence: "Add a new form called frmSettings.vb to the View layer."

### 6.4 Role-Implicit Routing

Because roles are tightly bound to agents (Pharos=LC, Lodestar=LD/RV, Don=OR), the ROLE code in the header serves as both identity confirmation AND capability declaration. An agent receiving `|LC|` knows:
- This message was sent by someone claiming coder authority
- The sender is asserting implementation ownership
- Review authority is NOT claimed

### 6.5 Consensus Tokens

Tokens like `APR`, `HTC`, `NOE`, `AWO` encode not just phrases but **protocol state transitions**:
- `APR` = the review gate has been passed
- `HTC` = a group decision was reached (not individual)
- `NOE` = an edit-conflict prevention contract is active
- `AWO` = a blocking dependency on the orchestrator exists

These are governance primitives, not abbreviations.

### 6.6 Self-Describing Operations

The `+IF IAgentConfig {read,display,verify}` syntax is self-describing:
- Another agent can parse this without a lookup table
- The interface name, its layer, and its capabilities are all in the expression
- An implementing agent can derive the method signatures from the capability list

---

## 7. Parser Specification (for implementing agents)

### 7.1 Header Parsing

```
HEADER = TYPE ":" ID [">" REF] "|" FROM ">" TO "|" STATUS [PRIORITY] "|" ROLE "|" PROJECT "|" TASK "|" INTENT
TYPE   = "RQ" | "RS" | "AK" | "RV" | "UP" | "PL" | "ER" | "BS"
ID     = INTEGER
REF    = INTEGER (optional, omit ">" if no reference)
FROM   = AGENT_CODE
TO     = AGENT_CODE ("," AGENT_CODE)*
STATUS = "C" | "W" | "Q" | "A" | "X" | "H"
PRIORITY = "!" | "." | "_" (optional, default "!")
ROLE   = ROLE_CODE ("," ROLE_CODE)*
PROJECT = PROJECT_CODE
TASK   = FREE_TEXT
INTENT = FREE_TEXT
```

### 7.2 Payload Parsing

```
OPERATION = ACTION LAYER TARGET ["{" PARAMS "}"]
ACTION    = "+" | "~" | "-" | "?" | "!" | "^" | ">" | "#" | "@" | "<" | "&"
LAYER     = "V" | "PR" | "M" | "SV" | "AD" | "MW" | "DB" | "CF" | "IF" | "TS" | "PX" | "WH" | "RT"
TARGET    = FILENAME | CLASSNAME | FREE_TEXT
PARAMS    = FREE_TEXT
MULTI_OP  = OPERATION (";" OPERATION)*
```

### 7.3 Token Expansion

Tokens in the codebook (Section 2.D) expand deterministically. An agent encountering `APR+` always expands to "Approved with amendments" regardless of context.

---

## 8. Migration Path

### Phase 1: Human-Readable Hybrid (Current)
AICP messages continue as-is. ACAL is used in `$SUMMARY` fields and inter-agent shorthand within payloads.

### Phase 2: Dual Format
Messages include both AICP headers (for viewer compatibility) and ACAL compact form (for agent-to-agent efficiency). The ACAL line could be added as a new header: `$ACAL: RQ:100|D>P|Q!|OR|IP|...`

### Phase 3: Native ACAL
Agent-to-agent traffic uses ACAL natively. The viewer/journal layer expands ACAL to human-readable AICP for display. Compression happens at send, expansion at display.

---

## 9. Reserved for Future Extension

- **Conditional operations**: `IF condition THEN operation`
- **Dependency chains**: `+M X -> ~PR Y -> #TS Z` (ordered dependencies)
- **Capability queries**: `?? agent capabilities` (ask what an agent can do)
- **Batch references**: `MSG:50..55` (reference a range of messages)
- **Voting/consensus**: `VOTE:APR 2/3` (2 of 3 agents approved)

---

## Appendix: Quick Reference Card

```
MESSAGE TYPES    AGENTS    STATUS    PRIORITY    ROLES
RQ = Request     D = Don   C = Done  ! = High    LC = Lead Coder
RS = Response    P = Phar  W = WIP   . = Med     LD = Lead Designer
AK = ACK         L = Lode  Q = Pend  _ = Low     RV = Reviewer
RV = Review      F = Forge A = Appr                OR = Orchestrator
UP = Update      S = Spin  X = Fail                AR = Architect
PL = Plan        T = Trid  H = Hold
ER = Error       U = Lumen
BS = Brainstorm  * = All

ACTIONS          LAYERS           PHRASES
+ = Add          V  = View        ACK = Acknowledged
~ = Modify       PR = Presenter   APR = Approved
- = Remove       M  = Model       AWO = Awaiting orchestrator
? = Review       SV = Service     RFR = Ready for review
! = Approve      AD = Adapter     RFI = Ready for implementation
^ = Refactor     MW = Middleware   NOE = No overlapping edits
> = Deploy       DB = Database    HTC = Hub team consensus
# = Test         CF = Config      NGA = Non-goals
@ = Fix          IF = Interface   SCR = Success criteria
< = Migrate      TS = Test        SLC:N = Slice N
& = Route        PX = Parser      PHS:N = Phase N
                 WH = Webhook     MVP = Min viable product
                 RT = Router      BC = Backward compatible

HEADER FORMAT:
TYPE:ID>REF|FROM>TO|STATUS PRIORITY|ROLE|PROJECT|TASK|INTENT

EXAMPLE:
RQ:100|D>P|Q!|OR|IP|+IF IAgentConfig|Enable config mgmt
```
