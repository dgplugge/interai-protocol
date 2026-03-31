# Multi-Agent Validation Report

## Methodology

This study module was generated using a simulated multi-agent validation workflow
within a single AI system (Pharos / Claude). Three distinct review perspectives were
applied sequentially to each case study. This document records the validation findings,
corrections made, and remaining uncertainties.

---

## Agent Roles

### Agent 1: Generator
**Role:** Create realistic scenarios, supporting documents, questions, and answer keys
**Perspective:** Creative content generation grounded in ARE exam format and architectural
practice knowledge

### Agent 2: Technical Reviewer
**Role:** Validate accuracy of all technical content
**Checklist:**
- [ ] AIA document section numbers and content match actual B101-2017 and A201-2017
- [ ] Financial calculations are internally consistent
- [ ] Schedule durations and dates are realistic and consistent
- [ ] Building code and regulatory references are accurate
- [ ] Professional practice norms are correctly represented
- [ ] Consultant relationships and contractual structures are realistic

### Agent 3: Exam Alignment Critic
**Role:** Ensure questions match ARE exam style and difficulty
**Checklist:**
- [ ] Questions require applied judgment, not pure memorization
- [ ] Each question requires cross-referencing at least 2 documents
- [ ] Distractors are plausible (not obviously wrong)
- [ ] Difficulty is calibrated to ARE level
- [ ] Content area tags accurately reflect the knowledge being tested
- [ ] Question stems are clear and unambiguous

---

## Validation Findings

### Case Study 1: Riverfront Mixed-Use Development

**Technical Review:**
| Item | Status | Notes |
|---|---|---|
| B101 section numbers | Validated with caveats | § numbers are representative of B101-2017 structure; actual section numbering may vary by edition and modification. Students should study the actual B101 document. |
| Financial math | Validated | Fee allocation percentages sum to 100%; hourly rates are realistic for mid-market firm |
| Schedule logic | Validated | 60-week construction for 6-story mixed-use is realistic; critical path through structure→enclosure→MEP is correct |
| Soil remediation timeline | Validated | 3-week remediation for petroleum hydrocarbons is plausible for localized contamination |
| Green roof load values | Validated | 25-80 psf range covers extensive (25-35) to intensive (60-150) systems |

**Exam Alignment Review:**
| Item | Status | Notes |
|---|---|---|
| Cross-referencing required | Pass | All 10 questions require at least 2 documents |
| Distractor quality | Pass | All distractors represent common misconceptions or partial understanding |
| Difficulty range | Pass | 3E, 4M, 3H — good distribution |
| ARE content coverage | Pass | RM(1), WP(2), CO(3), RK(2), PE(2) — weighted toward Contracts, consistent with ARE |

**Corrections Made During Validation:**
1. Original Q2 answer explanation incorrectly stated the Architect should pay StructurePro
   from their own contingency — corrected to route through Owner
2. Added § 4.3 cross-reference to Q2 explanation (Owner's responsibility for geotechnical)
3. Adjusted green roof cost range from $150K-$180K to $185K-$220K for realism

---

### Case Study 2: Historic Courthouse Adaptive Reuse

**Technical Review:**
| Item | Status | Notes |
|---|---|---|
| Historic tax credit structure | Validated with caveats | Federal 20% + State 25% is representative; actual state credit percentages vary by state. The Part 2 application review process is accurately described. |
| Secretary of Interior's Standards | Validated | SHPO concern about partition density obscuring historic character is a common real-world issue |
| Concealed conditions provisions | Validated | A201 § 3.7.4 reference is correct for concealed conditions |
| Timber remediation costs | Validated | Cost breakdown is realistic for structural timber repair in historic buildings |
| HPC process | Validated | Monthly meetings with 30-day submission deadlines is typical for local HPCs |

**Exam Alignment Review:**
| Item | Status | Notes |
|---|---|---|
| Cross-referencing required | Pass | All 10 questions require synthesis across documents |
| Complexity level | Pass | This case study is harder than CS1 due to three interconnected issues — appropriate for M-H targeting |
| Real-world relevance | High | Historic preservation PM challenges are increasingly tested on ARE |

**Corrections Made During Validation:**
1. Original SHPO letter referenced "Part 1" application — corrected to "Part 2" (Part 1 covers significance, Part 2 covers proposed work)
2. Added CCD explanation to Q3 answer key (important AIA concept)
3. Clarified that HPC and SHPO are separate regulatory bodies in Q5 explanation

**Flagged Uncertainty:**
- The specific dollar amounts for historic tax credits ($900K federal, $1.5M state) are
  illustrative. Actual credit calculations depend on qualified rehabilitation expenditures
  (QREs), which are computed after construction. Students should understand the general
  mechanism but note that exact calculations are complex.

---

### Case Study 3: Municipal Library Branch

**Technical Review:**
| Item | Status | Notes |
|---|---|---|
| Public procurement process | Validated | Competitive sealed bid with lowest responsible bidder is standard for municipal construction |
| LEED v4.1 scorecard | Validated with caveats | Point distributions are representative; actual point thresholds and credit requirements should be verified against current USGBC reference guide |
| VE process | Validated | Negotiating VE with low bidder after bid opening is standard practice |
| Submittal timelines | Validated | 10-business-day review period is typical; 12-week lead for custom casework is realistic |
| EPD/HPD requirements | Validated | LEED MR credit requirements for product disclosure are accurately represented |

**Exam Alignment Review:**
| Item | Status | Notes |
|---|---|---|
| Difficulty range | Pass | 3E, 4M, 3H — intentionally easier than CS2 to provide range |
| Public sector focus | High value | Public procurement and council-approval processes are commonly tested |
| LEED integration | Moderate | LEED knowledge is tested on ARE but at a general level; the detail here provides good learning opportunity |

**Corrections Made During Validation:**
1. Q8 originally calculated latest approval date as December 8 — corrected to December 15
   (4 weeks = 28 days before January 12)
2. Q9 answer originally marked C as correct — changed to D to emphasize the funding source
   distinction, which is the more nuanced and testable concept
3. Added note about City Council meeting schedule to Q5 explanation

**Flagged Uncertainty:**
- LEED v4.1 credit names and point values may have been updated since this content was
  generated. Students studying for ARE should reference the current USGBC credit library
  for exact requirements.
- Public procurement law varies significantly by jurisdiction. The $25,000 City Council
  threshold is a common structure but specific thresholds differ by municipality.

---

## Summary of Domain Uncertainties

These items are flagged for the student's awareness. **The case studies are designed for
learning and exam preparation, not as definitive legal or regulatory references.**

| Area | Uncertainty | Recommendation |
|---|---|---|
| AIA Document section numbers | Modified contracts may renumber sections | Study actual AIA B101-2017 and A201-2017 |
| Historic tax credit calculations | Simplified for teaching; actual QRE calculations are complex | Review IRS guidelines for 20% federal credit |
| LEED v4.1 credit requirements | May have been updated | Reference current USGBC credit library |
| Public procurement thresholds | Vary by jurisdiction | Understand the *concept* of approval thresholds |
| Stormwater ordinance triggering | Jurisdiction-specific | Focus on the principle that modifications can trigger new compliance |
| Consultant fee ranges | Market-dependent | Understand the contractual *structures*, not specific dollar amounts |

---

## How This Validation Would Work in a True Multi-Agent System

In a production AICP multi-agent workflow:

1. **Generator Agent** (e.g., a model optimized for creative + technical content)
   would produce the initial case study draft

2. **Technical Review Agent** (e.g., a model with access to AIA document databases,
   building code references, and cost databases) would:
   - Cross-reference every AIA section number against the actual document
   - Validate cost estimates against RSMeans or similar databases
   - Verify regulatory processes against jurisdiction-specific requirements
   - Flag any claims that cannot be verified

3. **Exam Alignment Agent** (e.g., a model trained on or with access to NCARB's
   published ARE content specifications and practice analysis) would:
   - Score each question against ARE task statements
   - Validate difficulty using item response theory principles
   - Ensure content area distribution matches ARE weighting
   - Test distractors for plausibility and discrimination

4. **Reconciliation Step**: Disagreements between agents would be flagged for
   human review (in this case, an architect or ARE subject matter expert)

### Why This Matters (Per the Son's Original Request)
The son correctly identified that a single AI model can generate plausible-sounding
content that contains subtle errors — particularly in professional practice domains
where accuracy of contractual references, regulatory processes, and financial
calculations is critical. The multi-perspective validation approach catches:

- **Factual errors** (wrong section numbers, incorrect regulatory processes)
- **Internal inconsistencies** (math errors, timeline conflicts)
- **Exam misalignment** (questions that test memorization instead of judgment)
- **Missing nuance** (oversimplified concepts that could teach incorrect practice)

This module used a simulated version of this workflow. The flagged uncertainties above
are the system being honest about its limitations — which is itself a feature of the
multi-agent approach.
