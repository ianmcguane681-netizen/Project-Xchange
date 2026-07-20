# GS-P001 Advisory Review Execution — Implementation Plan

## Status

- Execution mode: `ADVISORY_DRY_RUN`
- Authority status: non-binding
- Methodology profile: RBM-001 `RELEASE_CANDIDATE`
- Runtime baseline: RBE runtime v0.1 merged by PR #6
- Tracking issue: #7

## Objective

Execute GS-P001 through the merged RBE runtime end to end without fabricating evidence, reviewer records, signatures, conflicts, or outcomes.

## Guardrails

1. All outputs must state `ADVISORY_DRY_RUN`.
2. `merge_permitted` must remain `false`.
3. Only verified GS-P001 evidence may enter the evidence register.
4. AI and automation may assist preparation and validation but may not occupy human review seats, sign records, ratify outcomes, or publish authoritative decisions.
5. RBE-001 v1.1.0 and RBM-001 v2.0.0 controlled packages must not be modified.
6. No UI, production deployment, network API, or external-service dependency is in scope.

## Planned work packages

### WP-1 — Input inventory

- Identify all existing GS-P001 evidence sources.
- Classify each source as verified, pending verification, excluded, or unavailable.
- Record provenance, retrieval date, source owner, jurisdiction, independence, and integrity metadata.
- Reject demo, synthetic, unattributed, or unverifiable evidence.

### WP-2 — Review package contract

- Define the GS-P001 case metadata accepted by `rbe_runtime`.
- Map the research question and decision scope to the active advisory profile.
- Define required evidence categories, minimum provenance fields, and validation failures.
- Preserve raw authority records while storing any runtime normalization separately.

### WP-3 — Operator runbook

- Document authority validation.
- Document database initialization and case creation.
- Document evidence registration and integrity verification.
- Document reviewer assignment, independence checks, conflict declaration, quorum, report submission, deterministic decision calculation, human ratification separation, publication separation, export, and bundle verification.

### WP-4 — Runtime integration

- Add the smallest GS-P001-specific adapter or fixture necessary to create the advisory case.
- Reuse existing runtime services and storage contracts.
- Do not add GS-P001 decision logic to the methodology-neutral runtime core.

### WP-5 — Tests

Tests must cover:

- rejection of unverified or incomplete evidence;
- duplicate and provenance-integrity failures;
- reviewer independence and conflicts;
- quorum failure;
- deterministic outcome precedence;
- advisory/non-binding enforcement;
- ratification and publication separation;
- immutable export and checksum verification;
- prohibition on `merge_permitted=true`.

### WP-6 — Dry-run execution

- Execute only after a verified input inventory exists.
- Do not populate missing human reports with synthetic substitutes.
- A procedurally incomplete or insufficient-evidence result is acceptable and must not be overridden.
- Export the complete JSON and Markdown audit bundle.

### WP-7 — Principal Architect review

Provide:

- changed-file list;
- traceability matrix;
- test results;
- CI run;
- evidence inventory summary;
- exported bundle checksums;
- known limitations;
- explicit confirmation that no controlled authority package changed.

## Acceptance criteria

- Repository CI passes.
- Controlled authority validation passes.
- The execution remains headless and backend-neutral.
- No fabricated evidence or human action appears in the review record.
- Every admitted evidence item has traceable provenance.
- The generated bundle verifies successfully.
- The output is visibly non-binding and advisory.
- Principal Architect review is completed before any completion or release claim.

## Out of scope

- Activating RBM-001
- Authorizing software construction or investment
- Building a maintenance-communication component
- Provena Foundry dashboards or UI
- Production deployment
- External reviewer impersonation
