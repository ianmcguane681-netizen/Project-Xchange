"""When to stop researching a market.

Every study can conclude "continue research", and nothing ever says "we have spent
enough on this one". A system that can always ask for more evidence will, because
asking for more is always the defensible answer in the moment. That is how a study
consumes a year without ever being wrong.

These rules are deterministic, in the same spirit as the proof gates: given the
state of a study, they return one decision and the reason for it. They do not
decide whether the market is good. They decide whether to keep paying to find out.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class StopDecision(StrEnum):
    CONTINUE = "CONTINUE"
    STOP_OBJECTIVE_MET = "STOP_OBJECTIVE_MET"
    STOP_BUDGET_EXHAUSTED = "STOP_BUDGET_EXHAUSTED"
    STOP_NO_PROGRESS = "STOP_NO_PROGRESS"
    STOP_BLOCKED_EXTERNALLY = "STOP_BLOCKED_EXTERNALLY"


@dataclass(frozen=True, slots=True)
class StudyBudget:
    """What the organisation is willing to spend before deciding."""

    max_runs: int
    max_days: int
    # Runs allowed to pass with no new independent source family and no new
    # qualified evidence before the study is treated as stalled.
    max_runs_without_progress: int = 3

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class StudyState:
    runs_completed: int
    days_elapsed: int
    runs_since_progress: int
    independent_source_families: int
    qualified_evidence_count: int
    unresolved_external_blockers: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["unresolved_external_blockers"] = list(self.unresolved_external_blockers)
        return value


@dataclass(frozen=True, slots=True)
class StopAssessment:
    decision: str
    reasons: tuple[str, ...]
    recommended_action: str
    budget: dict[str, Any]
    state: dict[str, Any]

    @property
    def should_stop(self) -> bool:
        return self.decision != StopDecision.CONTINUE

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["reasons"] = list(self.reasons)
        return value


# The objective of a study is to reach a decidable position, not to be right.
DEFAULT_MINIMUM_SOURCE_FAMILIES = 2
DEFAULT_MINIMUM_QUALIFIED_EVIDENCE = 3


def evaluate_stop(
    budget: StudyBudget,
    state: StudyState,
    *,
    minimum_source_families: int = DEFAULT_MINIMUM_SOURCE_FAMILIES,
    minimum_qualified_evidence: int = DEFAULT_MINIMUM_QUALIFIED_EVIDENCE,
) -> StopAssessment:
    """Decide whether to keep researching.

    Order matters. The objective being met is checked first, so a study that has
    achieved what it set out to do is never reported as having run out of budget.
    An external blocker is checked before the stall rule, because a study waiting
    on something outside its control has not failed - it is waiting.
    """

    objective_met = (
        state.independent_source_families >= minimum_source_families
        and state.qualified_evidence_count >= minimum_qualified_evidence
    )
    if objective_met:
        return StopAssessment(
            decision=StopDecision.STOP_OBJECTIVE_MET,
            reasons=(
                f"{state.independent_source_families} independent source families "
                f"(minimum {minimum_source_families}).",
                f"{state.qualified_evidence_count} qualified evidence records "
                f"(minimum {minimum_qualified_evidence}).",
            ),
            recommended_action="Move to decision; further collection does not change decidability.",
            budget=budget.to_dict(),
            state=state.to_dict(),
        )

    if state.unresolved_external_blockers:
        return StopAssessment(
            decision=StopDecision.STOP_BLOCKED_EXTERNALLY,
            reasons=tuple(
                f"Unresolved external blocker: {item}"
                for item in sorted(state.unresolved_external_blockers)
            ),
            recommended_action="Pause and escalate the blocker; do not spend further runs against it.",
            budget=budget.to_dict(),
            state=state.to_dict(),
        )

    exhausted: list[str] = []
    if state.runs_completed >= budget.max_runs:
        exhausted.append(f"Run budget exhausted: {state.runs_completed}/{budget.max_runs}.")
    if state.days_elapsed >= budget.max_days:
        exhausted.append(f"Time budget exhausted: {state.days_elapsed}/{budget.max_days} days.")
    if exhausted:
        return StopAssessment(
            decision=StopDecision.STOP_BUDGET_EXHAUSTED,
            reasons=tuple(exhausted),
            recommended_action="Close the study at its current verdict, or re-authorise a new budget explicitly.",
            budget=budget.to_dict(),
            state=state.to_dict(),
        )

    if state.runs_since_progress >= budget.max_runs_without_progress:
        return StopAssessment(
            decision=StopDecision.STOP_NO_PROGRESS,
            reasons=(
                f"{state.runs_since_progress} consecutive runs added no independent source "
                f"family and no qualified evidence (limit {budget.max_runs_without_progress}).",
            ),
            recommended_action="Change the source strategy or close the study; repeating the run will not help.",
            budget=budget.to_dict(),
            state=state.to_dict(),
        )

    remaining_families = max(0, minimum_source_families - state.independent_source_families)
    remaining_evidence = max(0, minimum_qualified_evidence - state.qualified_evidence_count)
    return StopAssessment(
        decision=StopDecision.CONTINUE,
        reasons=(
            f"{remaining_families} further independent source family(ies) required.",
            f"{remaining_evidence} further qualified evidence record(s) required.",
            f"{max(0, budget.max_runs - state.runs_completed)} run(s) remaining in budget.",
        ),
        recommended_action="Continue collection against the identified gaps.",
        budget=budget.to_dict(),
        state=state.to_dict(),
    )
