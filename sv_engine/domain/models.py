"""Source-agnostic typed entities for deterministic solution validation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any

from sv_engine.domain.enums import (
    EvidenceClass,
    EvidenceSufficiency,
    GateStatus,
    ReviewState,
    ScenarioName,
    ValueKind,
    VerdictValue,
)

SCHEMA_VERSION = "1.0"


def _serialise(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _serialise(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _serialise(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialise(item) for item in value]
    return value


class ModelMixin:
    def to_dict(self) -> dict[str, Any]:
        return _serialise(self)


def _tuple(data: dict[str, Any], key: str) -> tuple[Any, ...]:
    return tuple(data.get(key) or ())


@dataclass(frozen=True)
class VerifiedProblemPackage(ModelMixin):
    verified_problem_id: str
    golden_study_id: str
    golden_study_verdict: str
    evidence_summary: str
    problem_mechanism: str
    affected_workflow: str
    affected_organisation_type: str
    known_consequences: tuple[str, ...]
    source_references: tuple[str, ...]
    evidence_lineage: tuple[str, ...]
    independent_source_family_count: int
    confidence: float
    limitations: tuple[str, ...] = ()
    schema_version: str = SCHEMA_VERSION

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VerifiedProblemPackage":
        required = (
            "verified_problem_id",
            "golden_study_id",
            "golden_study_verdict",
            "evidence_summary",
            "problem_mechanism",
            "affected_workflow",
            "affected_organisation_type",
        )
        missing = [key for key in required if not data.get(key)]
        if missing:
            raise ValueError(f"Verified problem package missing: {', '.join(missing)}")
        for key in ("known_consequences", "source_references", "evidence_lineage"):
            if not data.get(key):
                raise ValueError(f"Verified problem package requires non-empty {key}")
        confidence = float(data.get("confidence", 0.0))
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("Verified problem confidence must be between 0 and 1")
        verdict = str(data["golden_study_verdict"]).strip().upper()
        if verdict != "BUILD CANDIDATE":
            raise ValueError(
                "SV Engine requires a Golden Study BUILD CANDIDATE handoff; "
                f"received {verdict or 'empty verdict'}"
            )
        return cls(
            verified_problem_id=str(data["verified_problem_id"]),
            golden_study_id=str(data["golden_study_id"]),
            golden_study_verdict=verdict,
            evidence_summary=str(data["evidence_summary"]),
            problem_mechanism=str(data["problem_mechanism"]),
            affected_workflow=str(data["affected_workflow"]),
            affected_organisation_type=str(data["affected_organisation_type"]),
            known_consequences=tuple(str(item) for item in _tuple(data, "known_consequences")),
            source_references=tuple(str(item) for item in _tuple(data, "source_references")),
            evidence_lineage=tuple(str(item) for item in _tuple(data, "evidence_lineage")),
            independent_source_family_count=int(data.get("independent_source_family_count", 0)),
            confidence=confidence,
            limitations=tuple(str(item) for item in _tuple(data, "limitations")),
            schema_version=str(data.get("schema_version", SCHEMA_VERSION)),
        )


@dataclass(frozen=True)
class SolutionHypothesis(ModelMixin):
    solution_id: str
    statement: str
    intended_user: str
    intended_buyer_hypothesis: str
    scope_boundaries: tuple[str, ...]
    measurable_claims: tuple[str, ...]
    prototype_scope: str
    estimated_learning_value: float | None = None
    schema_version: str = SCHEMA_VERSION

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SolutionHypothesis":
        required = ("solution_id", "statement", "intended_user", "intended_buyer_hypothesis")
        missing = [key for key in required if not data.get(key)]
        if missing:
            raise ValueError(f"Solution hypothesis missing: {', '.join(missing)}")
        return cls(
            solution_id=str(data["solution_id"]),
            statement=str(data["statement"]),
            intended_user=str(data["intended_user"]),
            intended_buyer_hypothesis=str(data["intended_buyer_hypothesis"]),
            scope_boundaries=tuple(str(item) for item in _tuple(data, "scope_boundaries")),
            measurable_claims=tuple(str(item) for item in _tuple(data, "measurable_claims")),
            prototype_scope=str(data.get("prototype_scope", "")),
            estimated_learning_value=(
                float(data["estimated_learning_value"])
                if data.get("estimated_learning_value") is not None
                else None
            ),
            schema_version=str(data.get("schema_version", SCHEMA_VERSION)),
        )


@dataclass(frozen=True)
class EvidenceItem(ModelMixin):
    evidence_id: str
    evidence_class: EvidenceClass
    title: str
    description: str
    source_type: str
    source_locator: str
    source_organisation: str
    date_observed_or_published: str
    retrieval_timestamp: str
    content_hash: str
    relevant_claim: str
    linked_categories: tuple[str, ...]
    linked_gates: tuple[str, ...]
    review_state: ReviewState
    limitations: tuple[str, ...]
    contradiction_flag: bool
    confidence_contribution: float
    provenance: str
    reviewed_by: str = ""
    reviewed_at: str = ""
    assumptions: tuple[str, ...] = ()
    schema_version: str = SCHEMA_VERSION

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceItem":
        required = (
            "evidence_id",
            "evidence_class",
            "title",
            "description",
            "source_type",
            "source_locator",
            "source_organisation",
            "date_observed_or_published",
            "retrieval_timestamp",
            "content_hash",
            "relevant_claim",
            "provenance",
        )
        missing = [key for key in required if data.get(key) in (None, "")]
        if missing:
            raise ValueError(f"Evidence item missing: {', '.join(missing)}")
        evidence_class = EvidenceClass(str(data["evidence_class"]))
        assumptions = tuple(str(item) for item in _tuple(data, "assumptions"))
        if evidence_class is EvidenceClass.INTERNAL_ESTIMATE and not assumptions:
            raise ValueError("Internal estimates must expose at least one assumption")
        confidence = float(data.get("confidence_contribution", 0.0))
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("Evidence confidence contribution must be between 0 and 1")
        review_state = ReviewState(str(data.get("review_state", ReviewState.PENDING_REVIEW.value)))
        reviewed_by = str(data.get("reviewed_by", ""))
        reviewed_at = str(data.get("reviewed_at", ""))
        if review_state is ReviewState.APPROVED and (not reviewed_by or not reviewed_at):
            raise ValueError("Approved evidence must record reviewed_by and reviewed_at")
        return cls(
            evidence_id=str(data["evidence_id"]),
            evidence_class=evidence_class,
            title=str(data["title"]),
            description=str(data["description"]),
            source_type=str(data["source_type"]),
            source_locator=str(data["source_locator"]),
            source_organisation=str(data["source_organisation"]),
            date_observed_or_published=str(data["date_observed_or_published"]),
            retrieval_timestamp=str(data["retrieval_timestamp"]),
            content_hash=str(data["content_hash"]),
            relevant_claim=str(data["relevant_claim"]),
            linked_categories=tuple(str(item) for item in _tuple(data, "linked_categories")),
            linked_gates=tuple(str(item) for item in _tuple(data, "linked_gates")),
            review_state=review_state,
            limitations=tuple(str(item) for item in _tuple(data, "limitations")),
            contradiction_flag=bool(data.get("contradiction_flag", False)),
            confidence_contribution=confidence,
            provenance=str(data["provenance"]),
            reviewed_by=reviewed_by,
            reviewed_at=reviewed_at,
            assumptions=assumptions,
            schema_version=str(data.get("schema_version", SCHEMA_VERSION)),
        )


@dataclass(frozen=True)
class WorkflowMetric(ModelMixin):
    metric_id: str
    name: str
    value_kind: ValueKind
    value: float | str | None
    unit: str
    evidence_ids: tuple[str, ...]
    lower_bound: float | None = None
    upper_bound: float | None = None
    assumptions: tuple[str, ...] = ()
    schema_version: str = SCHEMA_VERSION

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkflowMetric":
        return cls(
            metric_id=str(data["metric_id"]),
            name=str(data["name"]),
            value_kind=ValueKind(str(data.get("value_kind", ValueKind.UNKNOWN.value))),
            value=data.get("value"),
            unit=str(data.get("unit", "")),
            evidence_ids=tuple(str(item) for item in _tuple(data, "evidence_ids")),
            lower_bound=float(data["lower_bound"]) if data.get("lower_bound") is not None else None,
            upper_bound=float(data["upper_bound"]) if data.get("upper_bound") is not None else None,
            assumptions=tuple(str(item) for item in _tuple(data, "assumptions")),
            schema_version=str(data.get("schema_version", SCHEMA_VERSION)),
        )


@dataclass(frozen=True)
class WorkflowStep(ModelMixin):
    step_id: str
    name: str
    actor: str
    systems: tuple[str, ...]
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    handoffs: int = 0
    manual_entries: int = 0
    duplicated_work: bool = False
    errors: tuple[str, ...] = ()
    rework: tuple[str, ...] = ()
    exceptions: tuple[str, ...] = ()
    compliance_risk: str = "unknown"
    customer_impact: str = "unknown"
    schema_version: str = SCHEMA_VERSION

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkflowStep":
        return cls(
            step_id=str(data["step_id"]),
            name=str(data["name"]),
            actor=str(data.get("actor", "unknown")),
            systems=tuple(str(item) for item in _tuple(data, "systems")),
            inputs=tuple(str(item) for item in _tuple(data, "inputs")),
            outputs=tuple(str(item) for item in _tuple(data, "outputs")),
            handoffs=int(data.get("handoffs", 0)),
            manual_entries=int(data.get("manual_entries", 0)),
            duplicated_work=bool(data.get("duplicated_work", False)),
            errors=tuple(str(item) for item in _tuple(data, "errors")),
            rework=tuple(str(item) for item in _tuple(data, "rework")),
            exceptions=tuple(str(item) for item in _tuple(data, "exceptions")),
            compliance_risk=str(data.get("compliance_risk", "unknown")),
            customer_impact=str(data.get("customer_impact", "unknown")),
            schema_version=str(data.get("schema_version", SCHEMA_VERSION)),
        )


@dataclass(frozen=True)
class WorkflowModel(ModelMixin):
    workflow_id: str
    state: str
    steps: tuple[WorkflowStep, ...]
    metrics: tuple[WorkflowMetric, ...]
    schema_version: str = SCHEMA_VERSION

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkflowModel":
        return cls(
            workflow_id=str(data["workflow_id"]),
            state=str(data["state"]),
            steps=tuple(WorkflowStep.from_dict(item) for item in data.get("steps", [])),
            metrics=tuple(WorkflowMetric.from_dict(item) for item in data.get("metrics", [])),
            schema_version=str(data.get("schema_version", SCHEMA_VERSION)),
        )


@dataclass(frozen=True)
class ValidationClaim(ModelMixin):
    claim_id: str
    category_id: str
    value: bool | float | str | None
    value_kind: ValueKind
    evidence_ids: tuple[str, ...]
    explanation: str
    uncertainty: str = ""
    schema_version: str = SCHEMA_VERSION

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ValidationClaim":
        return cls(
            claim_id=str(data["claim_id"]),
            category_id=str(data["category_id"]),
            value=data.get("value"),
            value_kind=ValueKind(str(data.get("value_kind", ValueKind.UNKNOWN.value))),
            evidence_ids=tuple(str(item) for item in _tuple(data, "evidence_ids")),
            explanation=str(data.get("explanation", "")),
            uncertainty=str(data.get("uncertainty", "")),
            schema_version=str(data.get("schema_version", SCHEMA_VERSION)),
        )


@dataclass(frozen=True)
class BuyerMap(ModelMixin):
    economic_buyer: str
    operational_owner: str
    technical_approver: str
    compliance_approver: str
    end_users: tuple[str, ...]
    budget_source: str
    purchase_authority: str
    urgency: str
    consequences_of_inaction: tuple[str, ...]
    procurement_path: str
    evidence_ids: tuple[str, ...]
    schema_version: str = SCHEMA_VERSION

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BuyerMap":
        return cls(
            economic_buyer=str(data.get("economic_buyer", "unknown")),
            operational_owner=str(data.get("operational_owner", "unknown")),
            technical_approver=str(data.get("technical_approver", "unknown")),
            compliance_approver=str(data.get("compliance_approver", "unknown")),
            end_users=tuple(str(item) for item in _tuple(data, "end_users")),
            budget_source=str(data.get("budget_source", "unknown")),
            purchase_authority=str(data.get("purchase_authority", "unknown")),
            urgency=str(data.get("urgency", "unknown")),
            consequences_of_inaction=tuple(str(item) for item in _tuple(data, "consequences_of_inaction")),
            procurement_path=str(data.get("procurement_path", "unknown")),
            evidence_ids=tuple(str(item) for item in _tuple(data, "evidence_ids")),
            schema_version=str(data.get("schema_version", SCHEMA_VERSION)),
        )


@dataclass(frozen=True)
class CompetitorRecord(ModelMixin):
    competitor_id: str
    name: str
    alternative_type: str
    strengths: tuple[str, ...]
    weaknesses: tuple[str, ...]
    pricing: str
    switching_cost: str
    differentiation: str
    evidence_ids: tuple[str, ...]
    schema_version: str = SCHEMA_VERSION

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CompetitorRecord":
        return cls(
            competitor_id=str(data["competitor_id"]),
            name=str(data["name"]),
            alternative_type=str(data.get("alternative_type", "unknown")),
            strengths=tuple(str(item) for item in _tuple(data, "strengths")),
            weaknesses=tuple(str(item) for item in _tuple(data, "weaknesses")),
            pricing=str(data.get("pricing", "unknown")),
            switching_cost=str(data.get("switching_cost", "unknown")),
            differentiation=str(data.get("differentiation", "unknown")),
            evidence_ids=tuple(str(item) for item in _tuple(data, "evidence_ids")),
            schema_version=str(data.get("schema_version", SCHEMA_VERSION)),
        )


@dataclass(frozen=True)
class CustomerEconomicsModel(ModelMixin):
    annual_value: float | None
    price_assumption: float | None
    payback_months: float | None
    formulae: tuple[str, ...]
    assumptions: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    schema_version: str = SCHEMA_VERSION

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CustomerEconomicsModel":
        return cls(
            annual_value=float(data["annual_value"]) if data.get("annual_value") is not None else None,
            price_assumption=float(data["price_assumption"]) if data.get("price_assumption") is not None else None,
            payback_months=float(data["payback_months"]) if data.get("payback_months") is not None else None,
            formulae=tuple(str(item) for item in _tuple(data, "formulae")),
            assumptions=tuple(str(item) for item in _tuple(data, "assumptions")),
            evidence_ids=tuple(str(item) for item in _tuple(data, "evidence_ids")),
            schema_version=str(data.get("schema_version", SCHEMA_VERSION)),
        )


@dataclass(frozen=True)
class ProvenaUnitEconomicsModel(ModelMixin):
    development_cost: float | None
    implementation_cost_per_customer: float | None
    annual_cost_to_serve_per_customer: float | None
    annual_price: float | None
    gross_margin_percent: float | None
    break_even_customer_count: float | None
    formulae: tuple[str, ...]
    assumptions: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    schema_version: str = SCHEMA_VERSION

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProvenaUnitEconomicsModel":
        number = lambda key: float(data[key]) if data.get(key) is not None else None
        return cls(
            development_cost=number("development_cost"),
            implementation_cost_per_customer=number("implementation_cost_per_customer"),
            annual_cost_to_serve_per_customer=number("annual_cost_to_serve_per_customer"),
            annual_price=number("annual_price"),
            gross_margin_percent=number("gross_margin_percent"),
            break_even_customer_count=number("break_even_customer_count"),
            formulae=tuple(str(item) for item in _tuple(data, "formulae")),
            assumptions=tuple(str(item) for item in _tuple(data, "assumptions")),
            evidence_ids=tuple(str(item) for item in _tuple(data, "evidence_ids")),
            schema_version=str(data.get("schema_version", SCHEMA_VERSION)),
        )


@dataclass(frozen=True)
class InternalOperationalComplexityAssessment(ModelMixin):
    monthly_operating_effort_hours: float | None
    support_effort_hours_per_customer: float | None
    expected_update_cadence: str
    principal_maintenance_risks: tuple[str, ...]
    principal_service_risks: tuple[str, ...]
    operational_complexity_rating: str
    confidence: float
    key_person_dependency: bool
    evidence_ids: tuple[str, ...]
    assumptions: tuple[str, ...]
    schema_version: str = SCHEMA_VERSION

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InternalOperationalComplexityAssessment":
        confidence = float(data.get("confidence", 0.0))
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("Operational complexity confidence must be between 0 and 1")
        return cls(
            monthly_operating_effort_hours=(
                float(data["monthly_operating_effort_hours"])
                if data.get("monthly_operating_effort_hours") is not None
                else None
            ),
            support_effort_hours_per_customer=(
                float(data["support_effort_hours_per_customer"])
                if data.get("support_effort_hours_per_customer") is not None
                else None
            ),
            expected_update_cadence=str(data.get("expected_update_cadence", "unknown")),
            principal_maintenance_risks=tuple(str(item) for item in _tuple(data, "principal_maintenance_risks")),
            principal_service_risks=tuple(str(item) for item in _tuple(data, "principal_service_risks")),
            operational_complexity_rating=str(data.get("operational_complexity_rating", "unknown")).upper(),
            confidence=confidence,
            key_person_dependency=bool(data.get("key_person_dependency", False)),
            evidence_ids=tuple(str(item) for item in _tuple(data, "evidence_ids")),
            assumptions=tuple(str(item) for item in _tuple(data, "assumptions")),
            schema_version=str(data.get("schema_version", SCHEMA_VERSION)),
        )


@dataclass(frozen=True)
class Scenario(ModelMixin):
    name: ScenarioName
    category_score_adjustment: float
    assumptions: tuple[str, ...]
    prototype_cost: float | None
    expected_learning_value: float | None
    schema_version: str = SCHEMA_VERSION

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Scenario":
        return cls(
            name=ScenarioName(str(data["name"]).lower()),
            category_score_adjustment=float(data.get("category_score_adjustment", 0.0)),
            assumptions=tuple(str(item) for item in _tuple(data, "assumptions")),
            prototype_cost=float(data["prototype_cost"]) if data.get("prototype_cost") is not None else None,
            expected_learning_value=(
                float(data["expected_learning_value"])
                if data.get("expected_learning_value") is not None
                else None
            ),
            schema_version=str(data.get("schema_version", SCHEMA_VERSION)),
        )


@dataclass(frozen=True)
class CategoryAssessment(ModelMixin):
    category_id: str
    category_name: str
    sufficiency: EvidenceSufficiency
    raw_score: int
    confidence: float
    adjusted_score: float
    evidence_ids: tuple[str, ...]
    contradiction_ids: tuple[str, ...]
    unresolved_questions: tuple[str, ...]
    conclusion: str
    rule_version: str
    schema_version: str = SCHEMA_VERSION


@dataclass(frozen=True)
class GateAssessment(ModelMixin):
    gate_id: str
    gate_name: str
    status: GateStatus
    rule_version: str
    evidence_ids: tuple[str, ...]
    explanation: str
    unresolved_questions: tuple[str, ...]
    failure_reason: str
    schema_version: str = SCHEMA_VERSION


@dataclass(frozen=True)
class MissingEvidenceItem(ModelMixin):
    missing_evidence_id: str
    category_id: str
    gate_id: str
    description: str
    recommended_method: str
    target_source_or_participant: str
    success_threshold: str
    estimated_effort: str
    decision_unlocked: str
    priority: int
    schema_version: str = SCHEMA_VERSION


@dataclass(frozen=True)
class ContradictionRecord(ModelMixin):
    contradiction_id: str
    claim: str
    evidence_ids: tuple[str, ...]
    impact: str
    resolution_status: str
    schema_version: str = SCHEMA_VERSION


@dataclass(frozen=True)
class ValidationAction(ModelMixin):
    action_id: str
    rank: int
    missing_evidence_id: str
    action: str
    target: str
    success_threshold: str
    estimated_effort: str
    decision_unlocked: str
    schema_version: str = SCHEMA_VERSION


@dataclass(frozen=True)
class SensitivityResult(ModelMixin):
    assumption: str
    downside_verdict: VerdictValue
    base_verdict: VerdictValue
    upside_verdict: VerdictValue
    material: bool
    recommended_action: str
    schema_version: str = SCHEMA_VERSION


@dataclass(frozen=True)
class SVVerdict(ModelMixin):
    value: VerdictValue
    explanation: str
    rejection_reasons: tuple[str, ...]
    unresolved_blockers: tuple[str, ...]
    borderline: bool
    weighted_adjusted_score: float
    rule_version: str
    schema_version: str = SCHEMA_VERSION


@dataclass(frozen=True)
class RunManifest(ModelMixin):
    run_id: str
    execution_id: str
    svr_id: str
    engine_version: str
    methodology_version: str
    scoring_rule_version: str
    input_hash: str
    stable_business_hash: str
    rule_set_hash: str
    output_hash: str
    source_ids: tuple[str, ...]
    source_retrieval_timestamps: tuple[str, ...]
    artifact_hashes: dict[str, str]
    transformations: tuple[str, ...]
    created_at: str
    schema_version: str = SCHEMA_VERSION


@dataclass(frozen=True)
class SolutionValidationRecord(ModelMixin):
    svr_id: str
    version: str
    verified_problem: VerifiedProblemPackage
    solution_hypothesis: SolutionHypothesis
    evidence_items: tuple[EvidenceItem, ...]
    current_workflow: WorkflowModel
    proposed_workflow: WorkflowModel
    buyer_map: BuyerMap
    competitors: tuple[CompetitorRecord, ...]
    customer_economics: CustomerEconomicsModel
    provena_unit_economics: ProvenaUnitEconomicsModel
    internal_operational_complexity: InternalOperationalComplexityAssessment
    category_assessments: tuple[CategoryAssessment, ...]
    gate_assessments: tuple[GateAssessment, ...]
    scenarios: tuple[Scenario, ...]
    sensitivity_results: tuple[SensitivityResult, ...]
    missing_evidence: tuple[MissingEvidenceItem, ...]
    contradictions: tuple[ContradictionRecord, ...]
    validation_actions: tuple[ValidationAction, ...]
    verdict: SVVerdict
    stable_business_hash: str
    input_hash: str
    output_hash: str
    schema_version: str = SCHEMA_VERSION


@dataclass(frozen=True)
class SolutionValidationInput(ModelMixin):
    svr_id: str
    version: str
    verified_problem: VerifiedProblemPackage
    solution_hypothesis: SolutionHypothesis
    evidence_items: tuple[EvidenceItem, ...]
    current_workflow: WorkflowModel
    proposed_workflow: WorkflowModel
    buyer_map: BuyerMap
    competitors: tuple[CompetitorRecord, ...]
    customer_economics: CustomerEconomicsModel
    provena_unit_economics: ProvenaUnitEconomicsModel
    internal_operational_complexity: InternalOperationalComplexityAssessment
    validation_claims: tuple[ValidationClaim, ...]
    scenarios: tuple[Scenario, ...]
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SolutionValidationInput":
        required = (
            "svr_id",
            "verified_problem",
            "solution_hypothesis",
            "current_workflow",
            "proposed_workflow",
            "buyer_map",
            "customer_economics",
            "provena_unit_economics",
            "internal_operational_complexity",
        )
        missing = [key for key in required if data.get(key) in (None, "")]
        if missing:
            raise ValueError(f"Solution validation input missing: {', '.join(missing)}")
        scenarios = tuple(Scenario.from_dict(item) for item in data.get("scenarios", []))
        names = {scenario.name for scenario in scenarios}
        expected = {ScenarioName.DOWNSIDE, ScenarioName.BASE, ScenarioName.UPSIDE}
        if len(scenarios) != 3 or names != expected:
            raise ValueError("Exactly downside, base and upside scenarios are required")
        return cls(
            svr_id=str(data["svr_id"]),
            version=str(data.get("version", "1.0")),
            verified_problem=VerifiedProblemPackage.from_dict(data["verified_problem"]),
            solution_hypothesis=SolutionHypothesis.from_dict(data["solution_hypothesis"]),
            evidence_items=tuple(EvidenceItem.from_dict(item) for item in data.get("evidence_items", [])),
            current_workflow=WorkflowModel.from_dict(data["current_workflow"]),
            proposed_workflow=WorkflowModel.from_dict(data["proposed_workflow"]),
            buyer_map=BuyerMap.from_dict(data["buyer_map"]),
            competitors=tuple(CompetitorRecord.from_dict(item) for item in data.get("competitors", [])),
            customer_economics=CustomerEconomicsModel.from_dict(data["customer_economics"]),
            provena_unit_economics=ProvenaUnitEconomicsModel.from_dict(data["provena_unit_economics"]),
            internal_operational_complexity=InternalOperationalComplexityAssessment.from_dict(
                data["internal_operational_complexity"]
            ),
            validation_claims=tuple(ValidationClaim.from_dict(item) for item in data.get("validation_claims", [])),
            scenarios=scenarios,
            metadata=dict(data.get("metadata") or {}),
            schema_version=str(data.get("schema_version", SCHEMA_VERSION)),
        )
