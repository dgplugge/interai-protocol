$PROTO: AICP/1.0
$TYPE: REQUEST
$ID: MSG-0047
$REF: NONE
$SEQ: 49
$FROM: Don
$TO: Pharos
$TIME: 2026-03-30T18:10:00-04:00
$TASK: Implement Project Registry and Builder "Create Project" workflow
$STATUS: PENDING
$ROLE: Orchestrator
$INTENT: Introduce structured project management into AICP system for multi-domain scalability
PROJECT: InterAI-Protocol
DOMAIN: Multi-Agent Systems

---PAYLOAD---

CONTEXT:
The AICP system is expanding beyond a single project into multiple domains (e.g., Operator Hub, Study Guide, InterAI Protocol). Manual entry of PROJECT and DOMAIN fields is becoming inconsistent and non-scalable.

OBJECTIVE:
Design and implement a lightweight Project Registry and integrate it into the AICP Builder workflow.

REQUIREMENTS:

1. PROJECT REGISTRY
- Create a persistent JSON-based registry (e.g., project-registry.json)
- Each project should include:
  - projectId (machine-readable)
  - projectName (display name)
  - domain
  - description
  - defaultAgents
  - status (active/incubating/archived)
  - createdOn (timestamp)
  - optional tags

2. BUILDER INTEGRATION
- Add dropdown to select existing project
- Add "Create New Project" option
- When selected:
  - Open input form (name, domain, description, default agents)
  - Validate inputs
  - Save to registry
  - Immediately populate PROJECT and DOMAIN fields

3. SYSTEM DESIGN
- Implement separation of concerns:
  - ProjectRegistryModel
  - ProjectRegistryService
  - UI integration layer
- Suggested service methods:
  - loadProjects()
  - saveProject(project)
  - validateProject(project)
  - getProjectById(id)

4. BEHAVIOR
- Maintain backward compatibility with manual PROJECT entry
- Prevent duplicate project names or IDs
- Normalize naming (avoid drift such as "Study Guide" vs "StudyGuide")

5. FUTURE EXTENSIBILITY (design consideration only)
- Allow later addition of:
  - default routing rules
  - storage paths
  - message ID prefixes
  - project-specific templates

DELIVERABLE:
- Updated Builder UI with project selection and creation
- project-registry.json structure and sample entries
- Service layer implementation
- Brief explanation of how projects are loaded, validated, and used in message generation

NOTE:
This enhancement supports transition of AICP from single-project workflow to multi-project operating system.

---END---
