# SV Engine v1 Commercial and Operational Review

**Role:** Commercial and operational reviewer (read-only review stance)  
**Scope:** buyer logic, willingness to pay, customer economics, Provena economics, competition, and internal operating burden

## Conclusion

The engine keeps customer benefit separate from Provena's ability to operate profitably. A strong problem or strong customer value cannot compensate for missing buyer authority, non-positive Provena contribution, an absent competitive wedge, or unacceptable operating burden.

## Findings and Resolutions

### C-01 Buyer credibility required more than a user name

Resolution: G4 requires traceable support for buyer identity and budget path, then cross-checks the typed buyer map for economic buyer, budget source, and purchase authority. Missing fields produce `VALIDATE FURTHER`; evidence-backed absence produces `DO NOT BUILD`.

Status: Resolved.

### C-02 Customer value could have obscured weak Provena economics

Resolution: customer economics and Provena unit economics are separate models and categories. G6 independently checks that annual price exceeds annual cost to serve. The test suite proves strong customer value cannot override negative Provena economics.

Status: Resolved.

### C-03 Internal operating complexity needed structural veto power

Resolution: monthly operating effort, support per customer, update cadence, maintenance risks, service risks, complexity rating, confidence, assumptions, and key-person dependency are first-class fields. Configured high effort, support, disallowed rating, or key-person dependency fails G6 regardless of customer value.

Status: Resolved.

### C-04 Competitive viability needed an alternatives register

Resolution: G7 requires supported competitive-wedge evidence and at least one current alternative. The output bundle includes a separate competitive-alternatives register.

Status: Resolved.

### C-05 Prototype investment needed proportionality

Resolution: a global supported claim and scenario-level prototype cost versus expected learning value constrain `BUILD PROTOTYPE`. An explicitly disproportionate cost returns `DO NOT BUILD`; missing support returns `VALIDATE FURTHER`.

Status: Resolved.

## Residual Commercial Risks

1. Fixture prices, buyers, workflow values, and costs are synthetic. They demonstrate rule behavior only.
2. The economics models expose formulas and assumptions but are intentionally bounded; they are not revenue forecasts or accounting advice.
3. Buyer interviews, budget authority, procurement paths, legal conclusions, and material financial assumptions require accountable human review.
4. A real positive verdict remains approval for a bounded prototype only. Production investment needs separate field evidence and governance.

## Recommendation

Use the next milestone to assess one legitimate Golden Study handoff and one tightly bounded solution. Require direct buyer, workflow, competitive, technical, legal, customer-economics, and Provena-operability evidence before accepting a positive verdict.

