# SV Engine v1 Implementation Guide

## Purpose and Boundary

SV Engine v1 answers one question: does traceable evidence justify investing in a bounded prototype of a proposed solution?

It begins only after a Golden Study supplies an eligible verified-problem package. It does not verify the original problem, approve a production product, prove demand, or replace human legal and commercial review. GS-P001 remains separate. No Lovable integration, dashboard, external AI service, or fabricated production evidence is part of this milestone.

## Architecture

```text
Golden Study handoff JSON
        |
        v
Typed domain validation
        |
        v
Evidence-linked category assessments (12)
        |
        v
Mandatory gate register (8)
        |
        v
Downside / base / upside sensitivity
        |
        v
Deterministic verdict
        |
        +--> JSON and Markdown artifacts
        +--> append-only SQLite audit run
```

The package is deliberately independent from the existing Streamlit application:

- `sv_engine/domain/`: typed, versioned business entities and controlled vocabulary.
- `sv_engine/rules/`: versioned rules loaded as data and recorded by hash.
- `sv_engine/services/`: hashing, evidence assessment, gates, scenarios, sensitivity, and verdict orchestration.
- `sv_engine/repositories/`: SQLite audit persistence with no UI dependency.
- `sv_engine/reporting/`: complete file-based decision artifacts.
- `sv_engine/fixtures/`: synthetic rule-test cases only.
- `sv_engine/schemas/`: the Golden Study verified-problem handoff contract.

## Domain Model

The implementation defines explicit models for:

- `VerifiedProblemPackage`
- `SolutionHypothesis`
- `SolutionValidationRecord`
- `EvidenceItem`
- `WorkflowModel`, `WorkflowStep`, and `WorkflowMetric`
- `CategoryAssessment` and `GateAssessment`
- `BuyerMap` and `CompetitorRecord`
- `CustomerEconomicsModel` and `ProvenaUnitEconomicsModel`
- `InternalOperationalComplexityAssessment`
- `Scenario` and `SensitivityResult`
- `MissingEvidenceItem` and `ContradictionRecord`
- `ValidationAction`, `SVVerdict`, and `RunManifest`

`ValidationClaim` is the explicit bridge between a material claim and its evidence. A positive or negative claim without approved linked evidence remains unresolved. It cannot receive positive score credit or fail a gate without traceable support.

Approved evidence records a reviewer and review timestamp. Internal estimates must expose assumptions and their confidence contribution is capped by the versioned rule set.

## Golden Study Handoff

The source-agnostic handoff schema is `sv_engine/schemas/golden_study_handoff.schema.json`.

Required fields include the verified problem ID, Golden Study ID and verdict, mechanism, affected workflow and organisation type, consequences, source references, evidence lineage, independent source-family count, confidence, and limitations.

Gate G1 also checks the handoff semantically. A rejected or insufficient Golden Study verdict fails. Fewer than two independent source families or low problem confidence leaves the gate unresolved. The SV Engine does not repair or inflate a weak Golden Study handoff.

## Rule Configuration

`sv_engine/rules/sv_rules_v1.json` is the decision contract for SV Engine v1. It contains:

- all 12 category IDs, weights, minimum build scores, and required claims;
- all eight mandatory gates and their required conditions;
- evidence review and confidence rules;
- build score and confidence thresholds;
- borderline sensitivity tolerance;
- internal operating effort, support, rating, and key-person limits;
- global prototype-cost proportionality requirements;
- fields excluded from stable business hashes.

The file is loaded, validated, canonically hashed, and recorded in each run manifest. Historical rules can be supplied through the CLI to reproduce an old run.

Scores use the methodology scale from zero to five. The engine awards score only when a category has both approved linked evidence and a supported structured claim. Confidence is derived from the linked evidence; the adjusted score is `raw_score * confidence`. Gates are evaluated before aggregate thresholds and cannot be overridden by a high score.

## Verdict Logic

`BUILD PROTOTYPE` requires every mandatory gate to pass, no unresolved global blocker, all minimum category scores, the configured confidence-adjusted threshold, sufficient overall confidence, a bounded prototype scope, measurable claims, and proportionate cost-to-learning evidence.

`VALIDATE FURTHER` is returned for unresolved but plausible conditions. It always includes specific missing evidence and a ranked validation plan.

`DO NOT BUILD` is returned for evidence-backed mandatory failures, non-positive customer or Provena economics, disproportionate prototype cost, or unacceptable internal operating burden. Scores cannot conceal those failures.

A material verdict change within the configured scenario tolerance marks the run `BORDERLINE`. A borderline positive case is conservatively downgraded to `VALIDATE FURTHER` with a priority action.

## Outputs

Each CLI run writes:

- `sv_result.json`
- `decision_brief.md`
- `evidence_register.json`
- `buyer_map.json`
- `willingness_to_pay_evidence.json`
- `competitive_alternatives.json`
- `technical_feasibility_assessment.json`
- `category_scorecard.json`
- `gate_register.json`
- `missing_evidence_register.json`
- `contradiction_register.json`
- `workflow_comparison.json`
- `internal_operational_complexity.json`
- `customer_economics.json`
- `provena_unit_economics.json`
- `scenario_sensitivity.json`
- `ranked_validation_plan.json`
- `deterministic_verdict.json`
- `run_manifest.json`

Reports distinguish source evidence, calculations, estimates, assumptions, unknowns, and contradictions. Unknown workflow values remain unknown.

## Determinism and Audit Lineage

The engine records the full input hash, stable business hash, rule-set hash, stable output hash, engine version, methodology version, scoring-rule version, evidence IDs, retrieval timestamps, transformations, artifact hashes, and execution metadata.

Metadata such as retrieval and execution timestamps does not change the stable business hash or business output hash. Material changes are detected and returned with changed field paths. A stable content-addressed run ID identifies equivalent business inputs; each execution also receives a unique execution ID so repeated runs remain append-only.

## Persistence and Migration

The default audit store is `data/sv_engine.db`. It is separate from `data/project_exchange.db` and does not alter existing PX-EOS tables.

Migration is additive and idempotent: the repository uses `CREATE TABLE IF NOT EXISTS` for SV runs, records, evidence, workflows, categories, gates, scenarios, validation actions, verdicts, and manifests. Existing local data is neither rewritten nor deleted.

## Execution

```powershell
python -m sv_engine.cli `
  --input examples\sv_engine\inputs\build_prototype.json `
  --output-dir data\sv_engine_output `
  --db data\sv_engine.db
```

Historical rules may be supplied with `--rules path\to\rules.json`.

The controlled examples in `examples/sv_engine/` demonstrate all three verdict classes. Every example is synthetic and must not be cited as a Provena finding, market fact, buyer interview, or commercial result.

## Test Strategy

The focused suite verifies deterministic output, metadata-only stability, material mutation detection, evidence removal, unsupported claims, gate precedence, buyer and baseline gaps, internal operability, customer versus Provena economics, weak solution linkage, contradiction retention, three genuine verdict paths, borderline sensitivity, historical rules, malformed input, review identity, reports, and append-only SQLite persistence.

Run:

```powershell
python -m pytest -q tests/test_sv_engine.py
```

The full repository remains covered by:

```powershell
python -m pytest -q
```

## Limitations and Excluded Scope

- No legitimate Golden Study handoff has yet been assessed by SV Engine v1. The included examples are synthetic.
- Evidence authenticity approval is recorded, but the engine cannot independently prove a reviewer's identity.
- Legal, privacy, security, buyer, and material financial conclusions still require accountable human review.
- Economics are bounded transparent models, not a forecasting or accounting system.
- Workflow values are accepted only as observed, calculated, bounded estimates, estimates, assumptions, unknowns, or contradictions; the engine does not collect them.
- Human challenges do not silently overwrite the deterministic verdict. A separate governed override workflow is intentionally deferred.
- No UI, external AI, autonomous research, customer deployment, or production investment approval is included.

## Next Eligible Milestone

Run SV Engine v1 with one legitimate Golden Study verified-problem package and one bounded solution hypothesis. Review every source, buyer, workflow, economics, legal, and operating artifact. Only after that run is reproducible should an optional governed human-challenge register or external consumer be considered.

