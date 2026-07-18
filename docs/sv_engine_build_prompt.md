# Build Prompt — Provena Foundry Solution Validation Engine

Use the following prompt with the engineering agent responsible for implementing the SV Engine.

---

You are the Principal Architect and Principal Software Engineer for Provena Foundry.

Your task is to design and implement **SV Engine v1 — the Solution Validation Engine**.

Read and treat the following file as the governing methodology contract:

`docs/sv_engine_methodology_specification.md`

Do not weaken, reinterpret or bypass that specification for convenience.

## Product context

Provena Foundry follows this progression:

```text
Verified Problems
→ Verifiable Solutions
→ Marketable Products
```

The existing Golden Study methodology verifies whether a problem is sufficiently real, repeated, independently supported and commercially relevant.

The SV Engine begins after a verified problem exists.

Its job is to answer:

> Does the available evidence justify investing engineering resources in a bounded prototype of this proposed solution?

The SV Engine must return exactly one deterministic verdict:

- `BUILD PROTOTYPE`
- `VALIDATE FURTHER`
- `DO NOT BUILD`

`BUILD PROTOTYPE` does not mean build a production product. It means the evidence supports a bounded prototype or pilot intended to test the remaining material uncertainties.

## Architectural boundaries

Keep GS-P001 and Provena Foundry separate.

- GS-P001 remains a standalone proof system.
- The SV Engine belongs to Provena Foundry.
- Do not merge the GS-P001 application into this repository.
- Define a clean import contract through which a Golden Study can later provide a verified-problem package.
- Do not connect the SV Engine to Lovable in this milestone.
- Do not build a decorative dashboard.
- Do not fabricate activity, evidence, buyers, interviews, prices, competitors, workflow metrics or commercial results.
- Do not use opaque AI scoring.
- Do not let an LLM assign the final score or verdict.

The first implementation must be local, deterministic, auditable, test-first and usable without external AI services.

## Primary implementation objective

Build a repeatable engine that can:

1. ingest a structured verified-problem package;
2. register one or more proposed solution hypotheses;
3. register traceable evidence for each validation category;
4. represent the current workflow and proposed workflow;
5. calculate transparent category scores and confidence;
6. evaluate mandatory gates;
7. perform downside, base and upside scenario analysis;
8. detect borderline outcomes and material assumptions;
9. produce a deterministic verdict;
10. generate machine-readable and human-readable outputs;
11. preserve complete audit lineage;
12. reproduce the same output from identical stable inputs and rule versions.

## Required validation categories

Implement all categories defined in the methodology specification:

1. Problem inheritance
2. Current workflow baseline
3. Workflow improvement potential
4. Technical feasibility
5. Internal operational complexity
6. Buyer definition and ownership
7. Willingness to pay and customer economics
8. Market and competitive position
9. Provena unit economics
10. Adoption and implementation risk
11. Component reusability
12. Strategic fit

The category **Internal Operational Complexity** is mandatory and distinct from technical feasibility.

It must assess the ongoing difficulty and cost for Provena Foundry to:

- run the solution;
- maintain it;
- service customers;
- provide support;
- monitor failures;
- update rules, dependencies or models;
- patch security issues;
- manage infrastructure;
- onboard customers;
- document and train staff;
- perform releases and regression testing;
- manage customer-specific configuration;
- avoid technical debt and key-person dependency.

Its output must include:

- estimated monthly operating effort;
- estimated support effort per customer or deployment;
- expected update cadence;
- principal maintenance risks;
- principal service risks;
- operational complexity rating;
- confidence level.

A high-value customer solution must still be capable of receiving `DO NOT BUILD` where its internal operating burden is unacceptable.

## Required mandatory gates

Implement these gates exactly as first-class records:

- `G1_VERIFIED_PROBLEM_LINKAGE`
- `G2_BASELINE_SUFFICIENCY`
- `G3_TECHNICAL_PLAUSIBILITY`
- `G4_BUYER_CREDIBILITY`
- `G5_VALUE_PLAUSIBILITY`
- `G6_INTERNAL_OPERABILITY`
- `G7_COMPETITIVE_VIABILITY`
- `G8_ETHICAL_LEGAL_REGULATORY_ACCEPTABILITY`

Each gate must have:

- status;
- rule version;
- evidence references;
- explanation;
- unresolved questions;
- failure reason where applicable.

Use these statuses:

- `PASS`
- `UNRESOLVED`
- `FAIL`

A failed mandatory gate must never be overridden by an aggregate score.

## Evidence model

Implement the evidence classes from the methodology:

- `E1_DIRECT_OPERATIONAL`
- `E2_DIRECT_BUYER`
- `E3_DIRECT_USER`
- `E4_AUTHORITATIVE_EXTERNAL`
- `E5_COMPETITIVE_MARKET`
- `E6_INTERNAL_ESTIMATE`
- `E7_PROTOTYPE`

Every evidence record must include at minimum:

- stable evidence ID;
- evidence class;
- title;
- description;
- source type;
- source locator;
- source organisation;
- date observed or published;
- retrieval timestamp;
- content hash;
- relevant claim;
- linked categories;
- linked gates;
- authenticity or review state;
- limitations;
- contradiction flag;
- confidence contribution;
- provenance.

Internal estimates must always expose assumptions and must never be treated as equal to observed evidence.

## Core domain objects

Create explicit versioned models for at least:

- `VerifiedProblemPackage`
- `SolutionHypothesis`
- `SolutionValidationRecord`
- `EvidenceItem`
- `WorkflowModel`
- `WorkflowStep`
- `WorkflowMetric`
- `CategoryAssessment`
- `GateAssessment`
- `BuyerMap`
- `CompetitorRecord`
- `CustomerEconomicsModel`
- `ProvenaUnitEconomicsModel`
- `InternalOperationalComplexityAssessment`
- `Scenario`
- `SensitivityResult`
- `MissingEvidenceItem`
- `ContradictionRecord`
- `ValidationAction`
- `SVVerdict`
- `RunManifest`

Use stable identifiers and explicit schema versions.

Avoid unstructured dictionaries for material business entities where typed models are appropriate.

## Scoring and confidence

Use the raw category scale:

- `0` contradicted or clearly non-viable
- `1` very weak
- `2` weak or materially incomplete
- `3` plausible but not yet proven
- `4` strong evidence
- `5` compelling direct evidence

Use a confidence value from `0.00` to `1.00`.

Calculate:

```text
adjusted_score = raw_score × confidence
```

Do not hard-code a misleading universal weighted score without documenting and versioning the weights.

Create a versioned rule configuration file containing:

- category weights;
- minimum category requirements;
- gate rules;
- verdict thresholds;
- borderline tolerance;
- evidence sufficiency requirements.

The rule configuration must be loaded as data, hashed and recorded in every run manifest.

## Verdict logic

Implement deterministic verdict logic consistent with the methodology.

### BUILD PROTOTYPE

Allowed only when:

- every mandatory gate passes;
- no unresolved blocker exists;
- the workflow baseline is sufficient;
- improvement claims are measurable;
- buyer and value hypotheses are credible;
- internal operational complexity is acceptable;
- the configured confidence-adjusted threshold is met;
- prototype cost is proportionate to expected learning value.

### VALIDATE FURTHER

Use where:

- the solution remains plausible;
- one or more critical evidence gaps remain;
- one or more gates are unresolved rather than failed;
- the next evidence-gathering action is specific and proportionate.

This verdict must generate a ranked validation plan containing:

- missing evidence;
- recommended method;
- target source or participant;
- success threshold;
- estimated effort;
- decision unlocked.

### DO NOT BUILD

Use where:

- a mandatory gate fails;
- the solution does not address the verified mechanism;
- no credible buyer or budget path exists;
- economics are structurally weak;
- existing alternatives adequately solve the problem with no viable differentiation;
- technical, regulatory or operating barriers are disproportionate;
- internal operational complexity is unacceptable.

Rejection reasons must be stored as structured, reusable records.

## Workflow comparison

Represent both:

- current-state workflow;
- proposed-state workflow.

Support explicit comparison of:

- steps;
- actors;
- handoffs;
- systems;
- manual entries;
- duplicated work;
- waiting time;
- handling time;
- errors;
- rework;
- exceptions;
- compliance risk;
- customer impact.

Do not invent baseline numbers.

Where values are unknown, store them as unknown and create missing-evidence actions.

Support measured values, bounded estimates and assumptions as different data types.

## Scenario and sensitivity analysis

Implement:

- downside scenario;
- base scenario;
- upside scenario.

Identify assumptions that materially influence the verdict.

A BUILD PROTOTYPE verdict must not depend exclusively on the upside scenario.

Where a small change in an uncertain assumption changes the verdict, mark the SVR as `BORDERLINE` and generate a priority validation action for that assumption.

## Persistence

Use the repository's existing persistence conventions where appropriate, but do not couple methodology logic directly to the UI or database layer.

Recommended layers:

```text
sv_engine/domain/
sv_engine/rules/
sv_engine/services/
sv_engine/repositories/
sv_engine/reporting/
sv_engine/fixtures/
```

Persist at minimum:

- SV records;
- evidence;
- workflows;
- category assessments;
- gate assessments;
- scenarios;
- validation actions;
- verdicts;
- run manifests;
- hashes;
- version information.

All migrations must be safe for existing local data.

## Input and output contracts

Provide a documented JSON Schema or typed schema for the Golden Study handoff package.

The engine must generate:

1. machine-readable JSON result;
2. human-readable Markdown decision brief;
3. category scorecard;
4. gate register;
5. missing evidence register;
6. contradiction register;
7. current-versus-proposed workflow comparison;
8. internal operational complexity report;
9. customer economics report;
10. Provena unit economics report;
11. scenario and sensitivity report;
12. ranked validation plan;
13. run manifest with hashes and version data.

Reports must distinguish clearly among:

- observed facts;
- calculated outputs;
- estimates;
- assumptions;
- unknowns;
- contradictions.

## Determinism and hashing

Two runs with identical stable inputs and identical rule versions must produce identical business outputs.

Implement separate treatment for:

- stable business fields;
- classification inputs;
- metadata-only fields.

Retrieval timestamps and other metadata-only changes must not alter stable business hashes.

Material changes to evidence, assumptions, workflows, buyers, economics or solution scope must be detected and explained.

Record:

- input hash;
- stable business hash;
- rule-set hash;
- output hash;
- engine version;
- methodology version.

## Test requirements

Use a test-first approach.

Add automated tests covering at minimum:

1. identical inputs produce identical outputs;
2. metadata-only mutation does not change the business verdict;
3. material business mutation is detected;
4. removing evidence lowers confidence or changes sufficiency;
5. failed gates cannot be overridden by scores;
6. missing buyer evidence blocks BUILD PROTOTYPE;
7. missing baseline blocks BUILD PROTOTYPE;
8. unacceptable internal operational complexity blocks BUILD PROTOTYPE;
9. strong customer value does not conceal poor Provena economics;
10. strong problem evidence does not conceal weak solution linkage;
11. contradictory evidence is preserved;
12. a genuine BUILD PROTOTYPE fixture;
13. a genuine VALIDATE FURTHER fixture;
14. multiple genuine DO NOT BUILD fixtures;
15. a borderline sensitivity fixture;
16. historical run reproduction under its original rule version;
17. malformed or incomplete Golden Study handoff input;
18. unsupported positive claims do not receive positive evidence credit.

Do not satisfy the three verdict tests by changing expected outputs artificially. Fixtures must contain materially different evidence conditions.

## Seed implementation

Create controlled fixtures for one verified problem and at least three materially distinct proposed-solution cases:

### Case A — BUILD PROTOTYPE candidate

Use synthetic test fixtures clearly labelled as test fixtures, not real evidence.

It should pass all gates and contain sufficient direct evidence to exercise the positive path.

### Case B — VALIDATE FURTHER

It should have a plausible solution and verified problem linkage but unresolved buyer or workflow baseline evidence.

### Case C — DO NOT BUILD

It should fail at least one mandatory gate for a substantive reason, such as no credible buyer, unacceptable operating burden, no differentiation or failed solution linkage.

Also create a second DO NOT BUILD fixture caused specifically by excessive internal operational complexity despite strong customer value.

Do not present any synthetic fixture as a real Provena finding.

## Review structure

Use three coordinated engineering roles:

1. **Primary implementation agent**
   - writes the architecture and code;
   - owns integration and test completion.

2. **Methodology auditor**
   - read-only review;
   - checks the implementation against `docs/sv_engine_methodology_specification.md`;
   - identifies evidence inflation, missing gates, non-determinism and overclaiming.

3. **Commercial and operational reviewer**
   - read-only review;
   - checks buyer logic, willingness-to-pay logic, customer economics, Provena unit economics and internal operational complexity.

The two reviewers must produce written review artefacts before the milestone is considered complete.

Create:

- `analysis/sv_methodology_audit.md`
- `analysis/sv_commercial_operational_review.md`

The primary agent must resolve or explicitly defer every finding.

## Required documentation

Add or update:

- architecture overview;
- domain model documentation;
- rule configuration documentation;
- Golden Study handoff contract;
- CLI or execution guide;
- report examples;
- test strategy;
- limitations and excluded scope;
- migration notes.

Do not rewrite Provena Foundry as an AI company.

AI may later assist evidence extraction or research, but the product and decision methodology are not AI products and the final verdict must remain deterministic.

## Milestone completion criteria

Do not declare completion until all of the following are true:

- methodology contract is implemented without silent omissions;
- all 12 validation categories exist;
- all 8 gates exist;
- internal operational complexity is fully implemented;
- all three verdict classes are demonstrated through materially different fixtures;
- audit lineage and hashes are present;
- scenario and sensitivity analysis works;
- JSON and Markdown reports are generated;
- tests pass;
- methodology audit is complete;
- commercial and operational review is complete;
- no Lovable UI has been built;
- no fake production evidence has been introduced;
- README explains current capabilities honestly.

## Delivery format

At the end of the milestone, provide:

1. concise architecture summary;
2. file-by-file change summary;
3. database or migration summary;
4. test results with exact counts;
5. example outputs for all three verdicts;
6. methodology audit findings and resolutions;
7. commercial and operational review findings and resolutions;
8. known limitations;
9. exact commit SHA;
10. recommended next milestone.

Work in small, reviewable commits.

Prioritise evidence quality, traceability, repeatability, commercial relevance, internal operability and honest rejection over feature quantity or presentation.
