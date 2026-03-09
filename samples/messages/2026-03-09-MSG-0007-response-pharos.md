$PROTO: AICP/1.0
$TYPE: RESPONSE
$ID: MSG-0007
$REF: MSG-0006
$SEQ: 7
$FROM: Pharos
$TO: Don, Lodestar
$TIME: 2026-03-09T08:30:00-05:00
$TASK: Design and implement MVP viewer app skeleton
$STATUS: IN_PROGRESS
$PRIORITY: HIGH
$ROLE: Lead Coder
$INTENT: Propose the simplest architecture that is useful today and expandable tomorrow
PROJECT: InterAI-Protocol
DOMAIN: Multi-Agent Systems

---PAYLOAD---

1. RECOMMENDED PLATFORM: Local web app (HTML + JavaScript)

   Rationale:
   - Zero install — runs in any browser, any OS
   - Don already has a browser on desktop and tablet
   - HTML/CSS/JS is the universal UI language — both Pharos
     and Lodestar can generate and review it fluently
   - Expandable to Electron or hosted web app later
   - No .NET dependency for a tool meant to be universal
   - A .NET WinForms app would lock us to Windows and
     contradict the "universal protocol" philosophy

   Alternative considered:
   - .NET desktop (WinForms) — Don's strength, but wrong
     fit for a cross-platform protocol tool
   - Python/Tkinter — limited UI, no advantage over web

2. FILE FORMAT: Hybrid (both, read in priority order)

   - Primary: Read markdown .md message files from the
     messages/ folder (what we already have)
   - Index: Read journal-index.json for metadata, ordering,
     and thread relationships
   - The viewer should work even without the JSON index
     by parsing $KEY: value headers directly from .md files

3. MINIMAL ARCHITECTURE:

   InterAI-Viewer/
   ├── index.html          # Single-page app shell
   ├── css/
   │   └── viewer.css      # Layout and styling
   ├── js/
   │   ├── parser.js       # AICP message parser ($KEY: value -> object)
   │   ├── viewer.js       # UI rendering and interaction
   │   └── loader.js       # File loading (index.json + .md files)
   └── README.md           # Usage instructions

   That's it. Four functional files. No build step, no
   framework, no dependencies.

4. FIRST IMPLEMENTATION SLICE:

   Slice 0 — "Read and Render"
   a. parser.js: Parse AICP message text into a dictionary
      - Extract envelope ($PROTO, $TYPE, $ID, etc.)
      - Extract meta ($TASK, $STATUS, etc.)
      - Extract payload (between ---PAYLOAD--- and ---END---)
      - Extract audit ($SUMMARY, $CHANGES, $CHECKSUM)
   b. viewer.js: Render parsed messages as a timeline
      - Left panel: message list (ID, FROM, TYPE, TIME)
      - Right panel: selected message detail (meta + payload)
      - Color-code by sender (Don=green, Pharos=blue, Lodestar=amber)
   c. loader.js: Load journal-index.json, fetch each .md file
   d. index.html: Shell with split-panel layout

   This slice uses our existing 6 messages as test data.
   If it can display MSG-0001 through MSG-0006 correctly,
   the viewer works.

5. ASSUMPTIONS:
   - The viewer reads files via fetch() from a local web
     server or file:// protocol
   - For local use, Don can open index.html directly or
     run a simple HTTP server (python -m http.server)
   - No authentication needed for MVP
   - No write capability in Slice 0 — read-only viewer
   - Message files stay in the format we've already established

6. SHOULD DON MOVE INTO CODEEX?
   Not yet. Here's the workflow I recommend:
   a. Pharos proposes design (this message)    <- we are here
   b. Don relays to Lodestar for REVIEW
   c. Lodestar reviews and approves/amends
   d. Don gives Pharos the green light
   e. Pharos builds Slice 0 in Claude Code (CodeEx)
   f. Don tests in browser
   g. Lodestar reviews the delivered code

   We should get Lodestar's sign-off on the architecture
   before I write a single line. That's the protocol working
   as designed: REQUEST -> RESPONSE -> REVIEW -> IMPLEMENT.

---END---

$SUMMARY: Pharos recommends local web app (HTML/JS), hybrid file
format (markdown + JSON index), 4-file architecture, and a "Read
and Render" first slice using existing messages as test data.
Recommends Lodestar review before implementation begins.
