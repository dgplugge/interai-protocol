# ARE Project Management — AI-Assisted Study System

## System Design Overview

This study module uses a **multi-agent generation and validation workflow** to produce
exam-aligned case studies for the ARE 5.0 Project Management division. The system is
designed to be **reusable** across all seven ARE divisions and adaptable for other
professional licensing exams.

---

## How This Study Module Works

### Structure Per Case Study
Each case study contains:

| Component | Purpose |
|---|---|
| **Scenario Narrative** | Sets the project context — client, scope, timeline, team, and emerging issues |
| **Supporting Document A** | Contract excerpt (based on AIA standard forms) |
| **Supporting Document B** | Schedule, budget, or payment application |
| **Supporting Document C** | Correspondence (emails, RFIs, meeting minutes) |
| **10 Questions** | Mix of multiple choice, scenario-based, and analytical |
| **Answer Key** | Justification + specific document cross-references |

### Question Design Philosophy
ARE questions test **applied judgment**, not memorization. Every question in this module
requires the student to:
1. Understand the scenario context
2. Locate relevant information across 2+ documents
3. Apply professional knowledge to select the best course of action

Questions are tagged by ARE 5.0 content area:
- **RM** — Resource Management
- **WP** — Project Work Planning
- **CO** — Contracts
- **RK** — Risk Management / Mitigation
- **PE** — Project Execution

### Difficulty Calibration
Questions are rated:
- **(E)** Entry — tests fundamental concepts
- **(M)** Mid — requires synthesis across documents
- **(H)** Hard — requires nuanced professional judgment with competing priorities

---

## ARE 5.0 Project Management — Division Overview

### What This Division Tests
The architect's role in **managing project resources, contracts, schedules, budgets,
and risk** from pre-design through construction administration.

### Key AIA Documents Referenced
| Document | Title | Relevance |
|---|---|---|
| **B101-2017** | Owner-Architect Agreement | Scope, compensation, responsibilities |
| **A101-2017** | Owner-Contractor Agreement | Contractor obligations, payment terms |
| **A201-2017** | General Conditions | Roles, change orders, claims, insurance |
| **G701-2017** | Change Order | Formalizing scope/cost/time changes |
| **G702/G703** | Application for Payment | Contractor pay requests, schedule of values |
| **E203-2013** | Building Information Modeling Exhibit | Digital deliverable expectations |

### Content Area Weightings (approximate)
- Resource Management: ~18%
- Project Work Planning: ~22%
- Contracts: ~24%
- Risk Management: ~18%
- Project Execution: ~18%

---

## Multi-Agent Validation Workflow

See `06-validation-report.md` for the full validation methodology and findings.

### Summary
Three agent perspectives review every case study:

1. **Generator** — Creates scenario, documents, questions, and answers
2. **Technical Reviewer** — Validates AIA document accuracy, industry realism,
   code/regulation references, and mathematical consistency
3. **Exam Alignment Critic** — Ensures question format matches ARE style,
   difficulty is appropriate, distractors are plausible, and cross-referencing
   is genuinely required

---

## How to Study With This Module

### Recommended Approach
1. **Read the scenario** carefully — take notes on key dates, dollar amounts, and relationships
2. **Study each supporting document** — highlight terms, conditions, and deadlines
3. **Attempt all 10 questions** without looking at the answer key
4. **Cross-reference your answers** against the documents before checking the key
5. **Review the answer key** — focus on the *reasoning*, not just the correct letter
6. **Re-read any AIA contract sections** you found unfamiliar

### Time Targets
- Scenario + documents review: 20–30 minutes
- 10 questions: 30–40 minutes
- Answer review: 15–20 minutes
- **Total per case study: ~60–90 minutes**

---

## Reuse for Other ARE Divisions

This system can generate case studies for any ARE 5.0 division by adjusting:
- **Scenario domain** (e.g., structural for PA, zoning for PPD)
- **Supporting documents** (e.g., code excerpts for PA, site plans for PPD)
- **Question tags** to match that division's content areas
- **Reference documents** to the relevant AIA forms and standards

### Future Divisions
| Division | Potential Scenario Types |
|---|---|
| Practice Management | Firm operations, staffing, business planning |
| Programming & Analysis | Client needs assessment, site analysis, code research |
| Project Planning & Design | Schematic design, design development, coordination |
| Project Development & Documentation | Construction documents, specifications, detailing |
| Construction & Evaluation | CA site visits, submittals, punchlist, closeout |

---

## Case Studies in This Module

| # | Title | Focus Areas | Difficulty |
|---|---|---|---|
| 1 | Riverfront Mixed-Use Development | Schedule management, change orders, consultant coordination | M–H |
| 2 | Historic Courthouse Adaptive Reuse | Risk management, unforeseen conditions, owner communication | M–H |
| 3 | Municipal Library Branch | Public procurement, budget constraints, quality control | E–M |
