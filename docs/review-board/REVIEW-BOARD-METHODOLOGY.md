# Provena Foundry Review Board — Governing Methodology

**Document ID:** RBM-001  
**Version:** 1.0.0  
**Status:** ACTIVE  
**Applicability:** Provena Foundry releases only. This document does not govern GS-P001 or any other Provena product line.  
**Last Updated:** 2026-07-18  
**Owner:** Provena Foundry Governance  

---

## Table of Contents

1. [Purpose and Scope](#1-purpose-and-scope)
2. [Relationship to GS-P001](#2-relationship-to-gs-p001)
3. [Governing Principles](#3-governing-principles)
4. [Review Board Composition](#4-review-board-composition)
5. [Independence Rules](#5-independence-rules)
6. [Review Trigger Conditions](#6-review-trigger-conditions)
7. [Input Package Requirements](#7-input-package-requirements)
8. [Evidence Standards](#8-evidence-standards)
9. [Severity Classification](#9-severity-classification)
10. [Decision Framework](#10-decision-framework)
11. [Merge-Blocking Rules](#11-merge-blocking-rules)
12. [Disagreement Handling](#12-disagreement-handling)
13. [Finding Lifecycle](#13-finding-lifecycle)
14. [Remediation and Re-Review Process](#14-remediation-and-re-review-process)
15. [Audit Trail Requirements](#15-audit-trail-requirements)
16. [Versioning and Reproducibility](#16-versioning-and-reproducibility)
17. [Required Output Templates](#17-required-output-templates)
18. [Milestone-Completion Criteria](#18-milestone-completion-criteria)
19. [Reviewer Specification Index](#19-reviewer-specification-index)
20. [Document History](#20-document-history)

---

## 1. Purpose and Scope

### 1.1 Purpose

The Provena Foundry Review Board (the Board) is the formal gate-keeping body responsible for certifying that each build increment of Provena Foundry meets defined standards before it may be merged into a protected branch, published to any external environment, or counted as a completed milestone.

The Board exists because:

- Software quality assertions made by the team that produces the software are structurally compromised by confirmation bias, time pressure, and familiarity blindness.
- Commercial commitments depend on accurate, defensible quality signals. A missed defect discovered by a client costs substantially more than the cost of a thorough review.
- Reproducibility and traceability are non-negotiable properties of professional software. Reviews must themselves be traceable and reproducible.
- Honest rejection is more valuable than optimistic approval. A FAIL verdict that prompts correction is a net positive; a PASS verdict that masks a defect is a liability.

### 1.2 Scope

This methodology applies to:

- All pull requests and merge requests targeting protected branches of Provena Foundry repositories.
- All milestone-completion declarations for Provena Foundry.
- All production deployments of Provena Foundry.
- Any change to Provena Foundry that touches security controls, data contracts, public APIs, or commercial commitments.

This methodology explicitly does **not** apply to:

- GS-P001 or any product governed by a separate methodology.
- Internal development branches that have not yet entered formal review.
- Documentation-only changes that carry no functional impact (subject to a lightweight documentation review, not full Board review).

### 1.3 What the Board Is Not

The Board is not:

- A rubber-stamp process. A review without findings on a non-trivial change is suspicious and must be justified.
- A code review substitute. Developer peer review is a prerequisite, not a replacement.
- An AI opinion oracle. AI tools may assist reviewers in locating evidence but may not substitute for human judgement or generate findings unsupported by verifiable evidence.

---

## 2. Relationship to GS-P001

GS-P001 is a separate Provena product line with its own governance, methodology, and review processes. This document, all reviewer specifications derived from it, and all Board decisions, finding records, and audit logs produced under it are scoped exclusively to Provena Foundry.

Where Provena Foundry shares infrastructure, libraries, or data pipelines with GS-P001, the reviewer must identify the shared component, note which governance regime owns it, and limit findings to the Provena Foundry usage of that component. Findings must not be raised against GS-P001 assets under this methodology.

If a shared component is found to be defective and that defect originates in GS-P001–governed code, the finding is recorded as an **External Dependency Risk** and escalated through the appropriate GS-P001 channel. The Provena Foundry FAIL/PASS determination must account for the risk but must not conflate the two governance regimes.

---

## 3. Governing Principles

The following principles are non-negotiable and take precedence over convenience, schedule, or reviewer preference.

### P1 — Evidence Quality

Every finding must be supported by specific, verifiable evidence. Evidence must be:

- **Concrete:** A specific file path, line number, log entry, test output, metric value, or document reference.
- **Reproducible:** Any reviewer given the same artefact package and the same evidence pointer must be able to independently verify the finding.
- **Current:** Evidence must refer to the artefact under review, not a previous version or a similar project.

Assertions of the form "this probably has issues" or "this feels wrong" are not findings. They may prompt a reviewer to search for evidence, but they do not become findings until evidence is located.

### P2 — Traceability

Every finding, every decision, and every remediation must be traceable to:

- The specific artefact version under review (commit SHA, build hash, or equivalent immutable identifier).
- The reviewer who raised it.
- The evidence that supports it.
- The resolution applied (if any).

Traceability records are permanent. They must not be deleted, even if a finding is later superseded.

### P3 — Repeatability

A review conducted twice on the same artefact by different reviewers following the same specification must produce materially equivalent results. Where results diverge, the divergence itself must be recorded and resolved through the Disagreement Handling process (§12), not suppressed.

Reviewers must document their method sufficiently that another reviewer can reproduce their conclusions without access to the original reviewer.

### P4 — Commercial Relevance

Findings must be assessed in terms of commercial impact, not merely technical correctness. A technically sub-optimal implementation that carries no commercial risk may be a Minor finding. A technically conformant implementation that creates a commercial liability is at minimum a Major finding.

Commercial relevance includes: client-facing data accuracy, contractual SLA compliance, licensing obligations, data sovereignty, and reputational exposure.

### P5 — Deterministic Decisions

Board decisions must be deterministic given the finding set. The decision rules in §10 must produce a unique outcome for any given combination of findings. Reviewers and the Board must not override decision rules based on schedule pressure, optimism, or qualitative judgement outside the defined framework.

If the decision rules produce an outcome that appears wrong, the correct action is to review the evidence and findings, not to adjust the outcome. If the rules themselves are inadequate, the rules must be amended through the versioning process (§16) before the next review cycle.

### P6 — Honest Rejection

A FAIL verdict is not a failure of the review process. It is the review process working correctly. Reviewers who consistently find no issues on non-trivial artefacts will be asked to justify their methodology. Reviewers must not moderate finding severity downward to avoid a FAIL verdict.

### P7 — No Fabricated Evidence

Reviewers must not generate, infer, or construct evidence. If a required evidence item is absent from the artefact package, the reviewer must raise an **Evidence Gap** finding. An Evidence Gap is itself a finding with its own severity. The absence of a required test, the absence of a performance baseline, the absence of a security scan report — these are findings, not assumptions.

### P8 — No Opaque AI Judgement

AI tools may be used to assist search (e.g., locate all usages of a deprecated function, identify patterns in test output). AI tools must not:

- Generate finding text that the reviewer cannot independently verify.
- Make or influence severity determinations.
- Produce summary conclusions that substitute for reviewer analysis.
- Generate evidence (e.g., synthesised test results, inferred metrics).

Where a reviewer uses AI assistance, they must disclose this in their review report and confirm that every finding produced with AI assistance has been independently verified by them against the actual artefact.

---

## 4. Review Board Composition

### 4.1 Roles

| Role | Abbrev | Responsibility |
|------|--------|----------------|
| Board Chair | BC | Convenes reviews, enforces process, casts deciding vote in deadlock |
| Methodology Auditor | MA | Reviews specification conformance and process integrity |
| Software Architecture Auditor | SAA | Reviews structural and architectural correctness |
| Business and Commercial Auditor | BCA | Reviews commercial impact and contractual alignment |
| Data and Evidence Auditor | DEA | Reviews data quality, evidence integrity, and traceability |
| QA and Reliability Auditor | QRA | Reviews test coverage, defect management, and reliability |
| Security and Privacy Auditor | SPA | Reviews security controls and privacy obligations |
| Performance and Operations Auditor | POA | Reviews performance, scalability, and operational readiness |
| Sceptical Reviewer | SR | Challenges assumptions, probes for hidden risks, devil's advocate |

### 4.2 Quorum

A review requires the participation of at least:

- Board Chair (or designated deputy).
- Methodology Auditor.
- At least four of the seven specialist auditors, selected based on the nature of the artefact under review.
- The Sceptical Reviewer.

If a required auditor is unavailable, the Board Chair must document the absence and assign a qualified substitute. A review conducted without quorum is void.

### 4.3 Assignment

The Board Chair is responsible for assigning reviewers to each review cycle. Assignment must respect independence rules (§5). Assignments are documented in the Review Initiation Record before any reviewer begins work.

### 4.4 Human Reviewers

All Board roles must be filled by human reviewers. AI agents may operate as execution assistants (running searches, formatting reports) but may not hold a Board role, sign off on findings, or cast votes.

---

## 5. Independence Rules

### 5.1 Conflict of Interest

A reviewer must not review artefacts they authored, co-authored, or substantially specified. If a reviewer contributed to any component within scope, they must declare this in the Review Initiation Record and must be recused from reviewing that component.

### 5.2 Commercial Independence

A reviewer must not hold a commercial stake in the outcome of the review (e.g., a bonus tied to release, a client relationship that depends on approval). Where a potential commercial conflict exists, the reviewer must declare it. The Board Chair determines whether recusal is required.

### 5.3 Organisational Independence

For milestone reviews that determine commercial invoicing or contractual commitments, at least one reviewer per specialist discipline must be organisationally independent from the team that produced the artefact. "Organisationally independent" means not managed by the same direct line manager and not a member of the same development team.

### 5.4 Independence for Sceptical Reviewer

The Sceptical Reviewer must always be independent of the authoring team for major milestone reviews. For routine maintenance reviews, a senior reviewer who was not involved in the specific change may serve.

### 5.5 Declaration Requirement

Every reviewer must sign an Independence Declaration at the start of each review, confirming they have no disqualifying conflicts. This declaration is retained in the audit trail.

---

## 6. Review Trigger Conditions

A Board review is mandatory when any of the following conditions are met:

| Trigger | Threshold |
|---------|-----------|
| Milestone completion | Any milestone with commercial or contractual significance |
| Protected branch merge | Any PR targeting `main`, `release/*`, or equivalent |
| Production deployment | Any deployment to a production environment |
| Security change | Any change to authentication, authorisation, encryption, or access control |
| Data contract change | Any change to public API schemas, database schemas affecting external clients |
| Performance boundary change | Any change expected to alter throughput, latency, or resource consumption by >10% |
| Dependency upgrade | Any major version upgrade of a critical dependency |
| Post-incident change | Any change implementing a post-incident action item |

Routine development merges to non-protected branches do not require a full Board review but should undergo standard developer peer review.

---

## 7. Input Package Requirements

### 7.1 Mandatory Inputs

No review may begin without a complete Input Package. The following items are mandatory for all reviews:

| Item | Description |
|------|-------------|
| Artefact Identifier | Immutable identifier: commit SHA, build hash, or tagged release identifier |
| Scope Statement | Explicit statement of what is in and out of scope for this review |
| Change Summary | Author-provided description of what changed and why |
| Linked Requirements | References to the requirements, specifications, or stories addressed by this change |
| Test Evidence Package | All test results (unit, integration, end-to-end) produced by the CI pipeline for this artefact version |
| Dependency Manifest | Complete list of runtime dependencies with versions |
| Known Issues Register | Documented list of known defects and limitations as of the artefact version |
| Previous Review Record | If a re-review: the prior Board decision and the remediation evidence |

### 7.2 Conditional Inputs

| Condition | Additional Required Input |
|-----------|--------------------------|
| Contains security changes | Security scan results (SAST, DAST, dependency vulnerability scan) |
| Handles personal data | Privacy impact assessment |
| Has performance implications | Performance benchmark results with baseline comparison |
| Modifies data contracts | Schema migration plan and backward-compatibility analysis |
| Is a milestone completion | Commercial acceptance criteria confirmation from the business owner |

### 7.3 Input Package Validation

The Methodology Auditor validates the Input Package before any specialist review begins. If mandatory items are absent, the review is **deferred** (not failed) pending package completion. A deferral is recorded in the audit trail.

The deferral clock starts when the Input Package is deemed incomplete. If the package is not completed within five business days, the Board Chair must escalate.

---

## 8. Evidence Standards

### 8.1 Evidence Quality Tiers

All evidence submitted in support of a finding or a remediation must be classified by the reviewer into one of the following tiers:

| Tier | Name | Description |
|------|------|-------------|
| T1 | Direct Instrument | Artefact produced directly by an automated tool against the specific artefact under review (e.g., CI test log, static analysis report, benchmark output) |
| T2 | Direct Observation | Reviewer-executed procedure applied to the specific artefact under review, with documented steps and output |
| T3 | Documentary Reference | A written specification, contract, design document, or prior decision record that the artefact can be compared against |
| T4 | Reasoned Inference | A conclusion derived from T1–T3 evidence using explicitly stated reasoning |
| T5 | Assertion | A claim without supporting T1–T4 evidence |

### 8.2 Evidence Admissibility

| Context | Minimum Tier Required |
|---------|----------------------|
| Raising a Critical finding | T1 or T2 |
| Raising a Major finding | T1, T2, or T3 |
| Raising a Minor finding | T1, T2, T3, or T4 |
| Raising an Observation | T1–T4 |
| Closing a Critical finding | T1 or T2 demonstrating resolution |
| Closing a Major finding | T1, T2, or T3 demonstrating resolution |
| Closing a Minor finding | T1–T4 demonstrating resolution |

T5 evidence (assertion) is not admissible for any finding. A reviewer who relies on assertion must either locate supporting evidence (T1–T4) or record an Evidence Gap finding.

### 8.3 Evidence Capture Requirements

Evidence must be captured in a form that:

- Can be reproduced by a third party following documented steps.
- References the specific artefact version (commit SHA or equivalent).
- Is timestamped at the point of capture.
- Is retained in the audit trail and not overwritten by subsequent evidence.

---

## 9. Severity Classification

All findings are classified using the following severity scale. Severity is assigned by the reviewer who raises the finding and may be challenged through the Disagreement Handling process (§12).

### SEV-1 — Critical

A defect, gap, or non-conformance that:

- Creates a material risk of data loss, data corruption, or unauthorised data access.
- Violates a contractual, legal, or regulatory obligation.
- Prevents core functionality from operating correctly.
- Would cause the system to produce incorrect outputs in normal operating conditions.
- Represents a security vulnerability that could be exploited without insider access.

**Board Decision Impact:** A single SEV-1 finding that is Open or Contested results in an automatic FAIL. No exceptions.

### SEV-2 — Major

A defect, gap, or non-conformance that:

- Significantly degrades system reliability, performance, or data accuracy under foreseeable conditions.
- Violates a stated requirement or design specification without a recorded waiver.
- Creates a commercial risk that is not mitigated by the known issues register.
- Would require a non-trivial remediation effort and cannot be deferred without accumulating technical debt that is not disclosed.

**Board Decision Impact:** Two or more Open SEV-2 findings result in FAIL. One Open SEV-2 finding results in PASS WITH FINDINGS if a remediation plan with a committed timeline is in place.

### SEV-3 — Minor

A defect, gap, or non-conformance that:

- Reduces system quality, maintainability, or observability below desired standards.
- Represents a deviation from best practice that carries low but non-zero risk.
- Is bounded in impact and can be remediated in a subsequent release without commercial risk.

**Board Decision Impact:** Minor findings do not block merge but must be entered into the tracking register with target remediation dates.

### SEV-4 — Observation

A note, recommendation, or improvement opportunity that:

- Does not represent a defect or non-conformance.
- Is provided for the team's benefit to improve future work.

**Board Decision Impact:** Observations do not affect the Board decision. They are recorded for reference.

---

## 10. Decision Framework

### 10.1 Decision Outcomes

The Board may issue one of three decisions:

#### PASS

Conditions:
- No SEV-1 findings are Open or Contested.
- Zero or one SEV-2 findings are Open, and a remediation plan with committed timeline is in place for any Open SEV-2.
- All mandatory inputs were provided.
- All required reviewer roles were filled.

A PASS is not a declaration of perfection. It is a declaration that the artefact meets the defined quality threshold for the defined scope.

#### PASS WITH FINDINGS

Conditions:
- No SEV-1 findings are Open or Contested.
- One Open SEV-2 finding exists with an accepted remediation plan.
- All mandatory inputs were provided.

A PASS WITH FINDINGS permits merge but requires the Open finding to be tracked and resolved per the remediation timeline. Failure to remediate within the agreed timeline triggers an automatic escalation to the Board Chair and a mandatory re-review of the outstanding finding.

#### FAIL

Conditions (any one is sufficient):
- One or more SEV-1 findings are Open or Contested.
- Two or more SEV-2 findings are Open.
- The mandatory Input Package was fraudulently represented as complete when it was not.
- A reviewer independence violation was discovered during the review.
- Quorum was not maintained and the review was conducted anyway without Board Chair approval.

A FAIL requires the authoring team to remediate findings and resubmit for a full re-review.

### 10.2 Decision Authority

The Board decision is determined by the finding set per the rules in 10.1. It is not a vote. If the finding set produces a FAIL, the Board decision is FAIL. No override is permitted.

The Board Chair confirms and records the decision. If any reviewer disputes the finding record (not the outcome — the record), disputes are resolved through §12 before the decision is finalised.

### 10.3 Abstentions

A reviewer may not abstain from raising a finding they have identified. If a reviewer is uncertain whether a finding warrants raising, they must raise it at the severity they believe is most defensible and note their uncertainty. Findings may be challenged and re-classified but must not be suppressed.

---

## 11. Merge-Blocking Rules

### 11.1 Hard Blocks

The following conditions constitute hard merge blocks. No merge to a protected branch may proceed while any hard block is active.

| Block Condition |
|----------------|
| Board decision is FAIL |
| One or more SEV-1 findings are Open |
| Two or more SEV-2 findings are Open without an accepted remediation plan |
| The review has not been completed (quorum not met, review not initiated) |
| The artefact identifier has changed since the review was conducted |

### 11.2 Soft Blocks

The following conditions are soft blocks. They may be waived by the Board Chair with explicit written justification recorded in the audit trail.

| Soft Block Condition | Waiver Condition |
|---------------------|-----------------|
| One Open SEV-2 without remediation plan | Board Chair confirms a remediation plan will be submitted within one business day |
| Review conducted without full specialist complement | Board Chair confirms the missing specialist's scope was covered by another qualified reviewer |

Soft block waivers do not change the Board decision; they permit operational continuity while the condition is resolved.

### 11.3 Branch Protection Integration

For repositories using automated branch protection, the Board decision must be recorded in a machine-readable format (defined in §17) that can be consumed by branch protection rules. The merge-blocking mechanism must not rely solely on manual process.

---

## 12. Disagreement Handling

### 12.1 Types of Disagreement

| Type | Description |
|------|-------------|
| Finding Dispute | A reviewer disagrees with a finding raised by another reviewer (existence, severity, or evidence) |
| Decision Dispute | A reviewer disputes the Board decision as not following from the finding set |
| Process Dispute | A reviewer disputes the conduct of the review (independence violation, evidence fabrication, etc.) |

### 12.2 Finding Dispute Resolution

**Step 1 — Peer Resolution (24 hours)**  
The disputing reviewer contacts the finding owner directly. Both reviewers attempt to agree on finding disposition. If agreed: the finding record is updated with the agreed disposition and the rationale.

**Step 2 — Board Panel (48 hours from Step 1 failure)**  
If peer resolution fails, the Board Chair convenes a panel of three reviewers (excluding the disputing parties). The panel reviews the evidence and makes a binding determination. The determination is recorded.

**Step 3 — Board Chair Decision**  
If the panel cannot reach a unanimous determination, the Board Chair makes the final binding decision with written justification.

At no stage may a finding be suppressed during an active dispute. The finding remains Open and Contested until resolution. A Contested SEV-1 finding blocks merge.

### 12.3 Decision Dispute Resolution

A Decision Dispute can only be raised on the grounds that the decision does not follow from the finding set per §10. Schedule pressure, commercial impact, or team workload are not valid grounds.

The Board Chair reviews the finding record and the decision rules. If the decision is found to have been misapplied, it is corrected. If the decision correctly follows from the finding set, the dispute is closed with a written explanation.

### 12.4 Process Dispute Resolution

Process disputes (independence violations, evidence fabrication, deliberate suppression) are elevated to Provena Foundry governance leadership immediately. The affected review is suspended pending investigation. All findings from the affected reviewer are placed under review.

---

## 13. Finding Lifecycle

All findings follow this lifecycle. State transitions are permanent and append-only in the audit trail.

```
[OPEN]
   │
   ├── Contested (dispute raised) ──► [OPEN] (dispute resolved, finding confirmed)
   │                                ──► [WITHDRAWN] (dispute resolved, finding invalid)
   │
   ├── Remediation submitted ──► [UNDER REVIEW]
   │                                │
   │                                ├── Evidence accepted ──► [CLOSED]
   │                                └── Evidence rejected ──► [OPEN]
   │
   └── Board decision: not applicable to this review ──► [WAIVED] (SEV-3/4 only, requires justification)
```

### 13.1 Finding Record Fields

Each finding must be recorded with:

| Field | Description |
|-------|-------------|
| Finding ID | Unique identifier: `[Review ID]-[Reviewer Abbrev]-[Sequence]` |
| Review ID | Identifier of the review cycle |
| Reviewer | Name and role of the reviewer who raised the finding |
| Artefact Version | Immutable identifier of the artefact under review |
| Severity | SEV-1 through SEV-4 |
| Reviewer Spec Reference | Section of the reviewer specification that identifies this finding type |
| Finding Title | Concise description (≤ 80 characters) |
| Finding Detail | Full description with evidence references |
| Evidence Tier | T1–T5 per §8.1 |
| Evidence Reference | Specific pointers to evidence (file path, line number, log entry, document section) |
| Status | OPEN / CONTESTED / UNDER REVIEW / CLOSED / WITHDRAWN / WAIVED |
| Remediation Requirement | What must be demonstrated to close this finding |
| Target Resolution Date | Required for SEV-1 and SEV-2 |
| Closure Evidence | Evidence submitted to close the finding |
| Closure Reviewer | Who reviewed and accepted closure |
| Closure Date | When the finding was closed |

---

## 14. Remediation and Re-Review Process

### 14.1 Remediation Plan Requirements

For SEV-1 and SEV-2 findings, the authoring team must submit a Remediation Plan within two business days of a FAIL or PASS WITH FINDINGS decision. The plan must include:

- Root cause analysis for each finding.
- Specific changes to be made.
- Who is responsible for each change.
- Target completion date.
- How resolution will be evidenced (what T1/T2 evidence will be produced).

The Methodology Auditor reviews and accepts or rejects the Remediation Plan. A rejected plan must be resubmitted within one business day.

### 14.2 Re-Review Scope

A re-review is scoped to:

- Verification that each remediated finding has been resolved per its closure requirements.
- Assessment of whether the remediation introduced new defects within the scope of the original review.
- Confirmation that the artefact version identifier has changed since the original review.

A re-review is **not** a fresh full review unless the Board Chair determines that the remediation was so extensive that the original review is no longer applicable.

### 14.3 Re-Review Decision

A re-review produces a decision using the same framework as the original review, applied to the post-remediation finding set. If all SEV-1 and SEV-2 findings have been closed and no new findings of the same severity have been introduced, the re-review will produce a PASS or PASS WITH FINDINGS.

If the remediation introduced new SEV-1 or SEV-2 findings, the re-review produces a FAIL and the process repeats.

### 14.4 Remediation Timeout

If a SEV-1 finding has not been remediated within ten business days of the FAIL decision, the Board Chair must escalate to Provena Foundry governance leadership. The release associated with the failing artefact must be placed on hold until the finding is closed.

---

## 15. Audit Trail Requirements

### 15.1 Mandatory Records

The following records must be retained for every review:

| Record | Retention Period |
|--------|-----------------|
| Review Initiation Record (artefact ID, reviewers, trigger) | Permanent |
| Independence Declarations (all reviewers) | Permanent |
| Input Package validation record | Permanent |
| All Finding Records (including Withdrawn) | Permanent |
| All Reviewer Reports | Permanent |
| Disagreement records | Permanent |
| Remediation Plans | Permanent |
| Re-review records | Permanent |
| Board Decision Record | Permanent |
| Branch protection integration record | 7 years |

### 15.2 Immutability

Audit trail records are append-only. No record may be deleted, overwritten, or altered. Corrections must be made by adding a superseding record that references the original, not by modifying the original.

### 15.3 Storage Requirements

Audit records must be stored in a location that:

- Is access-controlled and auditable.
- Is backed up with a tested restore process.
- Is retained independent of the code repository (to survive repository deletion or migration).
- Is readable without proprietary software.

For Provena Foundry, audit records are maintained in the designated review archive (location defined in the operational runbook, separate from this document).

### 15.4 Audit Log Format

Each audit log entry must be structured with:

- Timestamp (ISO 8601, UTC).
- Actor (human reviewer name and role; system if automated).
- Event type (finding raised, finding updated, decision recorded, etc.).
- Payload (the record content).
- Previous record reference (for updates and supersessions).

---

## 16. Versioning and Reproducibility

### 16.1 Document Versioning

This methodology and all reviewer specifications are versioned using semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR:** Changes that alter decision outcomes for the same finding set (e.g., adding a new mandatory input, changing severity rules, changing decision criteria).
- **MINOR:** Changes that add clarification, add non-mandatory guidance, or add new finding types without changing existing decision rules.
- **PATCH:** Typographic corrections, cross-reference fixes, or formatting changes.

Every published version is retained in version control with an immutable tag. The version used for a given review is recorded in the Review Initiation Record and determines which rules apply for that review. A review conducted under version 1.0.0 is evaluated by the rules of version 1.0.0 even if a newer version has since been published.

### 16.2 Review Reproducibility

A review is reproducible if, given:

- The artefact version (immutable identifier).
- The version of this methodology.
- The version of each applicable reviewer specification.
- The Input Package.

A different reviewer following the same process would reach materially equivalent conclusions.

Reviews must be conducted and documented to this standard. Reviewer-specific insight or institutional knowledge that cannot be documented must not be relied upon as a primary basis for findings.

### 16.3 Artefact Versioning

The artefact under review must be identified by an immutable version identifier before the review begins. Reviews conducted against a moving target (e.g., an untagged branch tip) are void unless the commit SHA is captured at the time of review initiation and does not change during the review.

If the artefact changes during a review, the review must be restarted against the new artefact version. The previous partial review is recorded as void.

---

## 17. Required Output Templates

### 17.1 Template Index

| Template ID | Name | Owner | Used By |
|-------------|------|-------|---------|
| TPL-RIR | Review Initiation Record | Board Chair | All reviews |
| TPL-IND | Independence Declaration | Each reviewer | All reviews |
| TPL-IPV | Input Package Validation | Methodology Auditor | All reviews |
| TPL-FND | Finding Record | Each reviewer | Per finding |
| TPL-RRR | Reviewer Report | Each reviewer | All reviews |
| TPL-BDR | Board Decision Record | Board Chair | All reviews |
| TPL-RMP | Remediation Plan | Authoring team | FAIL/PASS WITH FINDINGS |
| TPL-RVR | Re-Review Record | Board Chair | Re-reviews |
| TPL-MRI | Machine-Readable Indicator | Board Chair | Branch protection |

### 17.2 Template: Review Initiation Record (TPL-RIR)

```
REVIEW INITIATION RECORD
=========================
Review ID:
Review Date:
Trigger Condition (§6):
Artefact Identifier (commit SHA or equivalent):
Repository:
Branch / Target:
Methodology Version:
Reviewer Spec Versions (list each):

Assigned Reviewers:
  Board Chair:
  Methodology Auditor:
  Software Architecture Auditor:
  Business and Commercial Auditor:
  Data and Evidence Auditor:
  QA and Reliability Auditor:
  Security and Privacy Auditor:
  Performance and Operations Auditor:
  Sceptical Reviewer:

Omitted Specialist Roles (with justification):

Input Package Location:
Input Package Validated (Y/N):
Input Package Validator:
Input Package Validation Date:
```

### 17.3 Template: Independence Declaration (TPL-IND)

```
INDEPENDENCE DECLARATION
=========================
Review ID:
Reviewer Name:
Reviewer Role:
Date:

I confirm that:
[ ] I did not author or co-author any component within the scope of this review.
[ ] I do not hold a commercial stake in the outcome of this review.
[ ] I am not managed by the same direct line manager as the authoring team
    (required for milestone reviews; mark N/A for routine reviews).
[ ] I have no other conflict of interest that would impair my independence.

If any item above is unchecked, describe the conflict and state whether
the Board Chair has approved participation despite the conflict:

[Conflict description if applicable]
[Board Chair approval reference if applicable]

Signature:
```

### 17.4 Template: Finding Record (TPL-FND)

```
FINDING RECORD
==============
Finding ID:
Review ID:
Reviewer:
Reviewer Role:
Artefact Version:
Date Raised:

Severity: [ ] SEV-1  [ ] SEV-2  [ ] SEV-3  [ ] SEV-4
Reviewer Spec Reference:
Finding Title (≤ 80 chars):

Finding Detail:
[Full description]

Evidence:
  Evidence Tier: [ ] T1  [ ] T2  [ ] T3  [ ] T4  [ ] T5
  Evidence Reference:
  [Specific file path / line / log entry / document section]

AI Assistance Used: [ ] Yes  [ ] No
If yes, describe what AI was used for and confirm independent verification:

Status: [ ] OPEN  [ ] CONTESTED  [ ] UNDER REVIEW  [ ] CLOSED  [ ] WITHDRAWN  [ ] WAIVED

Remediation Requirement:
[What must be demonstrated to close this finding]

Target Resolution Date:
[Required for SEV-1 and SEV-2]

--- Closure ---
Closure Evidence:
Closure Reviewer:
Closure Date:
Closure Decision: [ ] ACCEPTED  [ ] REJECTED
Rejection Reason (if rejected):
```

### 17.5 Template: Board Decision Record (TPL-BDR)

```
BOARD DECISION RECORD
=====================
Review ID:
Artefact Identifier:
Decision Date:
Board Chair:

Summary of Finding Set:
  SEV-1 Open:         [count]
  SEV-2 Open:         [count]
  SEV-2 Remediation Plans Accepted: [count]
  SEV-3 Open:         [count]
  SEV-4 Open:         [count]
  Contested Findings: [count]

Decision: [ ] PASS  [ ] PASS WITH FINDINGS  [ ] FAIL

Decision Basis (reference to §10 rules applied):

Open Findings at Time of Decision (list Finding IDs):

Conditions on PASS WITH FINDINGS (if applicable):

Merge Authorisation:
  [ ] Merge permitted
  [ ] Merge blocked (state hard block condition):
  [ ] Merge blocked pending soft block waiver

Board Chair Signature:
Date:
```

### 17.6 Template: Machine-Readable Indicator (TPL-MRI)

```json
{
  "review_id": "",
  "artefact_sha": "",
  "methodology_version": "",
  "decision": "PASS | PASS_WITH_FINDINGS | FAIL",
  "merge_permitted": true,
  "decision_date": "",
  "board_chair": "",
  "open_sev1_count": 0,
  "open_sev2_count": 0,
  "open_sev2_remediation_plan_accepted": 0,
  "contested_findings": 0,
  "expires_at": ""
}
```

The `expires_at` field is set to 72 hours after `decision_date` for artefacts under active development. If the artefact SHA changes, the indicator is void regardless of expiry.

---

## 18. Milestone-Completion Criteria

### 18.1 Definition

A milestone is complete when and only when:

1. All deliverables defined in the milestone specification have been produced.
2. A Board review has been completed for the artefact representing the milestone output.
3. The Board decision is PASS or PASS WITH FINDINGS.
4. The Business and Commercial Auditor has confirmed that commercial acceptance criteria are met.
5. All Open SEV-1 findings are Closed.
6. A Remediation Plan with accepted timeline is in place for any Open SEV-2 findings.
7. The Board Decision Record has been signed by the Board Chair.

### 18.2 Commercial Invoicing Gate

Where milestone completion is linked to a commercial invoice, the invoice must not be raised until:

- Condition 1–7 above are satisfied.
- The Business and Commercial Auditor has explicitly confirmed in writing that the milestone output meets the commercial acceptance criteria as defined in the relevant agreement.

The Business and Commercial Auditor's confirmation is a separate document from the Board Decision Record and must reference the specific contractual milestone and the Board Review ID.

### 18.3 Partial Milestone Completion

A milestone is binary: complete or not complete. There is no partial completion for commercial invoicing purposes. Where a milestone contains multiple components and one component fails review, the entire milestone is incomplete until all components have received a PASS or PASS WITH FINDINGS decision.

---

## 19. Reviewer Specification Index

The following specifications define the scope, inputs, evidence requirements, checklists, and output templates for each Board reviewer role. Each specification is a standalone document that must be read alongside this governing methodology.

| Spec ID | Title | File |
|---------|-------|------|
| RBS-001 | Methodology Audit | `specs/RBS-001-METHODOLOGY-AUDIT.md` |
| RBS-002 | Software Architecture Audit | `specs/RBS-002-SOFTWARE-ARCHITECTURE-AUDIT.md` |
| RBS-003 | Business and Commercial Audit | `specs/RBS-003-BUSINESS-COMMERCIAL-AUDIT.md` |
| RBS-004 | Data and Evidence Audit | `specs/RBS-004-DATA-EVIDENCE-AUDIT.md` |
| RBS-005 | QA and Reliability Audit | `specs/RBS-005-QA-RELIABILITY-AUDIT.md` |
| RBS-006 | Security and Privacy Audit | `specs/RBS-006-SECURITY-PRIVACY-AUDIT.md` |
| RBS-007 | Performance and Operations Audit | `specs/RBS-007-PERFORMANCE-OPERATIONS-AUDIT.md` |
| RBS-008 | Sceptical Review | `specs/RBS-008-SCEPTICAL-REVIEW.md` |

---

## 20. Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-07-18 | Provena Foundry Governance | Initial release |

---

*End of Governing Methodology — RBM-001 v1.0.0*
