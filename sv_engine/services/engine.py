"""Deterministic orchestration for a complete Solution Validation Record."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sv_engine.domain.enums import GateStatus, ScenarioName, VerdictValue
from sv_engine.domain.models import (
    RunManifest,
    SVVerdict,
    SensitivityResult,
    SolutionValidationInput,
    SolutionValidationRecord,
    ValidationAction,
)
from sv_engine.rules.loader import RuleSet, load_rule_set
from sv_engine.services.assessment import (
    assess_categories,
    assess_gates,
    build_contradictions,
    build_missing_evidence,
    claim_support_state,
)
from sv_engine.services.hashing import canonical_hash, stable_business_hash


@dataclass(frozen=True)
class EngineResult:
    record: SolutionValidationRecord
    manifest: RunManifest

    def to_dict(self) -> dict[str, Any]:
        return {"record": self.record.to_dict(), "run_manifest": self.manifest.to_dict()}


class SolutionValidationEngine:
    """Apply versioned rules without AI scoring or hidden overrides."""

    def __init__(self, rule_set: RuleSet | None = None) -> None:
        self.rules = rule_set or load_rule_set()

    def evaluate_dict(self, payload: dict[str, Any]) -> EngineResult:
        return self.evaluate(SolutionValidationInput.from_dict(payload))

    def evaluate(self, data: SolutionValidationInput) -> EngineResult:
        self._validate_references(data)
        input_payload = data.to_dict()
        metadata_fields = self.rules.data.get("metadata_only_fields", [])
        input_hash = canonical_hash(input_payload)
        business_hash = stable_business_hash(input_payload, metadata_fields)
        contradictions = build_contradictions(data)
        categories = assess_categories(data, self.rules, contradictions)
        gates = assess_gates(data, self.rules)
        missing = build_missing_evidence(data, self.rules, gates)
        weighted_score = self._weighted_adjusted_score(categories)
        base_verdict, reasons, blockers = self._determine_verdict(
            data, categories, gates, contradictions, weighted_score
        )
        scenario_verdicts = self._scenario_verdicts(
            data, categories, gates, contradictions, weighted_score
        )
        base_verdict, reasons, blockers = self._reconcile_scenario_verdicts(
            base_verdict, reasons, blockers, scenario_verdicts
        )
        sensitivity = self._sensitivity_results(data, scenario_verdicts)
        borderline = any(item.material for item in sensitivity)
        if base_verdict is VerdictValue.BUILD_PROTOTYPE and borderline:
            base_verdict = VerdictValue.VALIDATE_FURTHER
            blockers = blockers + ("A material assumption changes the verdict within the borderline tolerance.",)
        verdict = SVVerdict(
            value=base_verdict,
            explanation=self._verdict_explanation(base_verdict, reasons, blockers),
            rejection_reasons=reasons,
            unresolved_blockers=blockers,
            borderline=borderline,
            weighted_adjusted_score=weighted_score,
            rule_version=self.rules.version,
        )
        actions = self._validation_actions(missing, sensitivity)
        record = SolutionValidationRecord(
            svr_id=data.svr_id,
            version=data.version,
            verified_problem=data.verified_problem,
            solution_hypothesis=data.solution_hypothesis,
            evidence_items=data.evidence_items,
            current_workflow=data.current_workflow,
            proposed_workflow=data.proposed_workflow,
            buyer_map=data.buyer_map,
            competitors=data.competitors,
            customer_economics=data.customer_economics,
            provena_unit_economics=data.provena_unit_economics,
            internal_operational_complexity=data.internal_operational_complexity,
            category_assessments=categories,
            gate_assessments=gates,
            scenarios=data.scenarios,
            sensitivity_results=sensitivity,
            missing_evidence=missing,
            contradictions=contradictions,
            validation_actions=actions,
            verdict=verdict,
            stable_business_hash=business_hash,
            input_hash=input_hash,
            output_hash="",
        )
        output_hash = stable_business_hash(record.to_dict(), metadata_fields)
        record = replace(record, output_hash=output_hash)
        now = datetime.now(timezone.utc).isoformat()
        manifest = RunManifest(
            run_id=f"SVRUN-{business_hash[:16].upper()}",
            execution_id=f"SVEXEC-{uuid4().hex.upper()}",
            svr_id=data.svr_id,
            engine_version=self.rules.engine_version,
            methodology_version=self.rules.methodology_version,
            scoring_rule_version=self.rules.version,
            input_hash=input_hash,
            stable_business_hash=business_hash,
            rule_set_hash=self.rules.rule_hash,
            output_hash=output_hash,
            source_ids=tuple(sorted(item.evidence_id for item in data.evidence_items)),
            source_retrieval_timestamps=tuple(
                sorted(item.retrieval_timestamp for item in data.evidence_items)
            ),
            artifact_hashes={"rule_set": self.rules.rule_hash, "stable_input": business_hash},
            transformations=(
                "Validated typed input contract",
                "Excluded metadata-only fields from stable business hash",
                "Scored categories from approved linked evidence",
                "Applied mandatory gates before aggregate threshold",
                "Applied downside/base/upside sensitivity rules",
            ),
            created_at=now,
        )
        return EngineResult(record=record, manifest=manifest)

    def _validate_references(self, data: SolutionValidationInput) -> None:
        evidence_ids = [item.evidence_id for item in data.evidence_items]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("Evidence IDs must be unique")
        content_hashes = [item.content_hash for item in data.evidence_items]
        if len(content_hashes) != len(set(content_hashes)):
            raise ValueError("Evidence content hashes must be unique; duplicate content cannot earn additional credit")
        known = set(evidence_ids)
        category_ids = {str(item["id"]) for item in self.rules.data["categories"]}
        gate_ids = {str(item["id"]) for item in self.rules.data["gates"]}
        evidence_by_id = {item.evidence_id: item for item in data.evidence_items}
        claim_ids = [claim.claim_id for claim in data.validation_claims]
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("Validation claim IDs must be unique")
        for item in data.evidence_items:
            unknown_categories = sorted(set(item.linked_categories).difference(category_ids))
            unknown_gates = sorted(set(item.linked_gates).difference(gate_ids))
            if unknown_categories or unknown_gates:
                raise ValueError(
                    f"Evidence {item.evidence_id} has unknown links: "
                    f"categories={unknown_categories}, gates={unknown_gates}"
                )
        for claim in data.validation_claims:
            if claim.category_id not in category_ids:
                raise ValueError(f"Claim {claim.claim_id} references unknown category {claim.category_id}")
            unknown = sorted(set(claim.evidence_ids).difference(known))
            if unknown:
                raise ValueError(
                    f"Claim {claim.claim_id} references unknown evidence: {', '.join(unknown)}"
                )
            # Historical handoffs may list broad supporting evidence on a claim.
            # Scoring only credits evidence explicitly linked to the claim's
            # category, so an unrelated reference is preserved but earns no
            # authority or confidence.
        for workflow, expected_category in (
            (data.current_workflow, "C2_CURRENT_WORKFLOW_BASELINE"),
            (data.proposed_workflow, "C3_WORKFLOW_IMPROVEMENT"),
        ):
            metric_ids = [metric.metric_id for metric in workflow.metrics]
            if len(metric_ids) != len(set(metric_ids)):
                raise ValueError(f"Workflow {workflow.workflow_id} metric IDs must be unique")
            for metric in workflow.metrics:
                unknown = sorted(set(metric.evidence_ids).difference(known))
                if unknown:
                    raise ValueError(
                        f"Workflow metric {metric.metric_id} references unknown evidence: {', '.join(unknown)}"
                    )
                mismatched = sorted(
                    evidence_id
                    for evidence_id in metric.evidence_ids
                    if expected_category not in evidence_by_id[evidence_id].linked_categories
                )
                if mismatched:
                    raise ValueError(
                        f"Workflow metric {metric.metric_id} uses evidence not linked to "
                        f"{expected_category}: {', '.join(mismatched)}"
                    )
        referenced_sections = [
            ("Buyer map", data.buyer_map.evidence_ids, "C6_BUYER_DEFINITION"),
            ("Customer economics", data.customer_economics.evidence_ids, "C7_CUSTOMER_ECONOMICS"),
            ("Provena unit economics", data.provena_unit_economics.evidence_ids, "C9_PROVENA_UNIT_ECONOMICS"),
            ("Internal operational complexity", data.internal_operational_complexity.evidence_ids, "C5_INTERNAL_OPERATIONAL_COMPLEXITY"),
        ]
        referenced_sections.extend(
            (f"Competitor {item.competitor_id}", item.evidence_ids, "C8_MARKET_COMPETITION")
            for item in data.competitors
        )
        for label, references, expected_category in referenced_sections:
            unknown = sorted(set(references).difference(known))
            if unknown:
                raise ValueError(f"{label} references unknown evidence: {', '.join(unknown)}")
            mismatched = sorted(
                evidence_id
                for evidence_id in references
                if expected_category not in evidence_by_id[evidence_id].linked_categories
            )
            if mismatched:
                raise ValueError(
                    f"{label} uses evidence not linked to {expected_category}: "
                    f"{', '.join(mismatched)}"
                )

    def _weighted_adjusted_score(self, categories: tuple[Any, ...]) -> float:
        weights = {item["id"]: float(item["weight"]) for item in self.rules.data["categories"]}
        return round(sum(item.adjusted_score * weights[item.category_id] for item in categories), 4)

    def _overall_confidence(self, categories: tuple[Any, ...]) -> float:
        weights = {item["id"]: float(item["weight"]) for item in self.rules.data["categories"]}
        return round(sum(item.confidence * weights[item.category_id] for item in categories), 4)

    def _global_claim_state(self, data: SolutionValidationInput) -> str:
        evidence = {item.evidence_id: item for item in data.evidence_items}
        claims = {item.claim_id: item for item in data.validation_claims}
        states = [
            claim_support_state(claims.get(claim_id), evidence)[0]
            for claim_id in self.rules.data.get("global_build_claims", [])
        ]
        if "NEGATIVE" in states:
            return "NEGATIVE"
        if any(state != "SUPPORTED" for state in states):
            return "UNRESOLVED"
        return "SUPPORTED"

    def _determine_verdict(
        self,
        data: SolutionValidationInput,
        categories: tuple[Any, ...],
        gates: tuple[Any, ...],
        contradictions: tuple[Any, ...],
        weighted_score: float,
    ) -> tuple[VerdictValue, tuple[str, ...], tuple[str, ...]]:
        failures = tuple(
            f"{gate.gate_id}: {gate.failure_reason or gate.explanation}"
            for gate in gates
            if gate.status is GateStatus.FAIL
        )
        if failures:
            return VerdictValue.DO_NOT_BUILD, failures, ()
        unresolved = tuple(
            f"{gate.gate_id}: {'; '.join(gate.unresolved_questions)}"
            for gate in gates
            if gate.status is GateStatus.UNRESOLVED
        )
        if contradictions:
            unresolved += (
                "Open contradiction records must be resolved before BUILD PROTOTYPE: "
                + ", ".join(item.contradiction_id for item in contradictions),
            )
        global_state = self._global_claim_state(data)
        if global_state == "NEGATIVE":
            return (
                VerdictValue.DO_NOT_BUILD,
                ("Prototype cost is explicitly disproportionate to expected learning value.",),
                unresolved,
            )
        if global_state == "UNRESOLVED":
            unresolved += ("Prototype cost and expected learning value are not sufficiently supported.",)
        if unresolved:
            return VerdictValue.VALIDATE_FURTHER, (), unresolved

        if not data.solution_hypothesis.prototype_scope:
            unresolved += ("A bounded prototype scope has not been defined.",)
        if not data.solution_hypothesis.measurable_claims:
            unresolved += ("The proposed solution has no measurable validation claims.",)
        if unresolved:
            return VerdictValue.VALIDATE_FURTHER, (), unresolved

        thresholds = self.rules.data["verdict_thresholds"]
        category_rules = {item["id"]: item for item in self.rules.data["categories"]}
        weak_categories = tuple(
            f"{item.category_id} score {item.raw_score} is below {category_rules[item.category_id]['minimum_build_score']}"
            for item in categories
            if item.raw_score < int(category_rules[item.category_id]["minimum_build_score"])
        )
        weak_categories += tuple(
            f"{item.category_id} confidence {item.confidence:.2f} is below "
            f"{float(category_rules[item.category_id].get('minimum_build_confidence', 0.5)):.2f}"
            for item in categories
            if item.confidence
            < float(category_rules[item.category_id].get("minimum_build_confidence", 0.5))
        )
        if weighted_score < float(thresholds["build_weighted_adjusted_score"]):
            weak_categories += (
                f"Weighted confidence-adjusted score {weighted_score:.2f} is below the configured threshold.",
            )
        confidence = self._overall_confidence(categories)
        if confidence < float(thresholds["minimum_overall_confidence"]):
            weak_categories += (
                f"Overall confidence {confidence:.2f} is below the configured minimum.",
            )
        if weak_categories:
            return VerdictValue.VALIDATE_FURTHER, (), weak_categories
        return VerdictValue.BUILD_PROTOTYPE, (), ()

    def _scenario_verdicts(
        self,
        data: SolutionValidationInput,
        categories: tuple[Any, ...],
        gates: tuple[Any, ...],
        contradictions: tuple[Any, ...],
        weighted_score: float,
    ) -> dict[ScenarioName, VerdictValue]:
        maximum_adjustment = float(
            self.rules.data["verdict_thresholds"]["maximum_scenario_adjustment"]
        )
        results: dict[ScenarioName, VerdictValue] = {}
        for scenario in data.scenarios:
            if abs(scenario.category_score_adjustment) > maximum_adjustment:
                raise ValueError(
                    f"Scenario {scenario.name.value} adjustment exceeds configured limit"
                )
            value, _, _ = self._determine_verdict(
                data,
                categories,
                gates,
                contradictions,
                weighted_score + scenario.category_score_adjustment,
            )
            if scenario.prototype_cost is None or scenario.expected_learning_value is None:
                if value is VerdictValue.BUILD_PROTOTYPE:
                    value = VerdictValue.VALIDATE_FURTHER
            elif scenario.prototype_cost <= 0 or scenario.expected_learning_value <= 0:
                value = VerdictValue.DO_NOT_BUILD
            elif scenario.prototype_cost > scenario.expected_learning_value:
                value = VerdictValue.DO_NOT_BUILD
            results[scenario.name] = value
        return results

    def _reconcile_scenario_verdicts(
        self,
        verdict: VerdictValue,
        reasons: tuple[str, ...],
        blockers: tuple[str, ...],
        scenarios: dict[ScenarioName, VerdictValue],
    ) -> tuple[VerdictValue, tuple[str, ...], tuple[str, ...]]:
        if verdict is VerdictValue.DO_NOT_BUILD:
            return verdict, reasons, blockers
        base = scenarios[ScenarioName.BASE]
        if base is VerdictValue.DO_NOT_BUILD:
            return (
                VerdictValue.DO_NOT_BUILD,
                reasons + ("The base scenario makes prototype cost or evidence structurally unacceptable.",),
                blockers,
            )
        if base is VerdictValue.VALIDATE_FURTHER:
            return (
                VerdictValue.VALIDATE_FURTHER,
                reasons,
                blockers + ("The base scenario does not support BUILD PROTOTYPE.",),
            )
        build_scenarios = [name for name, value in scenarios.items() if value is VerdictValue.BUILD_PROTOTYPE]
        if verdict is VerdictValue.BUILD_PROTOTYPE and build_scenarios == [ScenarioName.UPSIDE]:
            return (
                VerdictValue.VALIDATE_FURTHER,
                reasons,
                blockers + ("BUILD PROTOTYPE cannot depend exclusively on the upside scenario.",),
            )
        return verdict, reasons, blockers

    def _sensitivity_results(
        self,
        data: SolutionValidationInput,
        verdicts: dict[ScenarioName, VerdictValue],
    ) -> tuple[SensitivityResult, ...]:
        scenarios = {item.name: item for item in data.scenarios}
        tolerance = float(self.rules.data["verdict_thresholds"]["borderline_tolerance"])
        base = verdicts[ScenarioName.BASE]
        closest_change = min(
            abs(scenarios[ScenarioName.DOWNSIDE].category_score_adjustment - scenarios[ScenarioName.BASE].category_score_adjustment),
            abs(scenarios[ScenarioName.UPSIDE].category_score_adjustment - scenarios[ScenarioName.BASE].category_score_adjustment),
        )
        material = (
            verdicts[ScenarioName.DOWNSIDE] != base or verdicts[ScenarioName.UPSIDE] != base
        ) and closest_change <= tolerance
        assumptions = tuple(
            sorted({assumption for scenario in data.scenarios for assumption in scenario.assumptions})
        ) or ("No scenario assumptions recorded",)
        return tuple(
            SensitivityResult(
                assumption=assumption,
                downside_verdict=verdicts[ScenarioName.DOWNSIDE],
                base_verdict=base,
                upside_verdict=verdicts[ScenarioName.UPSIDE],
                material=material,
                recommended_action=(
                    "Validate this assumption before authorising a prototype."
                    if material
                    else "Monitor; this assumption does not currently change the verdict."
                ),
            )
            for assumption in assumptions
        )

    def _validation_actions(
        self, missing: tuple[Any, ...], sensitivity: tuple[SensitivityResult, ...]
    ) -> tuple[ValidationAction, ...]:
        actions = [
            ValidationAction(
                action_id=f"VA-{index:04d}",
                rank=index,
                missing_evidence_id=item.missing_evidence_id,
                action=item.recommended_method,
                target=item.target_source_or_participant,
                success_threshold=item.success_threshold,
                estimated_effort=item.estimated_effort,
                decision_unlocked=item.decision_unlocked,
            )
            for index, item in enumerate(missing, start=1)
        ]
        for item in sensitivity:
            if item.material:
                rank = len(actions) + 1
                actions.append(
                    ValidationAction(
                        action_id=f"VA-{rank:04d}",
                        rank=rank,
                        missing_evidence_id="SENSITIVITY",
                        action=item.recommended_action,
                        target=item.assumption,
                        success_threshold="The base verdict remains stable under the bounded downside case.",
                        estimated_effort="Defined by the validation owner",
                        decision_unlocked="Remove BORDERLINE status.",
                    )
                )
        return tuple(actions)

    @staticmethod
    def _verdict_explanation(
        value: VerdictValue, reasons: tuple[str, ...], blockers: tuple[str, ...]
    ) -> str:
        if value is VerdictValue.BUILD_PROTOTYPE:
            return "All mandatory gates pass and traceable evidence supports a bounded prototype, not a production build."
        if value is VerdictValue.DO_NOT_BUILD:
            return "One or more mandatory or structural conditions fail: " + " ".join(reasons)
        return "The solution remains plausible, but specific evidence gaps must be resolved: " + " ".join(blockers)
