"""The commercial half of the pipeline.

The studies establish that a problem is real. These modules cover what happens
between that point and a product in the market: who would pay, when to stop
looking, what may be claimed publicly, what actually happened after launch, and
the rule that agent output is never evidence.

Kept out of any single study, because none of it is market-specific.
"""

from commercial.agent_guard import (
    AgentGovernanceError,
    AgentOutput,
    AgentOutputKind,
    assert_not_evidence,
    record_agent_output,
    require_human_review,
)
from commercial.buyer import (
    BuyerEvidence,
    BuyerEvidenceError,
    ContactMethod,
    qualifies_for_buyer_gate,
    record_buyer_evidence,
)
from commercial.claims import (
    Claim,
    ClaimAudience,
    ClaimStatus,
    assess_claim,
    make_claim,
    publishable_claims,
)
from commercial.outcomes import (
    Direction,
    OutcomeRecord,
    OutcomeStatus,
    claims_contradicted_by,
    record_outcome,
)
from commercial.stop_rules import (
    StopAssessment,
    StopDecision,
    StudyBudget,
    StudyState,
    evaluate_stop,
)

__all__ = [
    "AgentGovernanceError", "AgentOutput", "AgentOutputKind", "assert_not_evidence",
    "record_agent_output", "require_human_review",
    "BuyerEvidence", "BuyerEvidenceError", "ContactMethod", "qualifies_for_buyer_gate",
    "record_buyer_evidence",
    "Claim", "ClaimAudience", "ClaimStatus", "assess_claim", "make_claim", "publishable_claims",
    "Direction", "OutcomeRecord", "OutcomeStatus", "claims_contradicted_by", "record_outcome",
    "StopAssessment", "StopDecision", "StudyBudget", "StudyState", "evaluate_stop",
]
