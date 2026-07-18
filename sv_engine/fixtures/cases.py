"""Synthetic test inputs. Nothing in this module is production evidence."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def _evidence(
    evidence_id: str,
    evidence_class: str,
    title: str,
    categories: list[str],
    gates: list[str],
    confidence: float,
    *,
    assumptions: list[str] | None = None,
    contradiction: bool = False,
) -> dict[str, Any]:
    return {
        "evidence_id": evidence_id,
        "evidence_class": evidence_class,
        "title": title,
        "description": f"Synthetic test evidence for {title.lower()}.",
        "source_type": "synthetic_test_fixture",
        "source_locator": f"fixture://{evidence_id}",
        "source_organisation": "SV Engine Test Fixture",
        "date_observed_or_published": "2026-07-01",
        "retrieval_timestamp": "2026-07-01T12:00:00+00:00",
        "content_hash": f"fixture-hash-{evidence_id}",
        "relevant_claim": title,
        "linked_categories": categories,
        "linked_gates": gates,
        "review_state": "APPROVED",
        "limitations": ["Synthetic fixture; not real market or customer evidence."],
        "contradiction_flag": contradiction,
        "confidence_contribution": confidence,
        "provenance": "Generated solely for deterministic automated testing.",
        "reviewed_by": "SV-FIXTURE-REVIEWER",
        "reviewed_at": "2026-07-01T12:30:00+00:00",
        "assumptions": assumptions or [],
    }


def _claim(
    claim_id: str,
    category_id: str,
    evidence_ids: list[str],
    value: bool = True,
    value_kind: str = "OBSERVED",
) -> dict[str, Any]:
    return {
        "claim_id": claim_id,
        "category_id": category_id,
        "value": value,
        "value_kind": value_kind,
        "evidence_ids": evidence_ids,
        "explanation": f"Synthetic fixture condition for {claim_id}.",
        "uncertainty": "Fixture values demonstrate rule behaviour only.",
    }


def build_prototype_case() -> dict[str, Any]:
    """Materially complete synthetic case that earns BUILD PROTOTYPE."""
    evidence = [
        _evidence(
            "EV-001",
            "E1_DIRECT_OPERATIONAL",
            "Observed dispute workflow baseline",
            ["C1_PROBLEM_INHERITANCE", "C2_CURRENT_WORKFLOW_BASELINE", "C3_WORKFLOW_IMPROVEMENT", "C10_ADOPTION_RISK", "C11_COMPONENT_REUSABILITY"],
            ["G1_VERIFIED_PROBLEM_LINKAGE", "G2_BASELINE_SUFFICIENCY", "G5_VALUE_PLAUSIBILITY"],
            0.90,
        ),
        _evidence(
            "EV-002",
            "E2_DIRECT_BUYER",
            "Budget owner interview and pilot authority",
            ["C6_BUYER_DEFINITION", "C7_CUSTOMER_ECONOMICS", "C10_ADOPTION_RISK"],
            ["G4_BUYER_CREDIBILITY", "G5_VALUE_PLAUSIBILITY"],
            0.88,
        ),
        _evidence(
            "EV-003",
            "E3_DIRECT_USER",
            "Operator workflow observation",
            ["C2_CURRENT_WORKFLOW_BASELINE", "C3_WORKFLOW_IMPROVEMENT", "C10_ADOPTION_RISK", "C11_COMPONENT_REUSABILITY"],
            ["G2_BASELINE_SUFFICIENCY", "G5_VALUE_PLAUSIBILITY"],
            0.86,
        ),
        _evidence(
            "EV-004",
            "E4_AUTHORITATIVE_EXTERNAL",
            "Applicable dispute-handling requirements",
            ["C1_PROBLEM_INHERITANCE", "C4_TECHNICAL_FEASIBILITY", "C8_MARKET_COMPETITION", "C12_STRATEGIC_FIT"],
            ["G1_VERIFIED_PROBLEM_LINKAGE", "G3_TECHNICAL_PLAUSIBILITY", "G8_ETHICAL_LEGAL_REGULATORY_ACCEPTABILITY"],
            0.82,
        ),
        _evidence(
            "EV-005",
            "E5_COMPETITIVE_MARKET",
            "Documented competitive gap",
            ["C8_MARKET_COMPETITION", "C11_COMPONENT_REUSABILITY", "C12_STRATEGIC_FIT"],
            ["G7_COMPETITIVE_VIABILITY"],
            0.78,
        ),
        _evidence(
            "EV-006",
            "E6_INTERNAL_ESTIMATE",
            "Engineering and service cost estimate",
            ["C4_TECHNICAL_FEASIBILITY", "C5_INTERNAL_OPERATIONAL_COMPLEXITY", "C9_PROVENA_UNIT_ECONOMICS"],
            ["G3_TECHNICAL_PLAUSIBILITY", "G6_INTERNAL_OPERABILITY"],
            0.70,
            assumptions=["Three-month bounded prototype", "No customer-specific fork"],
        ),
        _evidence(
            "EV-007",
            "E7_PROTOTYPE",
            "Controlled workflow simulation",
            ["C3_WORKFLOW_IMPROVEMENT", "C4_TECHNICAL_FEASIBILITY", "C5_INTERNAL_OPERATIONAL_COMPLEXITY", "C7_CUSTOMER_ECONOMICS", "C9_PROVENA_UNIT_ECONOMICS", "C10_ADOPTION_RISK", "C11_COMPONENT_REUSABILITY"],
            ["G3_TECHNICAL_PLAUSIBILITY", "G5_VALUE_PLAUSIBILITY", "G6_INTERNAL_OPERABILITY"],
            0.90,
        ),
        _evidence(
            "EV-008",
            "E2_DIRECT_BUYER",
            "Written budget and procurement path",
            ["C6_BUYER_DEFINITION", "C7_CUSTOMER_ECONOMICS", "C9_PROVENA_UNIT_ECONOMICS", "C12_STRATEGIC_FIT"],
            ["G4_BUYER_CREDIBILITY", "G5_VALUE_PLAUSIBILITY"],
            0.92,
        ),
    ]
    claims = [
        _claim("problem_solution_linkage", "C1_PROBLEM_INHERITANCE", ["EV-001", "EV-004"]),
        _claim("baseline_documented", "C2_CURRENT_WORKFLOW_BASELINE", ["EV-001", "EV-003"]),
        _claim("improvement_measurable", "C3_WORKFLOW_IMPROVEMENT", ["EV-001", "EV-003", "EV-007"]),
        _claim("technical_plausible", "C4_TECHNICAL_FEASIBILITY", ["EV-004", "EV-007"]),
        _claim("internal_operability_acceptable", "C5_INTERNAL_OPERATIONAL_COMPLEXITY", ["EV-006", "EV-007"], value_kind="BOUNDED_ESTIMATE"),
        _claim("buyer_identified", "C6_BUYER_DEFINITION", ["EV-002", "EV-008"]),
        _claim("budget_path_identified", "C6_BUYER_DEFINITION", ["EV-008"]),
        _claim("customer_value_positive", "C7_CUSTOMER_ECONOMICS", ["EV-002", "EV-007"]),
        _claim("value_traceable", "C7_CUSTOMER_ECONOMICS", ["EV-001", "EV-002"]),
        _claim("competitive_wedge", "C8_MARKET_COMPETITION", ["EV-005"]),
        _claim("provena_economics_positive", "C9_PROVENA_UNIT_ECONOMICS", ["EV-006", "EV-007", "EV-008"], value_kind="CALCULATED"),
        _claim("adoption_risk_acceptable", "C10_ADOPTION_RISK", ["EV-003", "EV-007"]),
        _claim("solution_reusable", "C11_COMPONENT_REUSABILITY", ["EV-001", "EV-007"]),
        _claim("strategic_fit", "C12_STRATEGIC_FIT", ["EV-004", "EV-005"]),
        _claim("ethical_legal_regulatory_acceptable", "C4_TECHNICAL_FEASIBILITY", ["EV-004"]),
        _claim("prototype_cost_proportionate", "C9_PROVENA_UNIT_ECONOMICS", ["EV-006", "EV-007"], value_kind="CALCULATED"),
    ]
    return {
        "schema_version": "1.0",
        "svr_id": "SVR-FIXTURE-BUILD-001",
        "version": "1.0",
        "verified_problem": {
            "schema_version": "1.0",
            "verified_problem_id": "VP-FIXTURE-001",
            "golden_study_id": "GS-FIXTURE-001",
            "golden_study_verdict": "BUILD CANDIDATE",
            "evidence_summary": "Synthetic verified-problem handoff for SV Engine testing.",
            "problem_mechanism": "Evidence submitted during a dispute is not consistently routed to the investigation step.",
            "affected_workflow": "Dispute intake, evidence routing and investigation",
            "affected_organisation_type": "Consumer reporting organisation",
            "known_consequences": ["Rework", "Delayed resolution", "Weak audit trace"],
            "source_references": ["fixture://golden-study/result"],
            "evidence_lineage": ["GS-EV-FIXTURE-001", "GS-EV-FIXTURE-002"],
            "independent_source_family_count": 2,
            "confidence": 0.85,
            "limitations": ["Synthetic fixture; no market claim may be drawn from it."]
        },
        "solution_hypothesis": {
            "solution_id": "SOL-FIXTURE-001",
            "statement": "A bounded evidence-intake and dispute-routing component may reduce document mismatches and rework.",
            "intended_user": "Dispute operations analyst",
            "intended_buyer_hypothesis": "Head of consumer dispute operations",
            "scope_boundaries": ["Intake", "Routing", "Audit trail", "No autonomous adjudication"],
            "measurable_claims": ["Reduce manual handoffs", "Reduce evidence mismatches"],
            "prototype_scope": "One workflow, one document type, synthetic or approved test records only",
            "estimated_learning_value": 60000
        },
        "evidence_items": evidence,
        "current_workflow": {
            "workflow_id": "WF-CURRENT-001",
            "state": "current",
            "steps": [
                {"step_id": "CW-1", "name": "Receive dispute", "actor": "Intake analyst", "systems": ["case system"], "inputs": ["dispute", "documents"], "outputs": ["case"], "handoffs": 1, "manual_entries": 2, "duplicated_work": True, "errors": ["document mismatch"], "rework": ["re-key case"], "exceptions": ["unsupported file"], "compliance_risk": "missed evidence", "customer_impact": "delay"},
                {"step_id": "CW-2", "name": "Route evidence", "actor": "Queue analyst", "systems": ["shared mailbox", "case system"], "inputs": ["case"], "outputs": ["investigation package"], "handoffs": 2, "manual_entries": 1, "duplicated_work": True, "errors": ["wrong queue"], "rework": ["reroute"], "exceptions": ["missing identifier"], "compliance_risk": "incomplete investigation", "customer_impact": "repeated submission"}
            ],
            "metrics": [
                {"metric_id": "CM-1", "name": "Manual handoffs per case", "value_kind": "OBSERVED", "value": 3, "unit": "handoffs", "evidence_ids": ["EV-001"]},
                {"metric_id": "CM-2", "name": "Handling time", "value_kind": "OBSERVED", "value": 42, "unit": "minutes", "evidence_ids": ["EV-001"]}
            ]
        },
        "proposed_workflow": {
            "workflow_id": "WF-PROPOSED-001",
            "state": "proposed",
            "steps": [
                {"step_id": "PW-1", "name": "Validate and route evidence", "actor": "Intake analyst", "systems": ["bounded prototype", "case system"], "inputs": ["dispute", "documents"], "outputs": ["traceable investigation package"], "handoffs": 1, "manual_entries": 1, "duplicated_work": False, "errors": [], "rework": [], "exceptions": ["unsupported file"], "compliance_risk": "human review retained", "customer_impact": "fewer resubmissions"}
            ],
            "metrics": [
                {"metric_id": "PM-1", "name": "Manual handoffs per case", "value_kind": "CALCULATED", "value": 1, "unit": "handoffs", "evidence_ids": ["EV-007"]},
                {"metric_id": "PM-2", "name": "Handling time", "value_kind": "BOUNDED_ESTIMATE", "value": 25, "unit": "minutes", "lower_bound": 20, "upper_bound": 32, "evidence_ids": ["EV-007"], "assumptions": ["Existing case API remains available"]}
            ]
        },
        "buyer_map": {
            "economic_buyer": "Head of consumer dispute operations",
            "operational_owner": "Dispute operations manager",
            "technical_approver": "Enterprise architecture lead",
            "compliance_approver": "Consumer compliance officer",
            "end_users": ["Intake analyst", "Investigator"],
            "budget_source": "Operations transformation budget",
            "purchase_authority": "Named economic buyer has pilot authority",
            "urgency": "Current rework budget is material",
            "consequences_of_inaction": ["Continuing rework", "Weak evidence trace"],
            "procurement_path": "Bounded pilot purchase",
            "evidence_ids": ["EV-002", "EV-008"]
        },
        "competitors": [
            {"competitor_id": "COMP-FIXTURE-001", "name": "Manual case-system configuration", "alternative_type": "internal alternative", "strengths": ["Already deployed"], "weaknesses": ["Manual evidence matching"], "pricing": "Internal labour", "switching_cost": "Moderate", "differentiation": "Traceable evidence routing without replacing adjudication", "evidence_ids": ["EV-005"]}
        ],
        "customer_economics": {
            "annual_value": 180000,
            "price_assumption": 48000,
            "payback_months": 3.2,
            "formulae": ["annual_value = observed_rework_hours * loaded_hourly_cost"],
            "assumptions": ["Observed fixture volume remains stable"],
            "evidence_ids": ["EV-001", "EV-002", "EV-007"]
        },
        "provena_unit_economics": {
            "development_cost": 25000,
            "implementation_cost_per_customer": 8000,
            "annual_cost_to_serve_per_customer": 9000,
            "annual_price": 48000,
            "gross_margin_percent": 81.25,
            "break_even_customer_count": 0.81,
            "formulae": ["gross_margin = (annual_price - annual_cost_to_serve) / annual_price", "break_even_customers = development_cost / (annual_price - annual_cost_to_serve - implementation_cost)"],
            "assumptions": ["No customer-specific fork", "One bounded integration"],
            "evidence_ids": ["EV-006", "EV-007", "EV-008"]
        },
        "internal_operational_complexity": {
            "monthly_operating_effort_hours": 24,
            "support_effort_hours_per_customer": 4,
            "expected_update_cadence": "Monthly maintenance window",
            "principal_maintenance_risks": ["Case-system API change"],
            "principal_service_risks": ["Customer-specific taxonomy mapping"],
            "operational_complexity_rating": "MEDIUM",
            "confidence": 0.72,
            "key_person_dependency": False,
            "evidence_ids": ["EV-006", "EV-007"],
            "assumptions": ["Shared configuration model"]
        },
        "validation_claims": claims,
        "scenarios": [
            {"name": "downside", "category_score_adjustment": -0.10, "assumptions": ["Integration takes 20% longer"], "prototype_cost": 30000, "expected_learning_value": 60000},
            {"name": "base", "category_score_adjustment": 0.0, "assumptions": ["Bounded integration succeeds"], "prototype_cost": 25000, "expected_learning_value": 60000},
            {"name": "upside", "category_score_adjustment": 0.10, "assumptions": ["Reusable connector reduces effort"], "prototype_cost": 22000, "expected_learning_value": 65000}
        ],
        "metadata": {"fixture": True, "created_at": "2026-07-01T12:00:00+00:00"}
    }


def validate_further_case() -> dict[str, Any]:
    payload = deepcopy(build_prototype_case())
    payload["svr_id"] = "SVR-FIXTURE-VALIDATE-001"
    payload["evidence_items"] = [item for item in payload["evidence_items"] if item["evidence_id"] not in {"EV-002", "EV-008"}]
    payload["validation_claims"] = [
        item
        for item in payload["validation_claims"]
        if item["claim_id"] not in {"buyer_identified", "budget_path_identified", "customer_value_positive"}
        and not set(item["evidence_ids"]).intersection({"EV-002", "EV-008"})
    ]
    payload["buyer_map"].update({"economic_buyer": "unknown", "budget_source": "unknown", "purchase_authority": "unknown", "evidence_ids": []})
    return payload


def do_not_build_no_buyer_case() -> dict[str, Any]:
    payload = deepcopy(build_prototype_case())
    payload["svr_id"] = "SVR-FIXTURE-REJECT-BUYER-001"
    negative = _evidence(
        "EV-009",
        "E2_DIRECT_BUYER",
        "Buyer declined ownership and budget",
        ["C6_BUYER_DEFINITION", "C7_CUSTOMER_ECONOMICS"],
        ["G4_BUYER_CREDIBILITY", "G5_VALUE_PLAUSIBILITY"],
        0.90,
        contradiction=True,
    )
    payload["evidence_items"].append(negative)
    for claim in payload["validation_claims"]:
        if claim["claim_id"] in {"buyer_identified", "budget_path_identified"}:
            claim.update({"value": False, "value_kind": "CONTRADICTION", "evidence_ids": ["EV-009"]})
    return payload


def do_not_build_operability_case() -> dict[str, Any]:
    payload = deepcopy(build_prototype_case())
    payload["svr_id"] = "SVR-FIXTURE-REJECT-OPERABILITY-001"
    payload["internal_operational_complexity"].update(
        {
            "monthly_operating_effort_hours": 240,
            "support_effort_hours_per_customer": 60,
            "operational_complexity_rating": "HIGH",
            "key_person_dependency": True,
            "principal_maintenance_risks": ["Customer-specific code fork for every deployment"],
            "principal_service_risks": ["Continuous manual exception handling"],
        }
    )
    for claim in payload["validation_claims"]:
        if claim["claim_id"] == "internal_operability_acceptable":
            claim.update({"value": False, "value_kind": "CALCULATED", "evidence_ids": ["EV-006"]})
    return payload


def borderline_case() -> dict[str, Any]:
    payload = deepcopy(build_prototype_case())
    payload["svr_id"] = "SVR-FIXTURE-BORDERLINE-001"
    for item in payload["evidence_items"]:
        if item["evidence_class"] != "E6_INTERNAL_ESTIMATE":
            item["confidence_contribution"] = 0.80
    payload["scenarios"] = [
        {"name": "downside", "category_score_adjustment": -0.25, "assumptions": ["Observed improvement is 15% lower"], "prototype_cost": 30000, "expected_learning_value": 60000},
        {"name": "base", "category_score_adjustment": 0.0, "assumptions": ["Observed improvement is sustained"], "prototype_cost": 25000, "expected_learning_value": 60000},
        {"name": "upside", "category_score_adjustment": 0.20, "assumptions": ["Reusable connector reduces effort"], "prototype_cost": 22000, "expected_learning_value": 65000},
    ]
    return payload
