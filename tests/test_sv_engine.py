from __future__ import annotations

from copy import deepcopy
import json

import pytest

from sv_engine.domain.enums import GateStatus, VerdictValue
from sv_engine.domain.models import SolutionValidationInput
from sv_engine.fixtures import (
    borderline_case,
    build_prototype_case,
    do_not_build_no_buyer_case,
    do_not_build_operability_case,
    validate_further_case,
)
from sv_engine.reporting import write_outputs
from sv_engine.repositories import SQLiteSVRepository
from sv_engine.rules import load_rule_set
from sv_engine.rules.loader import DEFAULT_RULE_PATH
from sv_engine.services.engine import SolutionValidationEngine
from sv_engine.services.hashing import classify_input_change


@pytest.fixture
def engine() -> SolutionValidationEngine:
    return SolutionValidationEngine()


def _remove_evidence(payload: dict, evidence_id: str) -> dict:
    changed = deepcopy(payload)
    changed["evidence_items"] = [
        item for item in changed["evidence_items"] if item["evidence_id"] != evidence_id
    ]
    for claim in changed["validation_claims"]:
        claim["evidence_ids"] = [item for item in claim["evidence_ids"] if item != evidence_id]
    for workflow_name in ("current_workflow", "proposed_workflow"):
        for metric in changed[workflow_name]["metrics"]:
            metric["evidence_ids"] = [item for item in metric["evidence_ids"] if item != evidence_id]
    for section in ("buyer_map", "customer_economics", "provena_unit_economics", "internal_operational_complexity"):
        changed[section]["evidence_ids"] = [
            item for item in changed[section].get("evidence_ids", []) if item != evidence_id
        ]
    for competitor in changed["competitors"]:
        competitor["evidence_ids"] = [item for item in competitor["evidence_ids"] if item != evidence_id]
    return changed


def test_rule_contract_contains_all_categories_and_gates() -> None:
    rules = load_rule_set()
    assert len(rules.data["categories"]) == 12
    assert len(rules.data["gates"]) == 8
    assert {item["id"] for item in rules.data["gates"]} == {
        "G1_VERIFIED_PROBLEM_LINKAGE",
        "G2_BASELINE_SUFFICIENCY",
        "G3_TECHNICAL_PLAUSIBILITY",
        "G4_BUYER_CREDIBILITY",
        "G5_VALUE_PLAUSIBILITY",
        "G6_INTERNAL_OPERABILITY",
        "G7_COMPETITIVE_VIABILITY",
        "G8_ETHICAL_LEGAL_REGULATORY_ACCEPTABILITY",
    }


def test_identical_inputs_produce_identical_business_outputs(engine: SolutionValidationEngine) -> None:
    first = engine.evaluate_dict(build_prototype_case())
    second = engine.evaluate_dict(build_prototype_case())
    assert first.record.verdict == second.record.verdict
    assert first.record.output_hash == second.record.output_hash
    assert first.manifest.run_id == second.manifest.run_id
    assert first.manifest.execution_id != second.manifest.execution_id


def test_metadata_only_mutation_does_not_change_business_verdict(engine: SolutionValidationEngine) -> None:
    original = build_prototype_case()
    changed = deepcopy(original)
    changed["metadata"]["created_at"] = "2030-01-01T00:00:00+00:00"
    changed["evidence_items"][0]["retrieval_timestamp"] = "2030-01-01T00:00:00+00:00"
    first = engine.evaluate_dict(original)
    second = engine.evaluate_dict(changed)
    assert classify_input_change(original, changed).classification == "METADATA_ONLY"
    assert first.record.verdict.value == second.record.verdict.value
    assert first.record.stable_business_hash == second.record.stable_business_hash
    assert first.record.output_hash == second.record.output_hash
    assert first.record.input_hash != second.record.input_hash


def test_material_business_mutation_is_detected_and_explained(engine: SolutionValidationEngine) -> None:
    original = build_prototype_case()
    changed = deepcopy(original)
    changed["solution_hypothesis"]["statement"] = "A materially different solution scope."
    classification = classify_input_change(original, changed)
    assert classification.classification == "MATERIAL_BUSINESS_CHANGE"
    assert "solution_hypothesis.statement" in classification.changed_paths
    assert engine.evaluate_dict(original).record.stable_business_hash != engine.evaluate_dict(changed).record.stable_business_hash


def test_removing_evidence_lowers_confidence_or_sufficiency(engine: SolutionValidationEngine) -> None:
    full = engine.evaluate_dict(build_prototype_case()).record
    reduced = engine.evaluate_dict(_remove_evidence(build_prototype_case(), "EV-007")).record
    full_category = next(item for item in full.category_assessments if item.category_id == "C3_WORKFLOW_IMPROVEMENT")
    reduced_category = next(item for item in reduced.category_assessments if item.category_id == "C3_WORKFLOW_IMPROVEMENT")
    assert reduced_category.adjusted_score < full_category.adjusted_score


def test_failed_gate_cannot_be_overridden_by_high_score(engine: SolutionValidationEngine) -> None:
    result = engine.evaluate_dict(do_not_build_no_buyer_case()).record
    assert result.verdict.weighted_adjusted_score > 2.75
    assert result.verdict.value is VerdictValue.DO_NOT_BUILD
    assert next(item for item in result.gate_assessments if item.gate_id == "G4_BUYER_CREDIBILITY").status is GateStatus.FAIL


def test_missing_buyer_evidence_blocks_build(engine: SolutionValidationEngine) -> None:
    result = engine.evaluate_dict(validate_further_case()).record
    assert result.verdict.value is VerdictValue.VALIDATE_FURTHER
    assert next(item for item in result.gate_assessments if item.gate_id == "G4_BUYER_CREDIBILITY").status is GateStatus.UNRESOLVED
    assert result.validation_actions


def test_missing_baseline_blocks_build(engine: SolutionValidationEngine) -> None:
    payload = build_prototype_case()
    payload["current_workflow"]["metrics"] = []
    result = engine.evaluate_dict(payload).record
    assert result.verdict.value is VerdictValue.VALIDATE_FURTHER
    assert next(item for item in result.gate_assessments if item.gate_id == "G2_BASELINE_SUFFICIENCY").status is GateStatus.UNRESOLVED


def test_unacceptable_operational_complexity_blocks_build(engine: SolutionValidationEngine) -> None:
    result = engine.evaluate_dict(do_not_build_operability_case()).record
    gate = next(item for item in result.gate_assessments if item.gate_id == "G6_INTERNAL_OPERABILITY")
    assert gate.status is GateStatus.FAIL
    assert result.verdict.value is VerdictValue.DO_NOT_BUILD
    assert "operational" in result.verdict.explanation.lower()


def test_strong_customer_value_cannot_hide_negative_provena_economics(engine: SolutionValidationEngine) -> None:
    payload = build_prototype_case()
    for claim in payload["validation_claims"]:
        if claim["claim_id"] == "provena_economics_positive":
            claim.update({"value": False, "value_kind": "CALCULATED", "evidence_ids": ["EV-006"]})
    result = engine.evaluate_dict(payload).record
    assert result.customer_economics.annual_value == 180000
    assert result.verdict.value is VerdictValue.DO_NOT_BUILD
    assert next(item for item in result.gate_assessments if item.gate_id == "G6_INTERNAL_OPERABILITY").status is GateStatus.FAIL


def test_strong_problem_evidence_cannot_hide_weak_solution_linkage(engine: SolutionValidationEngine) -> None:
    payload = build_prototype_case()
    for claim in payload["validation_claims"]:
        if claim["claim_id"] == "problem_solution_linkage":
            claim.update({"value": False, "value_kind": "CONTRADICTION", "evidence_ids": ["EV-001"]})
    result = engine.evaluate_dict(payload).record
    assert result.verified_problem.confidence == 0.85
    assert result.verdict.value is VerdictValue.DO_NOT_BUILD
    assert next(item for item in result.gate_assessments if item.gate_id == "G1_VERIFIED_PROBLEM_LINKAGE").status is GateStatus.FAIL


def test_contradictory_evidence_is_preserved(engine: SolutionValidationEngine) -> None:
    result = engine.evaluate_dict(do_not_build_no_buyer_case()).record
    assert any("EV-009" in item.evidence_ids for item in result.contradictions)
    assert any(item.evidence_id == "EV-009" for item in result.evidence_items)


def test_build_prototype_fixture_is_genuine(engine: SolutionValidationEngine) -> None:
    result = engine.evaluate_dict(build_prototype_case()).record
    assert result.verdict.value is VerdictValue.BUILD_PROTOTYPE
    assert all(item.status is GateStatus.PASS for item in result.gate_assessments)
    assert result.verdict.borderline is False


def test_validate_further_fixture_is_genuine(engine: SolutionValidationEngine) -> None:
    result = engine.evaluate_dict(validate_further_case()).record
    assert result.verdict.value is VerdictValue.VALIDATE_FURTHER
    assert any(item.status is GateStatus.UNRESOLVED for item in result.gate_assessments)
    assert not any(item.status is GateStatus.FAIL for item in result.gate_assessments)


@pytest.mark.parametrize("fixture", [do_not_build_no_buyer_case, do_not_build_operability_case])
def test_materially_distinct_do_not_build_fixtures(engine: SolutionValidationEngine, fixture) -> None:
    result = engine.evaluate_dict(fixture()).record
    assert result.verdict.value is VerdictValue.DO_NOT_BUILD
    assert result.verdict.rejection_reasons


def test_borderline_sensitivity_generates_priority_action(engine: SolutionValidationEngine) -> None:
    result = engine.evaluate_dict(borderline_case()).record
    assert result.verdict.value is VerdictValue.VALIDATE_FURTHER
    assert result.verdict.borderline is True
    assert any(item.material for item in result.sensitivity_results)
    assert any(item.missing_evidence_id == "SENSITIVITY" for item in result.validation_actions)


def test_historical_rule_version_reproduces_result(engine: SolutionValidationEngine) -> None:
    historical_path = DEFAULT_RULE_PATH.with_name("sv_rules_v1.json")
    historical_engine = SolutionValidationEngine(load_rule_set(historical_path))
    first = historical_engine.evaluate_dict(build_prototype_case())
    second = historical_engine.evaluate_dict(build_prototype_case())
    assert first.manifest.scoring_rule_version == "SV-RULES-1.0"
    assert first.record.output_hash == second.record.output_hash


def test_malformed_handoff_input_is_rejected() -> None:
    payload = build_prototype_case()
    del payload["verified_problem"]["problem_mechanism"]
    with pytest.raises(ValueError, match="problem_mechanism"):
        SolutionValidationInput.from_dict(payload)


def test_internal_estimate_without_assumptions_is_rejected() -> None:
    payload = build_prototype_case()
    estimate = next(item for item in payload["evidence_items"] if item["evidence_class"] == "E6_INTERNAL_ESTIMATE")
    estimate["assumptions"] = []
    with pytest.raises(ValueError, match="Internal estimates"):
        SolutionValidationInput.from_dict(payload)


def test_approved_evidence_requires_review_identity() -> None:
    payload = build_prototype_case()
    payload["evidence_items"][0]["reviewed_by"] = ""
    with pytest.raises(ValueError, match="reviewed_by"):
        SolutionValidationInput.from_dict(payload)


def test_unsupported_positive_claim_receives_no_credit(engine: SolutionValidationEngine) -> None:
    payload = build_prototype_case()
    for claim in payload["validation_claims"]:
        if claim["claim_id"] == "competitive_wedge":
            claim["evidence_ids"] = []
    result = engine.evaluate_dict(payload).record
    category = next(item for item in result.category_assessments if item.category_id == "C8_MARKET_COMPETITION")
    gate = next(item for item in result.gate_assessments if item.gate_id == "G7_COMPETITIVE_VIABILITY")
    assert category.raw_score == 0
    assert gate.status is GateStatus.UNRESOLVED
    assert result.verdict.value is VerdictValue.VALIDATE_FURTHER


def test_reports_include_all_required_artifacts(tmp_path, engine: SolutionValidationEngine) -> None:
    result = engine.evaluate_dict(build_prototype_case())
    final_result, paths = write_outputs(result, tmp_path)
    required = {
        "sv_result",
        "decision_brief",
        "evidence_register",
        "buyer_map",
        "willingness_to_pay_evidence",
        "competitive_alternatives",
        "technical_feasibility_assessment",
        "category_scorecard",
        "gate_register",
        "missing_evidence_register",
        "contradiction_register",
        "workflow_comparison",
        "internal_operational_complexity",
        "customer_economics",
        "provena_unit_economics",
        "scenario_sensitivity",
        "ranked_validation_plan",
        "deterministic_verdict",
        "run_manifest",
    }
    assert required.issubset(paths)
    assert all(path.exists() for path in paths.values())
    assert "BUILD PROTOTYPE" in paths["decision_brief"].read_text(encoding="utf-8")
    manifest = json.loads(paths["run_manifest"].read_text(encoding="utf-8"))
    assert manifest["artifact_hashes"] == final_result.manifest.artifact_hashes


def test_sqlite_persistence_is_append_only_and_safe(tmp_path, engine: SolutionValidationEngine) -> None:
    repository = SQLiteSVRepository(tmp_path / "sv.db")
    first = engine.evaluate_dict(build_prototype_case())
    second = engine.evaluate_dict(build_prototype_case())
    repository.save(first)
    repository.save(second)
    runs = repository.list_runs()
    assert len(runs) == 2
    assert runs[0]["run_id"] == runs[1]["run_id"]
    assert repository.load_record(first.manifest.execution_id)["verdict"]["value"] == "BUILD PROTOTYPE"


def test_scenario_economics_constrain_the_final_verdict(engine: SolutionValidationEngine) -> None:
    payload = build_prototype_case()
    for scenario in payload["scenarios"]:
        scenario.update({"prototype_cost": 1000000, "expected_learning_value": 1000})
    result = engine.evaluate_dict(payload).record
    assert result.verdict.value is VerdictValue.DO_NOT_BUILD
    assert "base scenario" in result.verdict.explanation.lower()


def test_workflow_regression_fails_value_gate(engine: SolutionValidationEngine) -> None:
    payload = build_prototype_case()
    payload["proposed_workflow"]["steps"][0].update(
        {"handoffs": 8, "manual_entries": 8, "duplicated_work": True}
    )
    payload["proposed_workflow"]["metrics"][0]["value"] = 8
    payload["proposed_workflow"]["metrics"][1]["value"] = 90
    result = engine.evaluate_dict(payload).record
    gate = next(item for item in result.gate_assessments if item.gate_id == "G5_VALUE_PLAUSIBILITY")
    assert gate.status is GateStatus.FAIL
    assert result.verdict.value is VerdictValue.DO_NOT_BUILD


@pytest.mark.parametrize("invalid_verdict", ["CONTINUE RESEARCH", "BUILD PROTOTYPE", "REJECT"])
def test_only_build_candidate_handoffs_are_accepted(invalid_verdict: str) -> None:
    payload = build_prototype_case()
    payload["verified_problem"]["golden_study_verdict"] = invalid_verdict
    with pytest.raises(ValueError, match="BUILD CANDIDATE"):
        SolutionValidationInput.from_dict(payload)


def test_duplicate_evidence_content_cannot_inflate_a_run(engine: SolutionValidationEngine) -> None:
    payload = build_prototype_case()
    payload["evidence_items"][1]["content_hash"] = payload["evidence_items"][0]["content_hash"]
    with pytest.raises(ValueError, match="content hashes must be unique"):
        engine.evaluate_dict(payload)


def test_unrelated_claim_evidence_earns_no_credit(engine: SolutionValidationEngine) -> None:
    payload = build_prototype_case()
    claim = next(item for item in payload["validation_claims"] if item["claim_id"] == "competitive_wedge")
    claim["evidence_ids"] = ["EV-001"]
    result = engine.evaluate_dict(payload).record
    category = next(item for item in result.category_assessments if item.category_id == "C8_MARKET_COMPETITION")
    gate = next(item for item in result.gate_assessments if item.gate_id == "G7_COMPETITIVE_VIABILITY")
    assert category.raw_score == 0
    assert gate.status is GateStatus.UNRESOLVED
    assert result.verdict.value is VerdictValue.VALIDATE_FURTHER


def test_contradictory_evidence_cannot_support_a_positive_verdict(engine: SolutionValidationEngine) -> None:
    payload = build_prototype_case()
    contradiction = deepcopy(payload["evidence_items"][0])
    contradiction.update(
        {
            "evidence_id": "EV-CONTRADICTION",
            "content_hash": "sha256:contradiction-unique",
            "title": "Contradictory workflow observation",
            "relevant_claim": "The alleged workflow failure was not observed.",
            "contradiction_flag": True,
        }
    )
    payload["evidence_items"].append(contradiction)
    result = engine.evaluate_dict(payload).record
    category = next(item for item in result.category_assessments if item.category_id == "C1_PROBLEM_INHERITANCE")
    assert "EV-CONTRADICTION" not in category.evidence_ids
    assert category.contradiction_ids
    assert result.verdict.value is VerdictValue.VALIDATE_FURTHER


@pytest.mark.parametrize(
    "section",
    ["buyer_map", "customer_economics", "provena_unit_economics", "internal_operational_complexity"],
)
def test_unknown_material_evidence_references_are_rejected(
    engine: SolutionValidationEngine, section: str
) -> None:
    payload = build_prototype_case()
    payload[section]["evidence_ids"] = ["EV-DOES-NOT-EXIST"]
    with pytest.raises(ValueError, match="unknown evidence"):
        engine.evaluate_dict(payload)


def test_unknown_competitor_evidence_reference_is_rejected(engine: SolutionValidationEngine) -> None:
    payload = build_prototype_case()
    payload["competitors"][0]["evidence_ids"] = ["EV-DOES-NOT-EXIST"]
    with pytest.raises(ValueError, match="unknown evidence"):
        engine.evaluate_dict(payload)


def test_semantically_unrelated_material_reference_is_rejected(
    engine: SolutionValidationEngine,
) -> None:
    payload = build_prototype_case()
    payload["customer_economics"]["evidence_ids"] = ["EV-001"]
    with pytest.raises(ValueError, match="not linked to C7_CUSTOMER_ECONOMICS"):
        engine.evaluate_dict(payload)


def test_unreconciled_customer_and_provena_economics_fail_gates(
    engine: SolutionValidationEngine,
) -> None:
    payload = build_prototype_case()
    payload["customer_economics"].update(
        {"annual_value": 10000, "price_assumption": 50000, "payback_months": 1}
    )
    payload["provena_unit_economics"].update(
        {"gross_margin_percent": 99, "break_even_customer_count": 99}
    )
    result = engine.evaluate_dict(payload).record
    gates = {item.gate_id: item for item in result.gate_assessments}
    assert gates["G5_VALUE_PLAUSIBILITY"].status is GateStatus.FAIL
    assert gates["G6_INTERNAL_OPERABILITY"].status is GateStatus.FAIL
    assert result.verdict.value is VerdictValue.DO_NOT_BUILD


def test_low_internal_confidence_blocks_build(engine: SolutionValidationEngine) -> None:
    payload = build_prototype_case()
    payload["internal_operational_complexity"]["confidence"] = 0
    result = engine.evaluate_dict(payload).record
    gate = next(item for item in result.gate_assessments if item.gate_id == "G6_INTERNAL_OPERABILITY")
    assert gate.status is GateStatus.UNRESOLVED
    assert result.verdict.value is VerdictValue.VALIDATE_FURTHER


def test_zero_confidence_critical_category_blocks_build(engine: SolutionValidationEngine) -> None:
    payload = build_prototype_case()
    for evidence in payload["evidence_items"]:
        if "C8_MARKET_COMPETITION" in evidence["linked_categories"]:
            evidence["confidence_contribution"] = 0
    result = engine.evaluate_dict(payload).record
    category = next(item for item in result.category_assessments if item.category_id == "C8_MARKET_COMPETITION")
    assert category.confidence == 0
    assert result.verdict.value is VerdictValue.VALIDATE_FURTHER


def test_unreviewed_rule_mutation_is_rejected(tmp_path) -> None:
    payload = json.loads(DEFAULT_RULE_PATH.read_text(encoding="utf-8"))
    payload["verdict_thresholds"]["build_weighted_adjusted_score"] = 0
    changed = tmp_path / "unreviewed_rules.json"
    changed.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="not approved"):
        load_rule_set(changed)
