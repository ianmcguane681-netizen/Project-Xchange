"""The commercial half of the pipeline.

Each of these covers a place where a carefully evidenced system normally starts
overstating itself: agent output drifting into evidence, one enthusiastic
conversation standing in for a market, a study researching forever, marketing
claims outrunning their support, and nobody checking afterwards whether the claim
held.
"""
from __future__ import annotations

import pytest

from commercial.agent_guard import (
    AgentGovernanceError,
    AgentOutputKind,
    assert_not_evidence,
    carries_agent_provenance,
    record_agent_output,
    require_human_review,
)
from commercial.buyer import (
    BuyerEvidenceError,
    ContactMethod,
    qualifies_for_buyer_gate,
    record_buyer_evidence,
    to_sv_evidence_item,
)
from commercial.claims import (
    ClaimAudience,
    ClaimStatus,
    assess_claim,
    make_claim,
    publishable_claims,
)
from commercial.outcomes import (
    Direction,
    OutcomeStatus,
    claims_contradicted_by,
    record_outcome,
)
from commercial.outcomes import to_sv_evidence_item as outcome_evidence_item
from commercial.stop_rules import (
    StopDecision,
    StudyBudget,
    StudyState,
    evaluate_stop,
)

# --------------------------------------------------------------------------
# Agent governance
# --------------------------------------------------------------------------


def agent_output(**overrides):
    payload = dict(
        agent_id="complaint-analyst",
        model="some-model",
        instruction_version="AGT-001",
        kind=AgentOutputKind.ANALYSIS,
        summary="Recurring reinvestigation failures across three furnishers.",
        body={"mechanism": "reinvestigation_failure"},
        input_evidence_ids=("EV-1", "EV-2"),
        produced_at="2026-07-26T00:00:00Z",
    )
    payload.update(overrides)
    return record_agent_output(**payload)


def test_agent_output_can_never_be_evidence():
    output = agent_output()

    assert output.is_evidence is False
    assert output.to_dict()["is_evidence"] is False
    # Not settable, even deliberately: it is not an init field.
    with pytest.raises((AttributeError, TypeError)):
        output.is_evidence = True  # type: ignore[misc]


def test_agent_output_is_refused_in_an_evidence_position():
    with pytest.raises(AgentGovernanceError) as exc:
        assert_not_evidence(agent_output(), position="finding support")

    assert exc.value.code == "AGENT_OUTPUT_IS_NOT_EVIDENCE"


def test_agent_provenance_is_detected_through_a_dict_wrapper():
    """Serialising an agent's output must not launder it into evidence."""
    assert carries_agent_provenance(agent_output().to_dict()) is True
    assert carries_agent_provenance({"method_used": "agent:x"}) is True
    assert carries_agent_provenance({"evidence_id": "EV-1", "review_state": "APPROVED"}) is False


def test_agent_output_requires_full_provenance():
    with pytest.raises(AgentGovernanceError) as exc:
        agent_output(model="")

    assert exc.value.code == "AGENT_PROVENANCE_INCOMPLETE"


def test_a_proposal_needs_a_named_human_before_it_can_be_acted_on():
    unreviewed = agent_output(kind=AgentOutputKind.PROPOSAL)
    with pytest.raises(AgentGovernanceError) as exc:
        require_human_review(unreviewed)
    assert exc.value.code == "AGENT_PROPOSAL_UNREVIEWED"

    reviewed = agent_output(
        kind=AgentOutputKind.PROPOSAL,
        human_reviewed_by="a-person",
        human_reviewed_at="2026-07-26T01:00:00Z",
    )
    assert require_human_review(reviewed) is reviewed


def test_identical_agent_output_gets_a_stable_id():
    assert agent_output().output_id == agent_output().output_id


# --------------------------------------------------------------------------
# Buyer evidence
# --------------------------------------------------------------------------


def buyer(**overrides):
    payload = dict(
        organisation="A Lender",
        respondent_role="Head of Disputes",
        contact_method=ContactMethod.INTERVIEW,
        occurred_at="2026-07-20T10:00:00Z",
        recorded_by="a-researcher",
        consent_reference="CONSENT-001",
        holds_budget_authority=True,
        stated_problem="Reinvestigations take too long and cannot be evidenced.",
        stated_willingness="Would pay to cut handling time.",
        verbatim_quotes=("We cannot show a regulator what we checked.",),
    )
    payload.update(overrides)
    return record_buyer_evidence(**payload)


def test_buyer_evidence_requires_consent():
    with pytest.raises(BuyerEvidenceError) as exc:
        buyer(consent_reference="")

    assert exc.value.code == "BUYER_CONSENT_MISSING"


def test_buyer_evidence_requires_an_identifiable_respondent():
    with pytest.raises(BuyerEvidenceError) as exc:
        buyer(respondent_role="")

    assert exc.value.code == "BUYER_EVIDENCE_INCOMPLETE"
    assert "respondent_role" in exc.value.details["missing"]


def test_one_enthusiastic_conversation_does_not_qualify():
    ok, reasons = qualifies_for_buyer_gate([buyer()])

    assert ok is False
    assert any("organisation" in reason for reason in reasons)


def test_two_organisations_with_budget_authority_and_verbatim_qualify():
    ok, reasons = qualifies_for_buyer_gate(
        [buyer(), buyer(organisation="Another Lender", holds_budget_authority=False)]
    )

    assert ok is True
    assert reasons == []


def test_budget_authority_is_required_however_many_conversations():
    ok, reasons = qualifies_for_buyer_gate(
        [
            buyer(holds_budget_authority=False),
            buyer(organisation="Another Lender", holds_budget_authority=False),
        ]
    )

    assert ok is False
    assert any("budget authority" in reason for reason in reasons)


def test_buyer_evidence_is_emitted_unreviewed_for_the_buyer_gate():
    item = to_sv_evidence_item(buyer())

    assert item["evidence_class"] == "E2_DIRECT_BUYER"
    assert item["linked_gates"] == ["G4_BUYER_CREDIBILITY"]
    assert item["review_state"] == "PENDING_REVIEW"


# --------------------------------------------------------------------------
# Stop rules
# --------------------------------------------------------------------------


BUDGET = StudyBudget(max_runs=10, max_days=60, max_runs_without_progress=3)


def state(**overrides):
    payload = dict(
        runs_completed=2,
        days_elapsed=10,
        runs_since_progress=0,
        independent_source_families=1,
        qualified_evidence_count=1,
    )
    payload.update(overrides)
    return StudyState(**payload)


def test_objective_met_stops_the_study():
    result = evaluate_stop(BUDGET, state(independent_source_families=2, qualified_evidence_count=3))

    assert result.decision == StopDecision.STOP_OBJECTIVE_MET
    assert result.should_stop is True


def test_objective_met_wins_over_exhausted_budget():
    """A study that achieved its aim has not failed, whatever it spent."""
    result = evaluate_stop(
        BUDGET,
        state(runs_completed=99, days_elapsed=999, independent_source_families=2, qualified_evidence_count=3),
    )

    assert result.decision == StopDecision.STOP_OBJECTIVE_MET


def test_exhausted_run_budget_stops_the_study():
    result = evaluate_stop(BUDGET, state(runs_completed=10))

    assert result.decision == StopDecision.STOP_BUDGET_EXHAUSTED
    assert any("Run budget" in reason for reason in result.reasons)


def test_exhausted_time_budget_stops_the_study():
    result = evaluate_stop(BUDGET, state(days_elapsed=60))

    assert result.decision == StopDecision.STOP_BUDGET_EXHAUSTED


def test_a_stalled_study_stops_before_the_budget_runs_out():
    result = evaluate_stop(BUDGET, state(runs_since_progress=3))

    assert result.decision == StopDecision.STOP_NO_PROGRESS
    assert "Change the source strategy" in result.recommended_action


def test_an_external_blocker_is_a_pause_not_a_failure():
    result = evaluate_stop(BUDGET, state(runs_since_progress=5, unresolved_external_blockers=("source offline",)))

    assert result.decision == StopDecision.STOP_BLOCKED_EXTERNALLY
    assert "escalate" in result.recommended_action


def test_continue_reports_what_is_still_needed():
    result = evaluate_stop(BUDGET, state())

    assert result.decision == StopDecision.CONTINUE
    assert result.should_stop is False
    assert any("independent source family" in reason for reason in result.reasons)


# --------------------------------------------------------------------------
# Claim register
# --------------------------------------------------------------------------


APPROVED_EVIDENCE = {"EV-1": {"review_state": "APPROVED", "evidence_id": "EV-1"}}
UNREVIEWED_EVIDENCE = {"EV-2": {"review_state": "PENDING_REVIEW", "evidence_id": "EV-2"}}


def test_a_claim_with_approved_evidence_is_publishable():
    claim = make_claim(
        text="Cuts dispute handling time by 40%",
        audience=ClaimAudience.PUBLIC_MARKETING,
        supporting_evidence_ids=("EV-1",),
    )

    assessment = assess_claim(claim, APPROVED_EVIDENCE)

    assert assessment.status == ClaimStatus.SUPPORTED
    assert assessment.publishable is True


def test_a_claim_with_no_evidence_cannot_be_published():
    claim = make_claim(text="The best dispute platform available", audience=ClaimAudience.PUBLIC_MARKETING)

    assessment = assess_claim(claim, {})

    assert assessment.status == ClaimStatus.UNSUPPORTED
    assert assessment.publishable is False
    assert any("No supporting evidence" in reason for reason in assessment.reasons)


def test_a_claim_citing_missing_evidence_is_not_publishable():
    claim = make_claim(
        text="Cuts handling time by half",
        audience=ClaimAudience.PUBLIC_MARKETING,
        supporting_evidence_ids=("EV-404",),
    )

    assessment = assess_claim(claim, APPROVED_EVIDENCE)

    assert assessment.publishable is False
    assert any("not found" in reason for reason in assessment.reasons)


def test_agent_drafted_support_does_not_make_a_claim_true():
    """An agent asserting a benefit is not the benefit being demonstrated."""
    claim = make_claim(
        text="Reduces cost by 30%",
        audience=ClaimAudience.PUBLIC_MARKETING,
        supporting_evidence_ids=("AGT-1",),
    )

    assessment = assess_claim(claim, {"AGT-1": {"method_used": "agent:copywriter"}})

    assert assessment.status == ClaimStatus.AGENT_ASSERTED
    assert assessment.publishable is False


def test_unreviewed_support_is_reported_distinctly_from_no_support():
    claim = make_claim(
        text="Halves resolution time",
        audience=ClaimAudience.PUBLIC_MARKETING,
        supporting_evidence_ids=("EV-2",),
    )

    assessment = assess_claim(claim, UNREVIEWED_EVIDENCE)

    assert assessment.status == ClaimStatus.UNREVIEWED_SUPPORT
    assert assessment.publishable is False


def test_contradicted_evidence_blocks_the_claim_outright():
    claim = make_claim(
        text="Cuts handling time by 40%",
        audience=ClaimAudience.PUBLIC_MARKETING,
        supporting_evidence_ids=("EV-3",),
    )

    assessment = assess_claim(
        claim, {"EV-3": {"review_state": "APPROVED", "contradiction_flag": True}}
    )

    assert assessment.status == ClaimStatus.CONTRADICTED
    assert assessment.publishable is False


def test_numbers_are_detected_as_quantitative():
    assert make_claim(text="40% faster", audience=ClaimAudience.INTERNAL).quantitative is True
    assert make_claim(text="Reduces manual effort", audience=ClaimAudience.INTERNAL).quantitative is True
    assert make_claim(text="An evidence platform", audience=ClaimAudience.INTERNAL).quantitative is False


def test_publishable_claims_splits_the_register():
    supported = make_claim(
        text="Cuts handling time by 40%",
        audience=ClaimAudience.PUBLIC_MARKETING,
        supporting_evidence_ids=("EV-1",),
    )
    unsupported = make_claim(text="Industry leading", audience=ClaimAudience.PUBLIC_MARKETING)

    publish, withhold = publishable_claims([supported, unsupported], APPROVED_EVIDENCE)

    assert [item.claim["text"] for item in publish] == ["Cuts handling time by 40%"]
    assert [item.claim["text"] for item in withhold] == ["Industry leading"]


# --------------------------------------------------------------------------
# Outcome ledger
# --------------------------------------------------------------------------


def outcome(**overrides):
    payload = dict(
        claim_id="CLM-1",
        measure="median dispute handling hours",
        direction=Direction.LOWER_IS_BETTER,
        predicted_value=10.0,
        observed_value=6.0,
        unit="hours",
        measurement_method="Median across all disputes in period",
        period_start="2026-08-01",
        period_end="2026-08-31",
        sample_size=250,
        recorded_by="a-person",
    )
    payload.update(overrides)
    return record_outcome(**payload)


def test_a_better_result_on_a_lower_is_better_measure_is_exceeded():
    assert outcome().status == OutcomeStatus.EXCEEDED


def test_meeting_the_prediction_is_delivered():
    assert outcome(observed_value=10.2).status == OutcomeStatus.DELIVERED


def test_a_worse_result_is_a_shortfall_not_a_rounding():
    result = outcome(observed_value=15.0)

    assert result.status == OutcomeStatus.SHORTFALL
    assert any("short by" in reason for reason in result.reasons)


def test_direction_is_respected_for_higher_is_better_measures():
    result = outcome(
        measure="disputes resolved per day",
        direction=Direction.HIGHER_IS_BETTER,
        predicted_value=10.0,
        observed_value=6.0,
    )

    assert result.status == OutcomeStatus.SHORTFALL


def test_an_underpowered_sample_is_inconclusive_not_delivered():
    result = outcome(observed_value=6.0, sample_size=3)

    assert result.status == OutcomeStatus.INCONCLUSIVE
    assert any("noise" in reason for reason in result.reasons)


def test_no_measurement_is_reported_as_unmeasured():
    assert outcome(observed_value=None).status == OutcomeStatus.UNMEASURED


def test_a_shortfall_contradicts_the_claim_it_tested():
    shortfall = outcome(observed_value=15.0)

    assert claims_contradicted_by([shortfall, outcome()]) == ["CLM-1"]
    assert outcome_evidence_item(shortfall)["contradiction_flag"] is True


def test_outcome_feeds_back_as_prototype_evidence():
    item = outcome_evidence_item(outcome())

    assert item["evidence_class"] == "E7_PROTOTYPE"
    assert item["linked_gates"] == ["G5_VALUE_PLAUSIBILITY"]
    assert item["review_state"] == "PENDING_REVIEW"


def test_the_loop_closes_a_shortfall_stops_the_claim_being_published():
    """End to end: a published claim, measured, falsified, withdrawn."""
    claim = make_claim(
        text="Cuts handling time by 40%",
        audience=ClaimAudience.PUBLIC_MARKETING,
        supporting_evidence_ids=("EV-1",),
    )
    assert assess_claim(claim, APPROVED_EVIDENCE).publishable is True

    measured = record_outcome(
        claim_id=claim.claim_id,
        measure="median dispute handling hours",
        direction=Direction.LOWER_IS_BETTER,
        predicted_value=6.0,
        observed_value=11.0,
        unit="hours",
        measurement_method="Median across all disputes in period",
        period_start="2026-08-01",
        period_end="2026-08-31",
        sample_size=250,
        recorded_by="a-person",
    )
    assert measured.status == OutcomeStatus.SHORTFALL
    assert claim.claim_id in claims_contradicted_by([measured])

    # The measurement returns as evidence, flagged, and the claim is now blocked.
    evidence_index = {**APPROVED_EVIDENCE, measured.outcome_id: outcome_evidence_item(measured)}
    revised = make_claim(
        text=claim.text,
        audience=ClaimAudience.PUBLIC_MARKETING,
        supporting_evidence_ids=("EV-1", measured.outcome_id),
    )

    assert assess_claim(revised, evidence_index).status == ClaimStatus.CONTRADICTED
