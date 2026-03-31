$PROTO: AICP/1.0
$TYPE: RESPONSE
$ID: MSG-0065
$REF: NONE
$SEQ: 77
$FROM: Pharos
$TO: Don, Lodestar
$TIME: 2026-03-31T09:30:00-04:00
$TASK: Capture best-practice project organization guidance for Visual Studio 2026 workspaces
$STATUS: COMPLETE
$ROLE: Lead Coder
$INTENT: Provide a reusable, agent-readable summary of root separation, repository boundaries, and AICP thread conventions
PROJECT: InterAI-Protocol
DOMAIN: Multi-Agent Systems / Project Organization

---PAYLOAD---

CONTEXT:
The user requested best-practice guidance for organizing multiple software efforts under H:\Code and asked that recommendations be captured as a proper AICP message for agent consumption.

RECOMMENDED ROOT SEPARATION:
- H:\Code\interai-protocol
- H:\Code\study-guide-app
- H:\Code\study-materials
- H:\Code\operator-hub

RATIONALE:
- Prevent cross-project coupling caused by nesting unrelated apps under one root
- Keep branching, CI/CD, releases, and ownership independent per product
- Simplify Visual Studio solution loading and dependency management

CORE ORGANIZATION RULES:
1. One product = one repository = one primary solution (.sln)
2. Keep production code and tests separated:
   - src/
   - tests/
3. Maintain shared baseline folders/files in each repository:
   - docs/
   - scripts/
   - .github/workflows/
   - README.md
   - .editorconfig
   - Directory.Build.props
   - Directory.Packages.props
4. Treat interai-protocol as shared contract/protocol package consumed by other projects via versioned releases, not source-copying
5. Keep environment-specific values outside code; commit templates only (for example .env.example)

AICP THREAD NAMESPACE GUIDANCE:
- aicp.interai-protocol.*
- aicp.study-guide.*
- aicp.operator-hub.*

REQUIRED ENVELOPE FIELDS FOR CROSS-AGENT CONSISTENCY:
- projectId
- threadId
- messageType
- correlationId
- schemaVersion
- timestamp

SCRIPT LOCATION GUIDANCE:
- Shared automation scripts: H:\Code\PowerShell
- Project-specific wrappers: <repo>\scripts
- Execute with explicit full paths to avoid working-directory ambiguity

EXECUTION ORDER:
1. Move study-guide-app and study-materials out of interai-protocol
2. Normalize operator-hub root path naming
3. Ensure one git repo per root
4. Ensure one .sln per repo
5. Apply namespace/thread conventions in AICP traffic

NOTES:
No protocol breaking changes are required for this organizational improvement.

---END---
