# Provena Foundry — Solution Validation Engine (SV Engine)

**Document status:** Draft v0.1  
**System:** Provena Foundry  
**Engine:** Solution Validation Engine (SV Engine)  
**Purpose:** Convert a verified problem into an evidence-backed decision on whether Provena Foundry should invest in prototyping and validating a proposed solution.

---

## 1. Position in the Provena pipeline

The SV Engine operates only after a Golden Study has produced a sufficiently supported problem record.

```text
Authentic Evidence
      ↓
Golden Study / Problem Verification
      ↓
Verified Problem
      ↓
Solution Validation Engine
      ↓
BUILD PROTOTYPE | VALIDATE FURTHER | DO NOT BUILD
      ↓
Prototype and Field Validation
      ↓
Marketable Product or Rejection
```

The Golden Study answers:

> Is the problem real, repeated, independently supported and commercially relevant?

The SV Engine answers:

> Does the available evidence justify investing engineering resources in this proposed solution?

The SV Engine does not prove that a finished product will succeed. It determines whether a solution hypothesis has earned the next level of investment.

---

## 2. Core principles

1. **Evidence before scoring.** No category may receive a positive score without traceable supporting evidence.
2. **No evidence inflation.** Complaint volume, market size estimates or internal enthusiasm cannot substitute for buyer, workflow or feasibility evidence.
3. **Deterministic decisions.** The same inputs and rules must produce the same output.
4. **Explicit unknowns.** Missing evidence must be recorded as missing, not estimated silently.
5. **Negative evidence matters.** Strong incumbent coverage, weak buyer urgency, excessive operating burden or poor economics can override attractive problem evidence.
6. **Separate problem truth from solution quality.** A verified problem does not imply that the proposed solution is good.
7. **Separate buildability from marketability.** A technically feasible solution may still be commercially weak.
8. **Separate customer value from Provena burden.** Customer benefit must be weighed against Provena's internal cost to build, run, maintain, service and update the solution.
9. **Traceability.** Every material conclusion must link back to source evidence, calculation or declared rule.
10. **Rejection is a valid outcome.** The system must be capable of producing genuine DO NOT BUILD verdicts.

---

## 3. Required inputs

An SV assessment must not begin until the following minimum inputs exist:

- `verified_problem_id`
- Golden Study verdict and evidence summary
- problem mechanism statement
- affected workflow
- affected organisation type
- known consequences of the failure
- proposed solution hypothesis
- intended user
- intended buyer hypothesis
- source references and evidence lineage

Optional inputs may include:

- current-state workflow map
- baseline time, cost, error or rework measurements
- buyer interviews
- operator interviews
- procurement evidence
- competitor research
- pricing evidence
- technical architecture notes
- integration documentation
- prototype or simulation results
- regulatory analysis

If the minimum inputs are incomplete, the SV Engine must return `VALIDATE FURTHER` with a missing-input register.

---

## 4. Unit of assessment

The unit of assessment is a **Solution Validation Record (SVR)**.

Each SVR represents one proposed solution to one verified problem mechanism.

A single verified problem may generate multiple SVRs where materially different solutions are possible. Solutions must not be combined merely to improve aggregate scoring.

Each SVR must contain:

- stable ID
- version
- linked Golden Study and verified problem
- solution hypothesis
- intended user
- intended buyer
- scope boundaries
- evidence register
- category assessments
- gate results
- calculated scores
- sensitivity analysis
- missing evidence
- contradictory evidence
- verdict
- verdict explanation
- created and updated timestamps
- input and output hashes

---

## 5. Evidence classes

Every evidence item must be classified.

### E1 — Direct operational evidence

Examples:

- observed workflow
- system logs
- case records
- measured handling time
- measured error rate
- support volume
- rework counts
- implementation records

### E2 — Direct buyer evidence

Examples:

- structured buyer interview
- signed pilot interest
- budget confirmation
- procurement record
- request for proposal
- paid proof of concept
- historical software purchase for the same problem

### E3 — Direct user evidence

Examples:

- structured operator interview
- usability test
- observed task completion
- workflow diary
- prototype test

### E4 — Authoritative external evidence

Examples:

- regulator publications
- official datasets
- legislation
- standards
- audited filings
- formal industry reports with disclosed methodology

### E5 — Competitive and market evidence

Examples:

- competitor documentation
- pricing pages
- product demos
- implementation guides
- customer case studies
- procurement databases
- credible market research

### E6 — Internal estimate

Examples:

- engineering estimate
- support estimate
- infrastructure estimate
- forecast adoption assumption

Internal estimates must be labelled as estimates, include assumptions and never be treated as equivalent to observed evidence.

### E7 — Prototype evidence

Examples:

- benchmark result
- simulated workflow
- controlled pilot
- technical spike
- integration test
- before-and-after task test

---

## 6. Validation categories

Each category receives:

- evidence sufficiency state
- score from 0 to 5
- confidence from 0 to 1
- evidence references
- contradictions
- unresolved questions
- category conclusion

A high raw score with low confidence must not be treated as strong evidence.

### 6.1 Problem inheritance

Purpose: Confirm that the proposed solution addresses the verified mechanism rather than a loosely related symptom.

Assess:

- strength of the Golden Study evidence
- independence of source families
- mechanism specificity
- frequency and severity
- commercial consequence
- stability across repeated runs
- whether the proposed solution maps directly to the mechanism

Failure condition:

- The solution does not clearly address the verified trigger → workflow → failure → consequence chain.

### 6.2 Current workflow baseline

Purpose: Establish the current state against which improvement can be measured.

Assess:

- actors
- steps
- handoffs
- systems used
- inputs and outputs
- decision points
- exceptions
- average and range of handling time
- error and rework points
- delays
- customer impact
- compliance or operational risk

A baseline cannot be replaced by a generic description of the industry.

### 6.3 Workflow improvement potential

Purpose: Estimate how materially the proposed solution could improve the current workflow.

Assess:

- steps removed
- handoffs removed
- manual entries removed
- duplicated work removed
- time saved
- waiting time reduced
- error reduction
- rework reduction
- exception handling improvement
- traceability improvement
- user experience improvement
- customer experience improvement

Preferred evidence:

- current-state versus proposed-state process map
- measured or simulated before-and-after results
- documented assumptions

### 6.4 Technical feasibility

Purpose: Determine whether the solution can realistically be built and integrated.

Assess:

- architecture complexity
- data availability and quality
- integration requirements
- API availability
- legacy system constraints
- security requirements
- privacy requirements
- regulatory constraints
- performance requirements
- reliability requirements
- scalability requirements
- technical dependencies
- vendor dependencies
- build estimate range

A technically possible solution may still score poorly where dependencies, uncertainty or integration risk are excessive.

### 6.5 Internal operational complexity

Purpose: Assess the ongoing difficulty for Provena Foundry to run, maintain, service, support and update the solution after initial development.

This is a distinct category and must not be collapsed into technical feasibility.

Assess:

- ongoing maintenance effort
- expected update frequency
- infrastructure administration
- monitoring and incident response
- customer support burden
- implementation and onboarding burden
- configuration requirements
- data quality operations
- model or rules maintenance
- regulatory update burden
- security patching burden
- dependency and vendor management
- documentation burden
- training burden
- release and regression testing burden
- customer-specific customisation risk
- technical debt risk
- key-person dependency
- ease of transferring ownership to new engineers
- service-level expectations
- cost to serve
- long-term sustainability

Required outputs:

- estimated monthly operating effort
- estimated support effort per customer or deployment
- expected update cadence
- principal maintenance risks
- principal service risks
- operational complexity rating
- confidence level

A solution with strong customer value may still fail if the internal operational burden destroys margin, reliability or scalability.

### 6.6 Buyer definition and ownership

Purpose: Determine whether a real organisational buyer can be identified.

Assess:

- economic buyer
- operational owner
- technical approver
- compliance approver
- end user
- budget source
- authority to purchase
- urgency
- internal incentives
- consequences of inaction
- procurement path

The category fails where the affected user is identifiable but no credible budget owner exists.

### 6.7 Willingness to pay and customer economics

Purpose: Determine whether the value created could support a purchase.

Assess:

- direct cost savings
- labour savings
- capacity released
- revenue protection
- loss avoidance
- compliance risk reduction
- customer retention impact
- service quality improvement
- existing spending on substitutes
- stated willingness to pay
- revealed willingness to pay
- pilot or procurement interest
- plausible pricing model
- customer payback period

Stated interest without budget, authority or behavioural evidence is weak evidence.

### 6.8 Market and competitive position

Purpose: Determine whether the solution has a defensible place in the market.

Assess:

- incumbent products
- internal alternatives
- manual alternatives
- build-versus-buy behaviour
- competitor strengths
- competitor weaknesses
- pricing
- switching costs
- implementation costs
- unmet gaps
- market concentration
- regulatory or contractual barriers
- distribution access
- differentiation

A large market does not compensate for a fully solved problem with no credible differentiation.

### 6.9 Provena unit economics

Purpose: Determine whether the opportunity could generate sustainable value for Provena Foundry.

Assess:

- expected development cost
- expected implementation cost
- ongoing cost to serve
- infrastructure cost
- support cost
- sales and procurement cost
- gross margin potential
- pricing range
- customer lifetime value assumptions
- customer acquisition difficulty
- break-even customer count
- cash-flow requirements
- downside case

All calculations must expose formulas and assumptions.

### 6.10 Adoption and implementation risk

Purpose: Assess whether customers can and will adopt the solution.

Assess:

- behavioural change required
- data migration
- system integration
- training
- workflow disruption
- implementation time
- executive sponsorship
- user resistance
- legal review
- security review
- procurement duration
- measurable time to value

### 6.11 Component reusability

Purpose: Determine whether the solution can become a reusable software component rather than a one-off custom build.

Assess:

- commonality of the mechanism across organisations
- configurable versus bespoke logic
- reusable data model
- reusable workflow primitives
- API potential
- portability across systems
- cross-industry applicability
- degree of customer-specific customisation
- integration abstraction potential

### 6.12 Strategic fit

Purpose: Determine whether the solution strengthens Provena Foundry's long-term component factory.

Assess:

- alignment with verified opportunity strategy
- relationship to existing or planned components
- future study leverage
- data asset creation
- repeatable distribution advantage
- operational capability reuse
- concentration risk
- distraction risk

Strategic fit must not override failed buyer, economic or feasibility gates.

---

## 7. Scoring model

Each category uses a 0–5 score:

- `0` — contradicted or clearly non-viable
- `1` — very weak
- `2` — weak or materially incomplete
- `3` — plausible but not yet proven
- `4` — strong evidence
- `5` — compelling direct evidence

Each category also receives a confidence value:

- `0.00–0.24` — speculative
- `0.25–0.49` — low
- `0.50–0.74` — moderate
- `0.75–0.89` — high
- `0.90–1.00` — very high

The confidence-adjusted category score is:

```text
adjusted_score = raw_score × confidence
```

Scores must be calculated from explicit rules and stored inputs. Language models may assist with extraction or summarisation only where their output is reviewed, versioned and converted into deterministic structured inputs. An LLM may not assign the final verdict.

---

## 8. Mandatory gates

The weighted score cannot override mandatory gates.

### Gate G1 — Verified problem linkage

Pass only if the solution directly addresses a verified mechanism.

### Gate G2 — Baseline sufficiency

Pass only if the current workflow is sufficiently documented to define what improvement means.

### Gate G3 — Technical plausibility

Pass only if no known technical, legal, security or data constraint makes the solution presently infeasible.

### Gate G4 — Buyer credibility

Pass only if a credible economic buyer and budget path are identified.

### Gate G5 — Value plausibility

Pass only if there is a traceable route from workflow improvement to economic or strategic value for the customer.

### Gate G6 — Internal operability

Pass only if Provena can plausibly run, maintain, service and update the solution without unacceptable cost, fragility or key-person dependency.

### Gate G7 — Competitive viability

Pass only if the solution has a credible advantage, gap, wedge or delivery model relative to current alternatives.

### Gate G8 — Ethical, legal and regulatory acceptability

Pass only if the proposed solution can be pursued within applicable ethical, legal, privacy, security and regulatory constraints.

---

## 9. Verdict rules

### BUILD PROTOTYPE

Return only when:

- all mandatory gates pass
- no unresolved blocker exists
- evidence is sufficient to define a testable prototype
- the weighted confidence-adjusted score meets the configured threshold
- workflow improvement is measurable
- buyer and value hypotheses are credible
- internal operational complexity is acceptable
- prototype cost is proportionate to expected learning value

BUILD PROTOTYPE means:

> The evidence justifies a bounded prototype or pilot designed to test the remaining material uncertainties.

It does not mean full product build, production deployment or commercial success.

### VALIDATE FURTHER

Return when:

- the solution remains plausible
- one or more critical evidence gaps remain
- a gate is unresolved rather than failed
- the next evidence-gathering action is identifiable and proportionate

The verdict must include a ranked validation plan with:

- missing evidence
- recommended method
- target participant or source
- success threshold
- estimated effort
- decision unlocked

### DO NOT BUILD

Return when:

- a mandatory gate fails
- negative evidence materially outweighs positive evidence
- no credible buyer exists
- economics are structurally weak
- incumbents adequately solve the problem with no viable differentiation
- technical or regulatory barriers are disproportionate
- internal operational burden is unacceptable
- the solution does not address the verified mechanism

The rejection reason must be explicit and reusable in future assessments.

---

## 10. Sensitivity and scenario analysis

Every SVR must include at least three scenarios:

- downside
- base
- upside

The engine must identify which assumptions most influence the verdict.

A BUILD PROTOTYPE verdict must not depend exclusively on an upside scenario.

Where a small change in one uncertain assumption changes the verdict, the record must be marked `BORDERLINE` and the assumption must become a priority validation target.

---

## 11. Evidence sufficiency states

Each category and gate must use one of:

- `SUPPORTED`
- `PARTIALLY_SUPPORTED`
- `UNSUPPORTED`
- `CONTRADICTED`
- `NOT_APPLICABLE`

`NOT_APPLICABLE` requires an explicit reason and cannot be used to avoid a difficult assessment.

---

## 12. Required outputs

The engine must generate:

1. Solution Validation Record
2. evidence register
3. current-state workflow
4. proposed-state workflow
5. workflow improvement table
6. buyer map
7. willingness-to-pay evidence register
8. competitive alternatives register
9. technical feasibility assessment
10. internal operational complexity assessment
11. customer economics model
12. Provena unit economics model
13. gate register
14. category scorecard
15. scenario and sensitivity analysis
16. missing evidence register
17. contradiction register
18. recommended validation plan
19. deterministic verdict
20. human-readable decision brief
21. machine-readable JSON output
22. input, output and rule-set hashes

---

## 13. Audit and reproducibility requirements

Each run must preserve:

- engine version
- methodology version
- scoring rule version
- source identifiers
- source retrieval timestamps
- content hashes
- structured inputs
- assumptions
- transformations
- calculations
- category outputs
- gate outputs
- final verdict
- mutation and repeatability results

Two runs with identical stable inputs and rule versions must produce identical outputs.

Retrieval metadata that does not alter business meaning must be excluded from stable business hashes.

Material business-field changes must be classified separately from metadata-only changes.

---

## 14. Testing requirements

Minimum automated test coverage must include:

- identical inputs produce identical verdicts
- evidence removal lowers confidence or changes sufficiency
- failed mandatory gates cannot be overridden by aggregate score
- unsupported positive claims are rejected
- contradictory evidence is preserved
- missing buyer evidence prevents BUILD PROTOTYPE
- unacceptable internal operational complexity prevents BUILD PROTOTYPE
- strong customer value cannot conceal negative Provena unit economics
- strong problem evidence cannot conceal weak solution linkage
- genuine DO NOT BUILD cases
- genuine VALIDATE FURTHER cases
- genuine BUILD PROTOTYPE cases
- borderline sensitivity cases
- metadata-only mutations do not alter business verdict
- material input mutations are detected and explained
- historical runs remain reproducible under their original rule versions

---

## 15. Human review boundaries

Human review is required for:

- approval of source authenticity classifications
- buyer interview interpretation
- legal and regulatory conclusions
- assumptions with material financial impact
- rule changes
- methodology version changes
- movement from BUILD PROTOTYPE to production investment

Human reviewers may challenge an output but must not silently overwrite it. Overrides require:

- reviewer identity
- reason
- evidence
- timestamp
- original verdict
- replacement decision

---

## 16. Initial implementation boundary

The first implementation should validate the method, not build a complete commercial platform.

Initial scope:

- one verified problem from the current Golden Study
- one primary solution hypothesis
- deterministic local execution
- structured YAML or JSON inputs
- SQLite or equivalent durable records
- command-line or test-first interface
- human-readable Markdown report
- machine-readable JSON report
- complete audit lineage
- automated tests

Excluded from the first implementation:

- Lovable integration
- public-facing UI
- autonomous purchasing decisions
- production customer deployment
- fabricated demo evidence
- opaque AI scoring
- unsupported market-size claims

---

## 17. Success criteria for SV Engine v1

SV Engine v1 is successful when it can:

1. ingest one legitimate verified-problem package from a Golden Study
2. register a proposed solution hypothesis
3. represent evidence across all mandatory categories
4. model the current and proposed workflow
5. calculate transparent scores and confidence
6. apply mandatory gates deterministically
7. return all three verdict classes in controlled fixtures
8. identify internal operational burden explicitly
9. produce reproducible reports and hashes
10. explain exactly what evidence is missing and what decision that evidence would unlock
11. withstand mutation and repeatability tests
12. avoid claiming that a prototype, product or market has been proven when it has not

---

## 18. Working terminology

- **Verified Problem:** A problem mechanism sufficiently supported by the Golden Study methodology.
- **Solution Hypothesis:** A proposed intervention intended to reduce or remove the verified mechanism.
- **Verifiable Solution:** A solution hypothesis with defined, measurable claims that can be tested.
- **SVR:** Solution Validation Record.
- **BUILD PROTOTYPE:** Evidence supports a bounded prototype or pilot.
- **VALIDATE FURTHER:** The opportunity remains plausible but material evidence is missing.
- **DO NOT BUILD:** Evidence does not justify further engineering investment.
- **Internal Operational Complexity:** Provena's ongoing difficulty and cost in running, maintaining, servicing, supporting and updating the solution.

---

## 19. Governing statement

The SV Engine exists to prevent Provena Foundry from confusing a real problem with a good product opportunity.

Its standard is not whether a solution sounds attractive. Its standard is whether traceable evidence supports a proportionate next investment.
