# GS-P001 Advisory Execution Package — Phase B Contract

## Status

- Phase: `B — Evidence and Traceability Framework`
- Execution mode: `ADVISORY_DRY_RUN`
- Authority status: non-binding
- Evidence status: framework only; no evidence is admitted by this document

## Purpose

Phase B defines the machine-readable registers, identifiers, relationships, integrity requirements, and admission rules required to prepare verified GS-P001 evidence for the Review Board Engine.

Phase B does not assert that sufficient evidence exists. It provides the controlled structure in which evidence may be recorded and tested.

## Controlled documents

| Document ID | Purpose |
|---|---|
| `GS-P001-DOC-009` | Evidence Register schema |
| `GS-P001-DOC-010` | Source Register schema |
| `GS-P001-DOC-011` | Complaint Register schema |
| `GS-P001-DOC-012` | Government Source Register schema |
| `GS-P001-DOC-013` | Software Source Register schema |
| `GS-P001-DOC-014` | Claim-to-Evidence Mapping schema |
| `GS-P001-DOC-015` | Evidence Map schema |
| `GS-P001-DOC-016` | Provenance Chain schema |

## Identifier policy

Identifiers are stable, unique within GS-P001, never reused, and never renumbered after publication.

- Evidence: `GS-P001-EV-0001`
- Source: `GS-P001-SRC-0001`
- Complaint: `GS-P001-CMP-0001`
- Government record: `GS-P001-GOV-0001`
- Software record: `GS-P001-SW-0001`
- Claim: `GS-P001-CLM-0001`
- Provenance record: `GS-P001-PROV-0001`

Deletion is prohibited after an identifier is issued. Incorrect or rejected records remain present with an appropriate status and reason.

## Admission rules

An evidence record may be marked `admitted` only when all of the following are true:

1. `verification_status` is `verified`.
2. The source exists in the Source Register.
3. The source is `independent` or `partially_independent`.
4. A canonical URL is recorded.
5. A raw archived copy exists.
6. A SHA-256 content hash exists and matches the archived copy.
7. The evidence falls within the Phase A scope.
8. The evidence is not a duplicate.
9. A provenance record exists.
10. No Phase A exclusion rule applies.

Failure of any admission rule results in `pending` or `excluded`; it must not be silently overridden.

## Referential integrity

- Every `evidence_id` references exactly one `source_id`.
- Every admitted complaint references one evidence record and one source record.
- Every claim references one or more evidence records.
- Every evidence record has exactly one provenance record.
- Government and software records may reference multiple evidence records but cannot replace the Evidence Register.
- Evidence Map nodes and edges are derived artifacts and may not introduce identifiers absent from the controlled registers.

## Duplicate handling

Potential duplicates are retained during investigation. Confirmed duplicates are marked `excluded`, identify `duplicate_of`, and are not counted toward frequency, corroboration, or source diversity.

## Independence handling

Vendor-controlled records may provide context but cannot independently establish operational pain. Claims relying exclusively on vendor-controlled or unknown-independence sources must be `unsupported` or `partially_supported`.

## Claim controls

Claims must be written narrowly enough to be tested against cited evidence. Every claim must record:

- claim type;
- supporting evidence identifiers;
- counterevidence identifiers where present;
- limitations;
- support status; and
- review status.

No claim may be inferred solely from the number of records without considering duplication, source concentration, geography, time period, and actor type.

## Provenance and integrity

Raw evidence is immutable after collection. Normalised summaries are stored separately and must not overwrite raw artifacts. Every custody event records an artifact path and SHA-256 checksum.

Automation may assist collection, hashing, deduplication, and validation. Automation may not fabricate evidence, invent human verification, sign review records, or convert an inconclusive verification into `verified`.

## Empty register policy

The Phase B data files are committed as empty controlled registers. Empty registers are valid preparation artifacts but are insufficient for review execution. The dry run must not begin until admitted evidence and complete provenance records exist.

## Phase B completion criteria

Phase B framework implementation is complete when:

- all eight schemas exist and parse as JSON;
- empty controlled data registers exist;
- identifiers and relationships are documented;
- admission and exclusion rules are explicit;
- raw and normalised evidence are separated;
- no fabricated evidence is present; and
- the branch remains non-binding with `merge_permitted=false`.
