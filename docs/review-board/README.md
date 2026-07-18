# Provena Foundry Review Board — Methodology Package

**Package Version:** 1.1.0  
**Status:** RELEASE-CANDIDATE — Pending Principal Architect approval  
**Applicability:** Provena Foundry only. Not applicable to GS-P001.  
**Last Updated:** 2026-07-18  

> **Note:** This package is a release candidate. The governing methodology (RBM-001 v1.1.0) must not be used for binding Board decisions until the Principal Architect formally approves it and the status is updated to ACTIVE.

---

## Overview

This directory contains the complete governing methodology and all individual reviewer specifications for the Provena Foundry Review Board. The package is designed to:

1. **Be committed to GitHub** as the authoritative source of truth for review governance.
2. **Be converted into individual reviewer prompts** — each specification includes a `Reviewer Prompt Conversion Notes` section with the identity, constraints, inputs, and output format required to instantiate that reviewer as an AI-assisted or human-guided review agent.
3. **Be compiled into an orchestration build specification** — the sequencing rules, input/output dependencies, tier routing, and schema references provide the contract for an orchestration layer that manages review workflow.

---

## Document Map

### Governing Methodology

| File | ID | Version | Description |
|------|----|---------|-------------|
| [`REVIEW-BOARD-METHODOLOGY.md`](REVIEW-BOARD-METHODOLOGY.md) | RBM-001 | 1.1.0 | Master governing document. All reviewer specifications are subordinate to this document. |

### Reviewer Specifications

| File | ID | Version | Role | Abbrev |
|------|----|---------|------|--------|
| [`specs/RBS-001-METHODOLOGY-AUDIT.md`](specs/RBS-001-METHODOLOGY-AUDIT.md) | RBS-001 | 1.1.0 | Methodology Auditor | MA |
| [`specs/RBS-002-SOFTWARE-ARCHITECTURE-AUDIT.md`](specs/RBS-002-SOFTWARE-ARCHITECTURE-AUDIT.md) | RBS-002 | 1.1.0 | Software Architecture Auditor | SAA |
| [`specs/RBS-003-BUSINESS-COMMERCIAL-AUDIT.md`](specs/RBS-003-BUSINESS-COMMERCIAL-AUDIT.md) | RBS-003 | 1.1.0 | Business and Commercial Auditor | BCA |
| [`specs/RBS-004-DATA-EVIDENCE-AUDIT.md`](specs/RBS-004-DATA-EVIDENCE-AUDIT.md) | RBS-004 | 1.1.0 | Data and Evidence Auditor | DEA |
| [`specs/RBS-005-QA-RELIABILITY-AUDIT.md`](specs/RBS-005-QA-RELIABILITY-AUDIT.md) | RBS-005 | 1.1.0 | QA and Reliability Auditor | QRA |
| [`specs/RBS-006-SECURITY-PRIVACY-AUDIT.md`](specs/RBS-006-SECURITY-PRIVACY-AUDIT.md) | RBS-006 | 1.1.0 | Security and Privacy Auditor | SPA |
| [`specs/RBS-007-PERFORMANCE-OPERATIONS-AUDIT.md`](specs/RBS-007-PERFORMANCE-OPERATIONS-AUDIT.md) | RBS-007 | 1.1.0 | Performance and Operations Auditor | POA |
| [`specs/RBS-008-SCEPTICAL-REVIEW.md`](specs/RBS-008-SCEPTICAL-REVIEW.md) | RBS-008 | 1.1.0 | Sceptical Reviewer | SR |

---

## Review Execution Sequence

The execution sequence depends on the assigned review risk tier (§6A of RBM-001). Steps within the same phase may execute in parallel. Steps in a later phase must not begin until all prior-phase steps are complete.

### Tier 1 — Lightweight

```
PHASE 0 — Pre-Review
  Board Chair:    Issue Review Initiation Record (TPL-RIR) with Tier 1 classification
  MA:             Validate Input Package (TPL-IPV)
  Reviewers:      Submit Independence Declarations (TPL-IND)
  [GATE: MA issues COMPLETE or DEFERRAL]

PHASE 1 — Specialist Reviews (parallel)
  Two of {SAA, QRA, POA} — selected by Board Chair for the specific change scope
  [SEV-1 findings escalated immediately regardless of tier]

PHASE 2 — Cross-Cutting Review
  MA:  Process Integrity Audit
  SR:  Sceptical Review + SR Challenge Questions

PHASE 3 — Decision
  Board Chair:  Applies §10.1 decision rules deterministically
  Board Chair:  Issues TPL-BDR + TPL-MRI
```

### Tier 2 — Standard

```
PHASE 0 — Pre-Review
  Board Chair:    Issue TPL-RIR with Tier 2 classification
  MA:             Validate Input Package (TPL-IPV)
  All reviewers:  Submit Independence Declarations (TPL-IND)
  [GATE: MA issues COMPLETE or DEFERRAL before Phase 1 begins]

PHASE 1 — Specialist Reviews (parallel)
  SAA:  Software Architecture Audit
  BCA:  Business and Commercial Audit
  DEA:  Data and Evidence Audit
  QRA:  QA and Reliability Audit
  SPA:  Security and Privacy Audit   [SEV-1 findings escalated immediately]
  POA:  Performance and Operations Audit
  [Minimum four of six; all six preferred]

PHASE 2 — Cross-Cutting Review
  MA:  Process Integrity Audit (reviews Phase 1 reports)
  SR:  Sceptical Review (reviews Phase 1 reports)
  SR:  Issues SR Challenge Questions before Phase 3

PHASE 3 — Decision
  Board Chair:  Resolves SR Challenge Questions
  Board Chair:  Applies §10.1 decision rules deterministically
  Board Chair:  Issues TPL-BDR + TPL-MRI
  BCA:          Issues Milestone-Completion Confirmation (if applicable)
```

### Tier 3 — Full Board

```
Same sequence as Tier 2, with:
  — All nine roles mandatory; no omissions permitted
  — SR report must include explicit Tier 3 Risk Characterisation section
  — BCA must confirm commercial invoicing gate scope limitation (§18.2)
  — Soft block waivers not available
```

---

## Review Risk Tiers — Quick Reference

Full definitions in RBM-001 §6A. Tier is proposed by authoring team, validated by MA, confirmed by Board Chair.

| Tier | Label | Typical Changes | Required Reviewers |
|------|-------|-----------------|-------------------|
| 1 | Lightweight | Doc corrections, test-only, patch upgrades, safe config | MA + 2 of {SAA, QRA, POA} + SR |
| 2 | Standard | Code changes, API changes, data model, major/minor upgrades | BC + MA + ≥4 specialists + SR |
| 3 | Full Board | Security, data contracts, milestones, methodology changes, post-incident | All 9 roles, no omissions |

Any trigger condition in RBM-001 §6 mandating Tier 3 overrides a lower tier proposal. Tiers can be escalated, never de-escalated.

---

## Key Decision Rules (Summary)

Full rules in RBM-001 §10. Evaluate in order — check FAIL first, then PASS WITH FINDINGS, then PASS. The three outcomes are mutually exclusive.

| Check | Outcome |
|-------|---------|
| Any SEV-1 Open or Contested → FAIL | FAIL (no exception) |
| Two or more SEV-2 Open → FAIL | FAIL |
| Process violation (MA SEV-1 finding) → FAIL | FAIL |
| Exactly one SEV-2 Open with accepted remediation plan | PASS WITH FINDINGS |
| Zero SEV-1 Open, zero SEV-2 Open, quorum met, inputs complete | PASS |

Decisions are produced by applying these rules to the finding set. The Board Chair confirms and records the result. There is no vote.

---

## Human Sign-off Boundaries

AI agents may assist in locating evidence, formatting reports, and running automated tools. The following acts require a named human reviewer's explicit signature before the record is accepted into the audit trail:

| Act | Required Signatory |
|----|-------------------|
| Independence Declaration | The named reviewer |
| Finding raised at SEV-1 or SEV-2 | The named specialist reviewer |
| Finding closure (SEV-1/SEV-2) | Closure reviewer (different person from finder) |
| Board Decision Record | Board Chair |
| Milestone-Completion Confirmation | Business and Commercial Auditor |
| MA Report (process integrity phase) | Methodology Auditor |
| Correction Record | Panel Chair |

---

## Evidence Tier Quick Reference

| Tier | Name | Admissible for SEV-1? | Admissible for SEV-2? |
|------|----|----------------------|----------------------|
| T1 | Direct Instrument (automated tool output) | Yes | Yes |
| T2 | Direct Observation (reviewer procedure) | Yes | Yes |
| T3 | Documentary Reference (spec/contract/regulation) | With T3-AUTHORITATIVE-EXTERNAL conditions (see §8.2) | Yes |
| T4 | Reasoned Inference | No | No |
| T5 | Assertion | No — never admissible | No — never admissible |

**T3-AUTHORITATIVE-EXTERNAL exception:** T3 is admissible for SEV-1 when: (1) the reference is an authoritative legal/regulatory/contractual/technical standard; (2) the specific clause is named; (3) direct applicability is shown in one logical step; (4) the document is confirmed currently in force. All four conditions required.

---

## Severity Reference

| Severity | Merge Impact | Example |
|----------|-------------|---------|
| SEV-1 — Critical | Hard block, no waiver | Authentication bypass; data corruption; hardcoded secret; confirmed regulatory violation |
| SEV-2 — Major | Block unless single finding with accepted remediation plan | Missing test coverage on critical path; SLA breach; unlicensed dependency |
| SEV-3 — Minor | No block; tracked in register | Naming convention violation; missing index; incomplete documentation |
| SEV-4 — Observation | No impact; recorded for reference | Style suggestions; minor improvements |

---

## Template and Schema Reference

All templates are defined in RBM-001 §17. Machine-readable JSON schemas are in RBM-001 §17.9.

| Template ID | Name | Owner | Schema |
|-------------|------|-------|--------|
| TPL-RIR | Review Initiation Record | Board Chair | §17.9.1 |
| TPL-IND | Independence Declaration | Each reviewer | — |
| TPL-IPV | Input Package Validation | MA | — |
| TPL-FND | Finding Record | Each reviewer | §17.9.2 |
| TPL-RRR | Reviewer Report | Each reviewer | — |
| TPL-BDR | Board Decision Record | Board Chair | §17.9.3 |
| TPL-RMP | Remediation Plan | Authoring team | — |
| TPL-RVR | Re-Review Record | Board Chair | — |
| TPL-MRI | Machine-Readable Indicator | Board Chair | §17.9.4 |
| TPL-COR | Correction Record | Panel Chair | §17.9.5 |

Reviewer-specific report templates: TPL-MAR (MA), TPL-SAAR (SAA), TPL-BCAR (BCA), TPL-DEAR (DEA), TPL-QRAR (QRA), TPL-SPAR (SPA), TPL-POAR (POA), TPL-SRR (SR).

---

## Orchestration Build Specification — Contracts

Input/output contract for each reviewer role, for use by an orchestration build specification. Tier column shows the minimum tier at which the role is engaged.

| Role | Min Tier | Phase | Inputs Required | Primary Output | Secondary Outputs |
|------|---------|-------|----------------|----------------|-------------------|
| MA (gate) | 1 | 0 | Input Package, TPL-RIR | TPL-IPV (COMPLETE or DEFERRAL) | Tier validation |
| SAA | 1* | 1 | Diff, dependency manifest, API spec, schema, ADR | TPL-SAAR + TPL-FND[] | — |
| BCA | 2 | 1 | Requirements, acceptance criteria, contracts, Known Issues | TPL-BCAR + TPL-FND[] | Milestone-Completion Confirmation (conditional) |
| DEA | 2 | 1 | Test results, Known Issues, data model, CI config | TPL-DEAR + TPL-FND[] | Evidence fabrication flag |
| QRA | 1* | 1 | Test results, test source, Known Issues, CI config | TPL-QRAR + TPL-FND[] | Trust assessment |
| SPA | 3** | 1 | SAST, dep scan, DAST, privacy assessment, diff | TPL-SPAR + TPL-FND[] | Immediate SEV-1 escalation |
| POA | 1* | 1 | Benchmarks, baseline, SLA, exec plans, monitoring config | TPL-POAR + TPL-FND[] | Operational readiness opinion |
| MA (process) | 1 | 2 | All Phase-1 reports, all TPL-FND, draft TPL-BDR | TPL-MAR + process TPL-FND[] | Process CLEAR/DEFICIENT/COMPROMISED opinion |
| SR | 1 | 2 | All Phase-1 reports, all TPL-FND, Input Package | TPL-SRCQ + TPL-SRR + TPL-FND[] | Re-open recommendation |
| Board Chair | 1 | 3 | All reports, all TPL-FND, SR challenge answers | TPL-BDR + TPL-MRI | TPL-COR (if correction) |

\* Tier 1 engages two of {SAA, QRA, POA} — Board Chair selects the most relevant for the change.  
\*\* SPA is required at Tier 3 and whenever any security trigger condition in §6 applies.

---

## Appeal and Correction — Summary

Full process in RBM-001 §18A.

- **Window:** 5 business days from Board Decision.
- **Valid grounds:** Procedural error, new material evidence, decision rule misapplication.
- **Invalid grounds:** Schedule pressure, commercial urgency, disagreement with technical merit without new evidence.
- **Outcome:** Correction Record (TPL-COR) appended — original records preserved unchanged. Revised TPL-MRI issued if decision is corrected.
- **Lineage:** `correction_ref` in TPL-MRI chains to TPL-COR; most recent operative record governs.

---

## GS-P001 Boundary

This entire package is scoped to Provena Foundry. GS-P001 is governed by a separate methodology. Where Provena Foundry shares infrastructure or libraries with GS-P001, findings must be scoped to the Provena Foundry usage of that component. Findings must not be raised against GS-P001–governed assets under this methodology.

---

## Versioning

This package follows semantic versioning per RBM-001 §16.1. Changes require updating:

1. The document version and status.
2. The `Document History` table in the changed document.
3. The `Reviewer Specification Index` in RBM-001 if a spec version changes.
4. This README's package version.

---

*End of README — Provena Foundry Review Board Methodology Package v1.1.0*
