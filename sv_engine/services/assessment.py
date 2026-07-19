"""Transparent category scoring and mandatory gate evaluation."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from sv_engine.domain.enums import (
    EvidenceClass,
    EvidenceSufficiency,
    GateStatus,
    ReviewState,
    ValueKind,
)
from sv_engine.domain.models import (
    CategoryAssessment,
    ContradictionRecord,
    EvidenceItem,
    GateAssessment,
    MissingEvidenceItem,
    SolutionValidationInput,
    ValidationClaim,
)
from sv_engine.rules.loader import RuleSet
from sv_engine.services.calculations import (
    compare_workflows,
    customer_economics_check,
    provena_economics_check,
)


def _evidence_index(data: SolutionValidationInput) -> dict[str, EvidenceItem]:
    index: dict[str, EvidenceItem] = {}
    for item in data.evidence_items:
        if item.evidence_id in index:
            raise ValueError(f"Duplicate evidence ID: {item.evidence_id}")
        index[item.evidence_id] = item
    return index


def _approved_evidence(
    evidence_ids: tuple[str, ...],
    evidence: dict[str, EvidenceItem],
    *,
    category_id: str = "",
    gate_id: str = "",
    include_contradictions: bool = False,
) -> tuple[EvidenceItem, ...]:
    return tuple(
        evidence[item_id]
        for item_id in evidence_ids
        if item_id in evidence
        and evidence[item_id].review_state is ReviewState.APPROVED
        and (include_contradictions or not evidence[item_id].contradiction_flag)
        and (not category_id or category_id in evidence[item_id].linked_categories)
        and (not gate_id or gate_id in evidence[item_id].linked_gates)
    )


def claim_support_state(
    claim: ValidationClaim | None,
    evidence: dict[str, EvidenceItem],
    *,
    gate_id: str = "",
) -> tuple[str, tuple[str, ...]]:
    if claim is None or claim.value is None or claim.value_kind is ValueKind.UNKNOWN:
        return "UNKNOWN", ()
    linked = _approved_evidence(
        claim.evidence_ids,
        evidence,
        category_id=claim.category_id,
        gate_id=gate_id,
        include_contradictions=claim.value_kind is ValueKind.CONTRADICTION or claim.value is False,
    )
    if claim.value_kind is ValueKind.CONTRADICTION or claim.value is False:
        if linked:
            return "NEGATIVE", tuple(item.evidence_id for item in linked)
        return "UNSUPPORTED_NEGATIVE", ()
    if bool(claim.value) and linked:
        return "SUPPORTED", tuple(item.evidence_id for item in linked)
    return "UNSUPPORTED_POSITIVE", ()


def build_contradictions(data: SolutionValidationInput) -> tuple[ContradictionRecord, ...]:
    records: list[ContradictionRecord] = []
    for item in sorted(data.evidence_items, key=lambda evidence: evidence.evidence_id):
        if item.contradiction_flag:
            records.append(
                ContradictionRecord(
                    contradiction_id=f"CR-{len(records) + 1:04d}",
                    claim=item.relevant_claim,
                    evidence_ids=(item.evidence_id,),
                    impact="Negative evidence lowers category confidence and must be resolved before BUILD PROTOTYPE.",
                    resolution_status="OPEN",
                )
            )
    for claim in sorted(data.validation_claims, key=lambda item: item.claim_id):
        if claim.value_kind is ValueKind.CONTRADICTION:
            records.append(
                ContradictionRecord(
                    contradiction_id=f"CR-{len(records) + 1:04d}",
                    claim=claim.explanation or claim.claim_id,
                    evidence_ids=claim.evidence_ids,
                    impact="A structured validation claim is contradicted.",
                    resolution_status="OPEN",
                )
            )
    return tuple(records)


def assess_categories(
    data: SolutionValidationInput,
    rules: RuleSet,
    contradictions: tuple[ContradictionRecord, ...],
) -> tuple[CategoryAssessment, ...]:
    evidence = _evidence_index(data)
    claims_by_category: dict[str, list[ValidationClaim]] = defaultdict(list)
    for claim in data.validation_claims:
        claims_by_category[claim.category_id].append(claim)
    contradiction_evidence_ids = {
        evidence_id for item in contradictions for evidence_id in item.evidence_ids
    }
    direct_classes = {
        EvidenceClass(value)
        for value in rules.data["evidence_sufficiency"]["direct_evidence_classes"]
    }
    estimate_cap = float(rules.data["evidence_sufficiency"]["internal_estimate_confidence_cap"])
    assessments: list[CategoryAssessment] = []
    for category in rules.data["categories"]:
        category_id = str(category["id"])
        category_claims = claims_by_category.get(category_id, [])
        category_evidence = tuple(
            item
            for item in data.evidence_items
            if category_id in item.linked_categories and item.review_state is ReviewState.APPROVED
        )
        linked = tuple(item for item in category_evidence if not item.contradiction_flag)
        supported_claims = [
            claim
            for claim in category_claims
            if claim_support_state(claim, evidence)[0] == "SUPPORTED"
        ]
        negative_claims = [
            claim
            for claim in category_claims
            if claim_support_state(claim, evidence)[0] == "NEGATIVE"
        ]
        classes = {item.evidence_class for item in linked}
        raw_score = 0
        if linked and supported_claims:
            raw_score = 1
            if len(linked) >= 2:
                raw_score += 1
            if len(classes) >= 2:
                raw_score += 1
            if classes.intersection(direct_classes):
                raw_score += 1
            if len(linked) >= 4 and len(supported_claims) >= 2:
                raw_score += 1
        raw_score = max(0, raw_score - min(2, len(negative_claims)))
        effective_confidence: list[float] = []
        for item in linked:
            value = item.confidence_contribution
            if item.evidence_class is EvidenceClass.INTERNAL_ESTIMATE:
                value = min(value, estimate_cap)
            effective_confidence.append(value)
        confidence = round(sum(effective_confidence) / len(effective_confidence), 4) if effective_confidence else 0.0
        category_contradictions = tuple(
            item.contradiction_id
            for item in contradictions
            if set(item.evidence_ids).intersection({entry.evidence_id for entry in category_evidence})
        )
        if category_contradictions:
            sufficiency = EvidenceSufficiency.CONTRADICTED
        elif raw_score >= 4 and confidence >= 0.5:
            sufficiency = EvidenceSufficiency.SUPPORTED
        elif raw_score >= 2:
            sufficiency = EvidenceSufficiency.PARTIALLY_SUPPORTED
        else:
            sufficiency = EvidenceSufficiency.UNSUPPORTED
        unresolved = tuple(
            f"Obtain traceable evidence for {claim_id}."
            for claim_id in category.get("required_claims", [])
            if claim_support_state(
                next((item for item in category_claims if item.claim_id == claim_id), None), evidence
            )[0]
            not in {"SUPPORTED", "NEGATIVE"}
        )
        if raw_score == 0:
            conclusion = "No positive score awarded because traceable approved evidence is absent."
        elif negative_claims or category_contradictions:
            conclusion = "Evidence exists, but explicit negative or contradictory evidence reduces the score."
        else:
            conclusion = "Score derives only from approved linked evidence and supported structured claims."
        assessments.append(
            CategoryAssessment(
                category_id=category_id,
                category_name=str(category["name"]),
                sufficiency=sufficiency,
                raw_score=raw_score,
                confidence=confidence,
                adjusted_score=round(raw_score * confidence, 4),
                evidence_ids=tuple(sorted(item.evidence_id for item in linked)),
                contradiction_ids=category_contradictions,
                unresolved_questions=unresolved,
                conclusion=conclusion,
                rule_version=rules.version,
            )
        )
    return tuple(assessments)


def assess_gates(data: SolutionValidationInput, rules: RuleSet) -> tuple[GateAssessment, ...]:
    evidence = _evidence_index(data)
    claims = {claim.claim_id: claim for claim in data.validation_claims}
    results: list[GateAssessment] = []
    for gate in rules.data["gates"]:
        states: list[str] = []
        evidence_ids: set[str] = set()
        unresolved: list[str] = []
        failures: list[str] = []
        for claim_id in gate["required_true_claims"]:
            state, linked_ids = claim_support_state(claims.get(claim_id), evidence, gate_id=str(gate["id"]))
            states.append(state)
            evidence_ids.update(linked_ids)
            if state in {"UNKNOWN", "UNSUPPORTED_POSITIVE", "UNSUPPORTED_NEGATIVE"}:
                unresolved.append(f"Traceable support is required for {claim_id}.")
            elif state == "NEGATIVE":
                failures.append(f"Required condition {claim_id} is explicitly false or contradicted.")

        gate_id = str(gate["id"])
        if gate_id == "G1_VERIFIED_PROBLEM_LINKAGE":
            verdict = data.verified_problem.golden_study_verdict.upper()
            if verdict != "BUILD CANDIDATE":
                failures.append("Golden Study verdict does not establish an eligible verified problem.")
            if data.verified_problem.independent_source_family_count < 2:
                unresolved.append("At least two independent source families are required before solution validation.")
            if data.verified_problem.confidence < 0.5:
                unresolved.append("Verified-problem confidence is below the methodology threshold.")
        if gate_id == "G2_BASELINE_SUFFICIENCY":
            measurable = any(
                metric.value_kind in {ValueKind.OBSERVED, ValueKind.CALCULATED, ValueKind.BOUNDED_ESTIMATE}
                and metric.value is not None
                for metric in data.current_workflow.metrics
            )
            if not data.current_workflow.steps or not measurable:
                unresolved.append("Current workflow steps and at least one measured or bounded baseline metric are required.")
        if gate_id == "G6_INTERNAL_OPERABILITY":
            limits = rules.data["operability_limits"]
            assessment = data.internal_operational_complexity
            if assessment.operational_complexity_rating in limits["disallowed_ratings"]:
                failures.append("Internal operational complexity rating is unacceptable.")
            if (
                assessment.monthly_operating_effort_hours is not None
                and assessment.monthly_operating_effort_hours
                > float(limits["maximum_monthly_operating_effort_hours"])
            ):
                failures.append("Estimated monthly operating effort exceeds the configured limit.")
            if (
                assessment.support_effort_hours_per_customer is not None
                and assessment.support_effort_hours_per_customer
                > float(limits["maximum_support_effort_hours_per_customer"])
            ):
                failures.append("Support effort per customer exceeds the configured limit.")
            if limits["key_person_dependency_blocks_build"] and assessment.key_person_dependency:
                failures.append("Material key-person dependency makes internal operation unacceptable.")
            minimum_confidence = float(limits.get("minimum_internal_operability_confidence", 0.5))
            if assessment.confidence < minimum_confidence:
                unresolved.append(
                    f"Internal operability confidence {assessment.confidence:.2f} is below {minimum_confidence:.2f}."
                )
            if assessment.monthly_operating_effort_hours is not None and assessment.monthly_operating_effort_hours < 0:
                failures.append("Monthly operating effort cannot be negative.")
            if assessment.support_effort_hours_per_customer is not None and assessment.support_effort_hours_per_customer < 0:
                failures.append("Support effort per customer cannot be negative.")
            provena_check = provena_economics_check(data.provena_unit_economics)
            failures.extend(provena_check.failures)
            unresolved.extend(provena_check.unresolved)
        if gate_id == "G4_BUYER_CREDIBILITY":
            buyer_fields = (
                data.buyer_map.economic_buyer,
                data.buyer_map.budget_source,
                data.buyer_map.purchase_authority,
            )
            if any(not value or value.lower() == "unknown" for value in buyer_fields):
                unresolved.append("Buyer identity, budget source and purchase authority must all be explicit.")
            linked_buyer = [evidence[item_id] for item_id in evidence_ids if item_id in evidence]
            if not any(item.evidence_class is EvidenceClass.DIRECT_BUYER for item in linked_buyer):
                unresolved.append("Buyer credibility requires approved direct-buyer evidence.")
        if gate_id == "G5_VALUE_PLAUSIBILITY":
            workflow_check = compare_workflows(data.current_workflow, data.proposed_workflow)
            if workflow_check.regressions:
                failures.append(
                    "Proposed workflow regresses explicit measures: " + "; ".join(workflow_check.regressions)
                )
            elif not workflow_check.measurable or not workflow_check.improvements:
                unresolved.append("No measurable workflow improvement has been demonstrated.")
            customer_check = customer_economics_check(data.customer_economics)
            failures.extend(customer_check.failures)
            unresolved.extend(customer_check.unresolved)
        if gate_id == "G7_COMPETITIVE_VIABILITY" and not data.competitors:
            unresolved.append("At least one current alternative must be assessed.")
        if gate_id == "G8_ETHICAL_LEGAL_REGULATORY_ACCEPTABILITY":
            if "ethical_legal_regulatory_acceptable" not in claims:
                unresolved.append("Human-reviewed legal and regulatory acceptability evidence is required.")
            else:
                legal_claim = claims["ethical_legal_regulatory_acceptable"]
                linked_legal = _approved_evidence(
                    legal_claim.evidence_ids,
                    evidence,
                    category_id=legal_claim.category_id,
                    gate_id=gate_id,
                )
                if not any(item.evidence_class is EvidenceClass.AUTHORITATIVE_EXTERNAL for item in linked_legal):
                    unresolved.append("Legal acceptability requires approved authoritative external evidence.")

        if failures:
            status = GateStatus.FAIL
            explanation = "Mandatory gate failed; aggregate scoring cannot override this result."
        elif unresolved:
            status = GateStatus.UNRESOLVED
            explanation = "Mandatory gate remains unresolved because required evidence is incomplete."
        else:
            status = GateStatus.PASS
            explanation = "Every configured condition is supported by approved traceable evidence."
        results.append(
            GateAssessment(
                gate_id=gate_id,
                gate_name=str(gate["name"]),
                status=status,
                rule_version=rules.version,
                evidence_ids=tuple(sorted(evidence_ids)),
                explanation=explanation,
                unresolved_questions=tuple(sorted(set(unresolved))),
                failure_reason=" ".join(failures),
            )
        )
    return tuple(results)


def build_missing_evidence(
    data: SolutionValidationInput,
    rules: RuleSet,
    gates: tuple[GateAssessment, ...],
) -> tuple[MissingEvidenceItem, ...]:
    evidence = _evidence_index(data)
    claims = {claim.claim_id: claim for claim in data.validation_claims}
    gate_by_claim: dict[str, str] = {}
    for gate in rules.data["gates"]:
        for claim_id in gate["required_true_claims"]:
            gate_by_claim.setdefault(claim_id, str(gate["id"]))
    missing: list[MissingEvidenceItem] = []
    for category in rules.data["categories"]:
        for claim_id in category.get("required_claims", []):
            state, _ = claim_support_state(claims.get(claim_id), evidence)
            if state in {"SUPPORTED", "NEGATIVE"}:
                continue
            missing.append(
                MissingEvidenceItem(
                    missing_evidence_id=f"ME-{len(missing) + 1:04d}",
                    category_id=str(category["id"]),
                    gate_id=gate_by_claim.get(claim_id, ""),
                    description=f"Approved traceable evidence for {claim_id} is missing.",
                    recommended_method="Collect direct observed evidence and record its provenance.",
                    target_source_or_participant="Relevant buyer, user, operator, system record or authoritative source",
                    success_threshold="At least one approved evidence item directly supports the claim.",
                    estimated_effort="To be estimated by the validation owner",
                    decision_unlocked="Resolve the linked category or mandatory gate.",
                    priority=1 if gate_by_claim.get(claim_id) else 2,
                )
            )
    covered_claims = {
        claim_id
        for category in rules.data["categories"]
        for claim_id in category.get("required_claims", [])
    }
    for gate in rules.data["gates"]:
        for claim_id in gate["required_true_claims"]:
            if claim_id in covered_claims:
                continue
            state, _ = claim_support_state(claims.get(claim_id), evidence)
            if state in {"SUPPORTED", "NEGATIVE"}:
                continue
            missing.append(
                MissingEvidenceItem(
                    missing_evidence_id=f"ME-{len(missing) + 1:04d}",
                    category_id="GATE",
                    gate_id=str(gate["id"]),
                    description=f"Approved traceable evidence for {claim_id} is missing.",
                    recommended_method="Obtain human-reviewed authoritative or direct evidence.",
                    target_source_or_participant="Appropriate legal, regulatory, buyer or operational reviewer",
                    success_threshold="The gate condition is directly supported by approved evidence.",
                    estimated_effort="To be estimated by the validation owner",
                    decision_unlocked="Resolve the mandatory gate.",
                    priority=1,
                )
            )
            covered_claims.add(claim_id)
    for global_claim in rules.data.get("global_build_claims", []):
        state, _ = claim_support_state(claims.get(global_claim), evidence)
        if state in {"SUPPORTED", "NEGATIVE"}:
            continue
        missing.append(
            MissingEvidenceItem(
                missing_evidence_id=f"ME-{len(missing) + 1:04d}",
                category_id="GLOBAL",
                gate_id="",
                description=f"Approved traceable evidence for {global_claim} is missing.",
                recommended_method="Define bounded prototype cost and expected learning value.",
                target_source_or_participant="Engineering and validation owner",
                success_threshold="Prototype cost is supported and proportionate to learning value.",
                estimated_effort="Small internal estimation exercise",
                decision_unlocked="Determine whether BUILD PROTOTYPE is proportionate.",
                priority=1,
            )
        )
    return tuple(sorted(missing, key=lambda item: (item.priority, item.missing_evidence_id)))
