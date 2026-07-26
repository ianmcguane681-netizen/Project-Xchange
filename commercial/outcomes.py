"""What actually happened after launch.

The pipeline currently stops at "tested and audited before going public". So the
system reasons carefully right up to the moment it would learn the most, and then
stops measuring. Whether the thing delivered better-for-cheaper in the real world
never returns to the evidence base.

An outcome record closes that loop. It pairs a claim that was published with what
was subsequently observed, and it is deliberately capable of embarrassing the
claim: a shortfall marks the claim as contradicted rather than quietly ageing.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

from rbe_runtime.canonical import canonical_hash, deterministic_id

# sv_engine.domain.enums.EvidenceClass.PROTOTYPE - evidence you create by shipping.
PROTOTYPE_EVIDENCE_CLASS = "E7_PROTOTYPE"


class OutcomeStatus(StrEnum):
    DELIVERED = "DELIVERED"
    SHORTFALL = "SHORTFALL"
    EXCEEDED = "EXCEEDED"
    UNMEASURED = "UNMEASURED"
    INCONCLUSIVE = "INCONCLUSIVE"


class Direction(StrEnum):
    """Whether a good result means the measure went up or down."""

    HIGHER_IS_BETTER = "HIGHER_IS_BETTER"
    LOWER_IS_BETTER = "LOWER_IS_BETTER"


@dataclass(frozen=True, slots=True)
class OutcomeRecord:
    outcome_id: str
    claim_id: str
    measure: str
    direction: str
    predicted_value: float | None
    observed_value: float | None
    unit: str
    measurement_method: str
    period_start: str
    period_end: str
    sample_size: int
    recorded_by: str
    status: str
    reasons: tuple[str, ...]
    content_hash: str
    evidence_class: str = PROTOTYPE_EVIDENCE_CLASS

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["reasons"] = list(self.reasons)
        return value


# Below this, a difference is not distinguishable from noise for our purposes.
DEFAULT_TOLERANCE = 0.05
MINIMUM_SAMPLE = 10


def record_outcome(
    *,
    claim_id: str,
    measure: str,
    direction: Direction,
    predicted_value: float | None,
    observed_value: float | None,
    unit: str,
    measurement_method: str,
    period_start: str,
    period_end: str,
    sample_size: int,
    recorded_by: str,
    tolerance: float = DEFAULT_TOLERANCE,
    minimum_sample: int = MINIMUM_SAMPLE,
) -> OutcomeRecord:
    """Compare what was promised with what was observed.

    An unmeasured or under-powered result is reported as such rather than being
    rounded toward the claim. The point of this record is to be able to say the
    claim did not hold.
    """

    reasons: list[str] = []
    if not measurement_method.strip():
        raise ValueError("An outcome requires a stated measurement method")

    if observed_value is None:
        status = OutcomeStatus.UNMEASURED
        reasons.append("No observed value was recorded.")
    elif predicted_value is None:
        status = OutcomeStatus.INCONCLUSIVE
        reasons.append("No predicted value was registered, so the claim cannot be tested.")
    elif sample_size < minimum_sample:
        status = OutcomeStatus.INCONCLUSIVE
        reasons.append(
            f"Sample of {sample_size} is below the minimum of {minimum_sample}; "
            "the difference is not distinguishable from noise."
        )
    else:
        status, reason = _compare(predicted_value, observed_value, direction, tolerance)
        reasons.append(reason)

    payload = {
        "claim_id": claim_id,
        "measure": measure,
        "predicted": predicted_value,
        "observed": observed_value,
        "period": [period_start, period_end],
        "method": measurement_method,
    }
    content_hash = canonical_hash(payload)
    return OutcomeRecord(
        outcome_id=deterministic_id("OUT", claim_id, measure, period_end, content_hash),
        claim_id=claim_id,
        measure=measure,
        direction=str(direction),
        predicted_value=predicted_value,
        observed_value=observed_value,
        unit=unit,
        measurement_method=measurement_method,
        period_start=period_start,
        period_end=period_end,
        sample_size=sample_size,
        recorded_by=recorded_by,
        status=str(status),
        reasons=tuple(reasons),
        content_hash=content_hash,
    )


def _compare(
    predicted: float, observed: float, direction: Direction, tolerance: float
) -> tuple[OutcomeStatus, str]:
    if predicted == 0:
        relative = 0.0 if observed == 0 else 1.0
    else:
        relative = (observed - predicted) / abs(predicted)
    if direction is Direction.LOWER_IS_BETTER:
        relative = -relative
    if abs(relative) <= tolerance:
        return OutcomeStatus.DELIVERED, (
            f"Observed {observed} against predicted {predicted}, within {tolerance:.0%} tolerance."
        )
    if relative > 0:
        return OutcomeStatus.EXCEEDED, (
            f"Observed {observed} against predicted {predicted}, better by {abs(relative):.0%}."
        )
    return OutcomeStatus.SHORTFALL, (
        f"Observed {observed} against predicted {predicted}, short by {abs(relative):.0%}."
    )


def claims_contradicted_by(outcomes: list[OutcomeRecord]) -> list[str]:
    """Claims a measured shortfall has falsified, and which must stop being made."""

    return sorted({item.claim_id for item in outcomes if item.status == OutcomeStatus.SHORTFALL})


def to_sv_evidence_item(record: OutcomeRecord) -> dict[str, Any]:
    """Feed the observed result back as evidence for the next decision."""

    return {
        "evidence_id": record.outcome_id,
        "title": f"Observed {record.measure} for {record.period_start} to {record.period_end}",
        "description": "; ".join(record.reasons),
        "relevant_claim": record.claim_id,
        "evidence_class": PROTOTYPE_EVIDENCE_CLASS,
        "source_type": "post_launch_measurement",
        "source_organisation": "Provena",
        "source_locator": record.measurement_method,
        "content_hash": record.content_hash,
        "date_observed_or_published": record.period_end,
        "retrieval_timestamp": record.period_end,
        "provenance": f"Measured by {record.recorded_by} over n={record.sample_size}",
        "linked_categories": ["C3_WORKFLOW_IMPROVEMENT", "C7_CUSTOMER_ECONOMICS"],
        "linked_gates": ["G5_VALUE_PLAUSIBILITY"],
        "review_state": "PENDING_REVIEW",
        "reviewed_by": "",
        "reviewed_at": "",
        "confidence_contribution": 0.0,
        "contradiction_flag": record.status == OutcomeStatus.SHORTFALL,
        "assumptions": [],
        "limitations": [
            "A single measurement period is not a trend.",
            "Observed change is not proof of causation.",
        ],
    }
