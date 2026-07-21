# GS-P001-DOC-007 — Exclusions Register

**Document version:** 1.0.0  
**Study:** GS-P001  
**Execution mode:** `ADVISORY_DRY_RUN`

The following evidence, actions and conclusions are excluded from admission or authority in GS-P001.

## Evidence exclusions

| ID | Exclusion | Reason | Handling rule |
|---|---|---|---|
| X-001 | AI-generated, synthetic or demo complaints | They are not independent evidence. | Reject and record the rejection reason. |
| X-002 | Duplicate copies, reposts or summaries of the same underlying incident | They can falsely inflate recurrence. | Link as duplicates and count the underlying incident once. |
| X-003 | Unverifiable screenshots or extracts without recoverable provenance | Authenticity and context cannot be established. | Reject unless provenance is later completed. |
| X-004 | Anonymous documents with no identifiable source, date or retrieval record | Traceability is inadequate. | Reject. |
| X-005 | Vendor marketing, sales brochures and unsupported feature claims | They are commercially interested and do not independently prove pain. | Context only; never use as core evidence. |
| X-006 | Unsupported opinion, speculation or general commentary | It does not demonstrate an operational event or measured condition. | Reject as evidence; contextual notes may be stored separately. |
| X-007 | Evidence outside the United States | It falls outside the geographic scope. | Reject from GS-P001; retain only in a separate out-of-scope log if useful. |
| X-008 | Commercial-only, industrial or unrelated facilities-management evidence | It falls outside the residential sector boundary. | Reject unless a distinct residential component is independently traceable. |
| X-009 | Maintenance-condition evidence with no communication or workflow dimension | GS-P001 concerns maintenance communication operations. | Reject unless the communication failure is explicit and traceable. |
| X-010 | Internal Project Exchange analysis presented as external evidence | Internal work is not independent market evidence. | Treat as analysis only and require external source support. |
| X-011 | Evidence obtained unlawfully or without required access authority | It creates legal, ethical and audit risk. | Reject and do not distribute. |
| X-012 | Records whose material content cannot be preserved or integrity-checked | Independent verification cannot be repeated. | Reject or classify as pending until preservation succeeds. |

## Governance exclusions

The advisory execution excludes:

- AI or automation occupying a human reviewer seat;
- fabricated reviewer identities, declarations, signatures or reports;
- simulated quorum;
- retrospective alteration of reviewer reports to produce a preferred outcome;
- treating advisory output as binding ratification;
- publication of an authoritative decision without the required human authority;
- setting `merge_permitted` to `true`;
- modification of controlled RBE-001 or RBM-001 authority packages as part of this execution.

## Decision exclusions

GS-P001 cannot decide:

- that software must be built;
- which software architecture or vendor should be used;
- how much should be invested;
- projected revenue, valuation or market share;
- production-readiness or security approval;
- that Provena Foundry should implement or display the study.

## Audit rule

Every rejected item must retain a rejection record containing its proposed evidence ID, source reference, exclusion ID, reviewer or validator, timestamp and reason. Rejected content must never silently disappear from the audit trail.
