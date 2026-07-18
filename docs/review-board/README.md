# Provena Foundry Review Board — Methodology Package

**Package Version:** 1.0.0  
**Applicability:** Provena Foundry only. Not applicable to GS-P001.  
**Last Updated:** 2026-07-18  

---

## Overview

This directory contains the complete governing methodology and all individual reviewer specifications for the Provena Foundry Review Board. The package is designed to:

1. **Be committed to GitHub** as the authoritative source of truth for review governance.
2. **Be converted into individual reviewer prompts** — each specification includes a `Reviewer Prompt Conversion Notes` section with the identity, constraints, inputs, and output format required to instantiate that reviewer as an AI-assisted or human-guided review agent.
3. **Be compiled into an orchestration build specification** — the sequencing rules, input/output dependencies, and template references provide the contract for an orchestration layer that manages review workflow.

---

## Document Map

### Governing Methodology

| File | ID | Description |
|------|----|-------------|
| [`REVIEW-BOARD-METHODOLOGY.md`](REVIEW-BOARD-METHODOLOGY.md) | RBM-001 | Master governing document. Defines all principles, decision rules, templates, and process. All reviewer specifications are subordinate to this document. |

### Reviewer Specifications

| File | ID | Role | Abbrev |
|------|----|------|--------|
| [`specs/RBS-001-METHODOLOGY-AUDIT.md`](specs/RBS-001-METHODOLOGY-AUDIT.md) | RBS-001 | Methodology Auditor | MA |
| [`specs/RBS-002-SOFTWARE-ARCHITECTURE-AUDIT.md`](specs/RBS-002-SOFTWARE-ARCHITECTURE-AUDIT.md) | RBS-002 | Software Architecture Auditor | SAA |
| [`specs/RBS-003-BUSINESS-COMMERCIAL-AUDIT.md`](specs/RBS-003-BUSINESS-COMMERCIAL-AUDIT.md) | RBS-003 | Business and Commercial Auditor | BCA |
| [`specs/RBS-004-DATA-EVIDENCE-AUDIT.md`](specs/RBS-004-DATA-EVIDENCE-AUDIT.md) | RBS-004 | Data and Evidence Auditor | DEA |
| [`specs/RBS-005-QA-RELIABILITY-AUDIT.md`](specs/RBS-005-QA-RELIABILITY-AUDIT.md) | RBS-005 | QA and Reliability Auditor | QRA |
| [`specs/RBS-006-SECURITY-PRIVACY-AUDIT.md`](specs/RBS-006-SECURITY-PRIVACY-AUDIT.md) | RBS-006 | Security and Privacy Auditor | SPA |
| [`specs/RBS-007-PERFORMANCE-OPERATIONS-AUDIT.md`](specs/RBS-007-PERFORMANCE-OPERATIONS-AUDIT.md) | RBS-007 | Performance and Operations Auditor | POA |
| [`specs/RBS-008-SCEPTICAL-REVIEW.md`](specs/RBS-008-SCEPTICAL-REVIEW.md) | RBS-008 | Sceptical Reviewer | SR |

---

## Review Execution Sequence

The following sequence must be respected by any orchestration layer. Steps within the same phase may execute in parallel. Steps in a later phase must not begin until all prior-phase steps are complete.

```
PHASE 0 — Pre-Review
  Board Chair:    Issue Review Initiation Record (TPL-RIR)
  MA:             Validate Input Package (TPL-IPV)
  All reviewers:  Submit Independence Declarations (TPL-IND)
  [GATE: MA issues COMPLETE or DEFERRAL before Phase 1 begins]

PHASE 1 — Specialist Reviews (parallel)
  SAA:  Software Architecture Audit
  BCA:  Business and Commercial Audit
  DEA:  Data and Evidence Audit
  QRA:  QA and Reliability Audit
  SPA:  Security and Privacy Audit   [SEV-1 findings escalated immediately to Board Chair]
  POA:  Performance and Operations Audit
  [All six may run concurrently]

PHASE 2 — Cross-Cutting Review
  MA:  Process Integrity Audit (reviews Phase 1 specialist reports)
  SR:  Sceptical Review (reviews Phase 1 specialist reports)
  [MA and SR may run concurrently in Phase 2]
  SR:  Issues SR Challenge Questions to Board before Phase 3

PHASE 3 — Decision
  Board Chair:  Resolves SR Challenge Questions
  Board Chair:  Compiles finding set
  Board Chair:  Issues Board Decision Record (TPL-BDR)
  MA:           Confirms decision validity
  BCA:          Issues Milestone-Completion Confirmation (if applicable)
  Board Chair:  Issues Machine-Readable Indicator (TPL-MRI)
```

---

## Key Decision Rules (Summary)

Full rules are in RBM-001 §10. This summary is for orientation only — the full rules govern.

| Condition | Decision |
|-----------|----------|
| Zero SEV-1 Open; zero or one SEV-2 Open with remediation plan | PASS or PASS WITH FINDINGS |
| One or more SEV-1 Open or Contested | FAIL (no exception) |
| Two or more SEV-2 Open | FAIL |
| Input Package fraudulently represented | FAIL |
| Reviewer independence violation discovered | FAIL |

---

## Severity Reference (Summary)

| Severity | Merge Impact | Example |
|----------|-------------|---------|
| SEV-1 — Critical | Hard block, no waiver | Authentication bypass; data corruption; hardcoded secret |
| SEV-2 — Major | Block unless remediation plan accepted | Missing test coverage on critical path; SLA breach; unlicensed dependency |
| SEV-3 — Minor | No block; tracked in register | Naming convention violation; missing index; incomplete documentation |
| SEV-4 — Observation | No impact; recorded for reference | Style suggestions; minor improvements |

---

## Template Reference

All templates are defined in RBM-001 §17. Quick reference:

| Template ID | Name | Owner |
|-------------|------|-------|
| TPL-RIR | Review Initiation Record | Board Chair |
| TPL-IND | Independence Declaration | Each reviewer |
| TPL-IPV | Input Package Validation | MA |
| TPL-FND | Finding Record | Each reviewer |
| TPL-RRR | Reviewer Report | Each reviewer |
| TPL-BDR | Board Decision Record | Board Chair |
| TPL-RMP | Remediation Plan | Authoring team |
| TPL-RVR | Re-Review Record | Board Chair |
| TPL-MRI | Machine-Readable Indicator | Board Chair |

Each reviewer specification also defines its own report template (TPL-MAR, TPL-SAAR, TPL-BCAR, TPL-DEAR, TPL-QRAR, TPL-SPAR, TPL-POAR, TPL-SRR).

---

## Orchestration Build Specification — Contracts

The following table captures the input/output contract for each reviewer role, for use by an orchestration build specification.

| Role | Phase | Inputs Required | Primary Output | Secondary Outputs |
|------|-------|----------------|----------------|-------------------|
| MA (gate) | 0 | Input Package, TPL-RIR | TPL-IPV (COMPLETE or DEFERRAL) | — |
| SAA | 1 | Diff, dependency manifest, API spec, schema, ADR | TPL-SAAR + TPL-FND[] | — |
| BCA | 1 | Requirements, acceptance criteria, contracts, Known Issues | TPL-BCAR + TPL-FND[] | Milestone-Completion Confirmation |
| DEA | 1 | Test results, Known Issues, data model, CI config | TPL-DEAR + TPL-FND[] | Evidence fabrication flag |
| QRA | 1 | Test results, test source, Known Issues, CI config | TPL-QRAR + TPL-FND[] | Trust assessment |
| SPA | 1 | SAST, dep scan, DAST, privacy assessment, diff | TPL-SPAR + TPL-FND[] | Immediate SEV-1 escalation |
| POA | 1 | Benchmarks, baseline, SLA, exec plans, monitoring config | TPL-POAR + TPL-FND[] | Operational readiness opinion |
| MA (process) | 2 | All Phase-1 reports, all TPL-FND, draft TPL-BDR | TPL-MAR + process TPL-FND[] | Process opinion |
| SR | 2 | All Phase-1 reports, all TPL-FND, Input Package | TPL-SRCQ (challenge questions) + TPL-SRR + TPL-FND[] | Re-open recommendation |
| Board Chair | 3 | All reports, all TPL-FND, SR challenge answers | TPL-BDR | TPL-MRI |

---

## GS-P001 Boundary

This entire package is scoped to Provena Foundry. GS-P001 is governed by a separate methodology. Where Provena Foundry shares infrastructure or libraries with GS-P001, findings must be scoped to the Provena Foundry usage of that component. Findings must not be raised against GS-P001–governed assets under this methodology.

---

## Versioning

This package follows semantic versioning. The version in each document header is the version of that document. Changes require updating:

1. The document version.
2. The `Document History` table in the changed document.
3. The `Reviewer Specification Index` in RBM-001 if a spec version changes.
4. This README's package version if any document version changes.

Version bumps follow the rules in RBM-001 §16.1.

---

*End of README — Provena Foundry Review Board Methodology Package v1.0.0*
