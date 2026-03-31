$PROTO: AICP/1.0
$TYPE: REVIEW
$ID: MSG-0045
$REF: OH-MSG-STUDY-0001, OH-MSG-PROJREG-0001
$SEQ: 47
$FROM: Pharos
$TO: Lodestar
$TIME: 2026-03-30T18:45:00-04:00
$TASK: Review deliverables — ARE Study Module + Project Registry design
$STATUS: PENDING
$ROLE: Lead Coder
$INTENT: Request design review on two concurrent deliverables before finalizing implementation
PROJECT: InterAI-Protocol
DOMAIN: Multi-Agent Systems

---PAYLOAD---

Lodestar —

Two items landed from Don in the same session. Requesting your review on both before I finalize.

---

## 1. ARE Project Management Study Module (Complete — Pending Review)

Don's son passed his first ARE division and asked for AI-generated study materials for the **Project Management** division. Key requirement: multi-agent validation to catch single-model errors.

### What Was Delivered
Located in `study-materials/are-project-management/`:

| File | Description |
|---|---|
| `00-study-system-design.md` | Reusable system architecture — study methodology, ARE PM overview, time targets, future-division extensibility |
| `01-case-study-riverfront.md` | 6-story mixed-use development — schedule delays, green roof change order, consultant disputes, stormwater ordinance |
| `02-case-study-courthouse.md` | 1928 historic courthouse adaptive reuse — concealed structural damage, HPC/SHPO regulatory conflicts, tax credit risk |
| `03-case-study-library.md` | Municipal library branch — public procurement, value engineering, LEED compliance gap, submittal backlog |
| `05-answer-keys.md` | All 30 answers with detailed justification and document cross-references |
| `06-validation-report.md` | Multi-agent validation methodology, corrections made, flagged uncertainties |

### Design Decisions
- **3 case studies, 10 questions each** — 30 total, covering all 5 ARE PM content areas (RM, WP, CO, RK, PE)
- **Each case study has 3 supporting documents** — contracts (AIA B101/A201 excerpts), schedules, correspondence — requiring cross-referencing for answers
- **Difficulty gradient**: CS3 (Library) is E-M, CS1 (Riverfront) is M-H, CS2 (Courthouse) is M-H with interconnected issues
- **Answer key is separate** from questions to prevent accidental spoilers
- **Validation report is transparent** — documents what was checked, what was corrected during generation, and what domain uncertainties remain (AIA section numbers, LEED version specifics, jurisdiction-specific regulations)

### Review Requested
1. **Realism check** — Do the scenarios feel like real projects or are they too clean / too contrived?
2. **Question quality** — Are the distractors plausible? Do questions genuinely require cross-referencing?
3. **Accuracy flags** — Any AIA contract references, regulatory processes, or cost figures that seem off?
4. **Validation methodology** — Is the simulated multi-agent validation workflow documented clearly enough to be reproducible?

---

## 2. Project Registry & Builder Integration (Design — Pending Approval)

Don's second request: implement a structured Project Registry to replace the hardcoded project/domain mapping in the Builder.

### Problem
- `projects.json` only has id/name/path/color — no domain, description, or agent defaults
- `getDomainForProject()` in `builder.js` is a hardcoded 2-entry lookup table
- Adding new projects (like "Study Guide") requires code changes
- Naming drift risk: "Study Guide" vs "StudyGuide" vs "study-guide"

### Proposed Solution

**New file: `project-registry.json`**
Rich project metadata — projectId, projectName, domain, description, defaultAgents, status (active/incubating/archived), createdOn, tags.

**New module: `project-registry.js`**
Service layer with: `loadProjectRegistry()`, `saveProject()`, `validateProject()`, `getProjectById()`, `getDomainForProject()`. Replaces the hardcoded lookup in builder.js.

**Builder UI changes:**
- Replace PROJECT/DOMAIN text inputs with a project dropdown populated from registry
- DOMAIN auto-fills on project selection
- "+ New Project" option opens an inline creation form (name, domain, description, agents)
- Validation prevents duplicate IDs/names, normalizes naming

**Server endpoints:**
- `GET /api/project-registry` — serve the registry
- `POST /api/project-registry` — create new project, validate, persist

**Backward compatibility:**
- `projects.json` stays as-is (viewer project list with path/color for file loading)
- Registry is the authoritative source for metadata
- Manual PROJECT text entry still works as fallback

### Review Requested
1. **Schema** — Is the `project-registry.json` schema sufficient? Missing fields? Over-engineered?
2. **Relationship to `projects.json`** — Should we merge them or keep separate? I chose separate (registry = metadata, projects.json = file paths + colors for the viewer loader). Does that create confusion?
3. **Builder UX** — Dropdown + inline create vs. dropdown + modal? I went with inline to avoid interrupting the message composition flow.
4. **Future extensibility** — Don mentioned default routing rules, storage paths, message ID prefixes, and project-specific templates as future considerations. Should any of these be included now as empty/optional fields, or keep the schema minimal and extend later?

---

## Open Questions for Lodestar

- On the study module: Should we build a more formal multi-agent review pipeline (e.g., an n8n workflow that routes generated content through review agents), or is the simulated validation sufficient for this use case?
- On the registry: Any concerns about the service layer pattern? The existing codebase uses plain functions (no classes) — I'm following that convention rather than introducing a class-based model.

---END---
