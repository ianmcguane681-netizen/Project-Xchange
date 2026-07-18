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
        base_verdict, reasons, blockers = self._determine_verdict(data, categories, gates, weighted_score)
        scenario_verdicts = self._scenario_verdicts(data, categories, gates, weighted_score)
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
        known = set(evidence_ids)
        for claim in data.validation_claims:
            unknown = sorted(set(claim.evidence_ids).difference(known))
            if unknown:
                raise ValueError(
                    f"Claim {claim.claim_id} references unknown evidence: {', '.join(unknown)}"
                )
        for workflow in (data.current_workflow, data.proposed_workflow):
            for metric in workflow.metrics:
                unknown = sorted(set(metric.evidence_ids).difference(known))
                if unknown:
                    raise ValueError(
                        f"Workflow metric {metric.metric_id} references unknown evidence: {', '.join(unknown)}"
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
        weighted_score: float,
    ) -> dict[ScenarioName, VerdictValue]:
        failed = any(item.status is GateStatus.FAIL for item in gates)
        unresolved = any(item.status is GateStatus.UNRESOLVED for item in gates)
        maximum_adjustment = float(
            self.rules.data["verdict_thresholds"]["maximum_scenario_adjustment"]
        )
        threshold = float(
            self.rules.data["verdict_thresholds"]["build_weighted_adjusted_score"]
        )
        global_state = self._global_claim_state(data)
        results: dict[ScenarioName, VerdictValue] = {}
        for scenario in data.scenarios:
            if abs(scenario.category_score_adjustment) > maximum_adjustment:
                raise ValueError(
                    f"Scenario {scenario.name.value} adjustment exceeds configured limit"
                )
            if failed or global_state == "NEGATIVE":
                value = VerdictValue.DO_NOT_BUILD
            elif unresolved or global_state == "UNRESOLVED":
                value = VerdictValue.VALIDATE_FURTHER
            elif (
                scenario.prototype_cost is not None
                and scenario.expected_learning_value is not None
                and scenario.prototype_cost > scenario.expected_learning_value
            ):
                value = VerdictValue.DO_NOT_BUILD
            elif weighted_score + scenario.category_score_adjustment >= threshold:
                value = VerdictValue.BUILD_PROTOTYPE
            else:
                value = VerdictValue.VALIDATE_FURTHER
            results[scenario.name] = value
        return results

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
