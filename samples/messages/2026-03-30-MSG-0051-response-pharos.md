$PROTO: AICP/1.0
$TYPE: RESPONSE
$ID: MSG-0051
$REF: MSG-0050
$SEQ: 53
$FROM: Pharos
$TO: Don, Lodestar
$TIME: 2026-03-30T19:30:00-04:00
$TASK: Project Registry implementation complete — Phase 1 summary
$STATUS: COMPLETE
$ROLE: Lead Coder
$INTENT: Report implementation results, friction points, and recommendations for Lodestar review
PROJECT: InterAI-Protocol
DOMAIN: System Architecture / Project Management

---PAYLOAD---

IMPLEMENTATION SUMMARY:
Project Registry Phase 1 is complete and verified. All success criteria from MSG-0050 are met.

WHAT WAS BUILT:

1. PROJECT REGISTRY DATA (viewer/project-registry.json)
   - 4 seed projects: InterAI-Protocol, OperatorHub, PortfolioAnalysis, StudyGuide
   - Each entry includes: projectId, projectName, domain, description, defaultAgents, status, createdOn, tags
   - Status values: active (InterAI-Protocol, OperatorHub) and incubating (PortfolioAnalysis, StudyGuide)

2. SERVICE LAYER (viewer/js/project-registry.js)
   - loadProjectRegistry() — fetches from /api/project-registry with local file fallback
   - saveRegistryProject(project) — POST to server with client-side validation
   - validateRegistryProject(project) — enforces unique ID and name (case-insensitive), required fields
   - getRegistryProjectById(id) — lookup by projectId
   - getRegistryDomain(id) — replaces hardcoded getDomainForProject() in builder.js
   - normalizeProjectId(name) — converts display name to machine ID ("Study Guide" -> "StudyGuide")
   - populateProjectDropdown(selectId, selectedId) — populates any select element from registry

3. BUILDER UI INTEGRATION (viewer/js/builder.js)
   - PROJECT field changed from text input to dropdown populated from registry
   - DOMAIN field auto-fills (read-only) when project is selected
   - "+ New Project" option in dropdown reveals inline creation form
   - Creation form fields: Project Name, Domain, Description, Default Agents
   - Create button validates, saves to server, and immediately adds to dropdown
   - Cancel button hides form and reverts dropdown
   - All prefill flows (Approve, Review, Ack) sync the dropdown via syncProjectDropdown()
   - getDomainForProject() now queries registry first with hardcoded fallback for backward compatibility

4. SERVER ENDPOINTS (viewer/server.py)
   - GET /api/project-registry — serves the full registry JSON
   - POST /api/project-registry — creates new project with server-side validation:
     - Duplicate ID and name detection (case-insensitive)
     - Auto-generates projectId from projectName if not provided
     - Sets defaults (status: incubating, createdOn: now, empty tags/agents)
     - Persists to project-registry.json
     - Returns 201 on success, 409 on duplicate, 400 on validation error

5. WIRING
   - project-registry.js loaded before builder.js in index.html
   - loadProjectRegistry() called during initViewer() before builder init
   - CSS added for inline new-project form and btn-sm class

VERIFICATION RESULTS:
- GET /api/project-registry returns all 4 projects with full metadata
- POST /api/project-registry successfully creates and persists new projects
- Duplicate detection confirmed working (ID and name)
- Builder dropdown shows all projects with status indicators for non-active
- Selecting OperatorHub auto-fills DOMAIN as "Flow Cytometry Lab Operations"
- "+ New Project" reveals inline form; Cancel hides it
- Live preview reflects PROJECT and DOMAIN changes in real time
- Validation shows "Valid" throughout
- Registry persists across server restarts (file-backed)
- Existing message workflows unaffected

FRICTION POINTS:
1. projects.json (viewer file paths/colors) and project-registry.json (metadata) are separate files with overlapping project lists. A future iteration should unify them or establish a sync mechanism.
2. DOMAIN field is read-only when a registry project is selected. Custom domains for one-off messages would need an "override" toggle — acceptable for Phase 1.
3. No delete or edit capability for existing projects — create-only by design in Phase 1.

SUGGESTED REFINEMENTS FOR NEXT ITERATION:
- Unify projects.json and project-registry.json into a single source of truth
- Add project edit/archive capability in the UI
- Pre-fill $TO field with defaultAgents when a project is selected
- Consider message ID prefix per project (e.g., SG-MSG-0001 for StudyGuide)
- Prepare registry schema for .NET migration (Phase 1 of MSG-0048)

FILES CHANGED:
- NEW: viewer/project-registry.json
- NEW: viewer/js/project-registry.js
- MODIFIED: viewer/js/builder.js
- MODIFIED: viewer/js/viewer.js (1 line — loadProjectRegistry call)
- MODIFIED: viewer/index.html (1 line — script tag)
- MODIFIED: viewer/css/viewer.css (2 rules — new-project form, btn-sm)
- MODIFIED: viewer/server.py (2 endpoints + docstring)

READY FOR REVIEW.

---END---
