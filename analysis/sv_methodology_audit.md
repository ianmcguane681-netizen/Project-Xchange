# SV Engine v1 Methodology Audit

**Role:** Methodology auditor (read-only review stance)  
**Contract reviewed:** `docs/sv_engine_methodology_specification.md` and `docs/sv_engine_build_prompt.md`  
**Implementation reviewed:** `sv_engine/` and `tests/test_sv_engine.py`

## Conclusion

The implementation represents the methodology as deterministic rules and typed artifacts. It does not use AI scoring, does not couple verdicts to Streamlit, does not treat a verified problem as proof of a solution, and demonstrates genuine positive, unresolved, negative, and borderline paths with synthetic fixtures.

## Findings and Resolutions

### M-01 Approved evidence initially lacked reviewer identity

Risk: an `APPROVED` state without a reviewer and time would weaken authenticity lineage.

Resolution: approved evidence now requires `reviewed_by` and `reviewed_at`. Automated coverage rejects incomplete approval records.

Status: Resolved.

### M-02 Unsupported negative claims could initially fail a gate

Risk: the engine must not accept unsupported optimism or unsupported rejection.

Resolution: negative and contradictory claims now require approved linked evidence. Unsupported negative claims remain unresolved.

Status: Resolved.

### M-03 Gate claims needed domain cross-checks

Risk: a supported Boolean claim could conflict with an empty buyer map, weak Golden Study handoff, missing economics, absent competitor register, or missing authoritative legal evidence.

Resolution: G1, G4, G5, G6, G7, and G8 now cross-check the relevant typed records. Mandatory failures remain immune to aggregate score.

Status: Resolved.

### M-04 Required output registers were present only inside the aggregate result

Risk: reviewers need independently inspectable buyer, competition, technical, and verdict artifacts.

Resolution: separate JSON files are generated for each material register while retaining the complete aggregate result.

Status: Resolved.

### M-05 Metadata-only changes altered the first output hash implementation

Risk: retrieval metadata could make a stable business decision appear materially different.

Resolution: metadata exclusions now always include the engine defaults as well as rule-configured fields. A regression test proves input hashes change while stable business and output hashes do not.

Status: Resolved.

## Contract Coverage

- 12 validation categories: implemented and versioned.
- Eight mandatory gates: implemented as first-class records.
- Evidence classes E1-E7: implemented.
- Internal operational complexity: separate typed assessment and blocking gate logic.
- Three verdicts: demonstrated by materially different fixtures.
- Scenario and sensitivity analysis: implemented with conservative borderline downgrade.
- Missing evidence and ranked actions: generated deterministically.
- Contradictions: preserved as evidence and explicit records.
- File reports and SQLite lineage: implemented.
- Stable input, rule, output, and artifact hashes: implemented.
- No UI, Lovable, external AI, or fake production evidence: confirmed.

## Explicit Deferrals

1. A real Golden Study handoff has not yet been validated. Synthetic fixtures prove rules, not commercial truth.
2. A governed human challenge/override register is deferred. The deterministic verdict cannot currently be overwritten, which is the safer v1 behavior.
3. Reviewer identity is recorded but not authenticated by this local engine.

These deferrals do not weaken the deterministic prototype-investment verdict. They constrain where the engine may be used and are disclosed in every implementation guide.

