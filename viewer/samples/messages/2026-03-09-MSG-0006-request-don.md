$PROTO: AICP/1.0
$TYPE: REQUEST
$ID: MSG-0006
$REF: MSG-0005
$SEQ: 6
$FROM: Don
$TO: Pharos, Lodestar
$TIME: 2026-03-09T08:25:00-05:00
$TASK: Design and implement MVP viewer app skeleton
$STATUS: PENDING
$PRIORITY: HIGH
$ROLE: Orchestrator
$INTENT: Create the first practical interface for viewing and managing the shared Inter-AI journal
PROJECT: InterAI-Protocol
DOMAIN: Multi-Agent Systems

---PAYLOAD---

Selected Task:
D. Viewer app skeleton

Scope for this first trial:
Build the smallest useful viewer app skeleton for the Inter-AI Protocol journal.

Goals:
1. Read journal/message files from a local folder
2. Display messages in chronological order
3. Show message metadata clearly
4. Show payload content in a readable panel
5. Keep architecture simple and expandable

Constraints:
- This is an MVP skeleton, not a full production app
- Prefer simple local-first design
- Avoid overengineering
- No overlapping edits between agents
- Pharos is Lead Coder
- Lodestar is Lead Designer and Reviewer

Questions for Pharos:
1. What platform do you recommend for the skeleton?
   - .NET desktop app
   - local web app
   - other
2. What minimal folder/file format should the viewer read first?
   - markdown message files
   - JSON packets
   - hybrid
3. What project structure do you recommend for MVP?
4. What exact first implementation slice should be built?

Instruction:
Please respond with:
- recommended platform
- minimal architecture
- first implementation slice
- any assumptions
- whether Don should now move into CodeEx

Lodestar will review the proposed design before implementation begins.

---END---

$SUMMARY: Don selected Task D, the viewer app skeleton, as the first applied
workflow test. Pharos is asked to propose platform, architecture, file format,
first slice, assumptions, and whether to move into CodeEx.
