"""Evidence from people who would actually pay.

Every source in the studies so far is documentary: complaints, court records,
regulatory filings. All of it establishes that something happened. None of it
establishes that anyone will buy, and no database ever will - that evidence only
exists once someone has spoken to a real buyer.

The SV Engine already demands it (G4_BUYER_CREDIBILITY requires direct-buyer
evidence, class E2_DIRECT_BUYER). This module is the lane that produces it, held
to the same standard as every other source: named provenance, recorded consent,
and no anonymous hearsay.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

from commercial.agent_guard import assert_not_evidence
from rbe_runtime.canonical import canonical_hash, deterministic_id

# sv_engine.domain.enums.EvidenceClass.DIRECT_BUYER
DIRECT_BUYER_CLASS = "E2_DIRECT_BUYER"


class ContactMethod(StrEnum):
    INTERVIEW = "INTERVIEW"
    SURVEY = "SURVEY"
    DEMO_SESSION = "DEMO_SESSION"
    PROCUREMENT_CONVERSATION = "PROCUREMENT_CONVERSATION"


class BuyerEvidenceError(RuntimeError):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


@dataclass(frozen=True, slots=True)
class BuyerEvidence:
    evidence_id: str
    organisation: str
    respondent_role: str
    contact_method: str
    occurred_at: str
    recorded_by: str
    consent_reference: str
    holds_budget_authority: bool
    stated_problem: str
    stated_willingness: str
    verbatim_quotes: tuple[str, ...]
    evidence_class: str = DIRECT_BUYER_CLASS
    content_hash: str = ""
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["verbatim_quotes"] = list(self.verbatim_quotes)
        value["limitations"] = list(self.limitations)
        return value


DEFAULT_LIMITATIONS = (
    "A single respondent is not a market.",
    "Stated willingness to buy is not a purchase.",
    "Respondents may overstate intent in a conversation with a vendor.",
)


def record_buyer_evidence(
    *,
    organisation: str,
    respondent_role: str,
    contact_method: ContactMethod,
    occurred_at: str,
    recorded_by: str,
    consent_reference: str,
    holds_budget_authority: bool,
    stated_problem: str,
    stated_willingness: str,
    verbatim_quotes: tuple[str, ...] = (),
    limitations: tuple[str, ...] = DEFAULT_LIMITATIONS,
) -> BuyerEvidence:
    """Create buyer evidence, refusing anything that cannot be traced to a person.

    Consent is required rather than encouraged: this is evidence about identifiable
    people at identifiable organisations, and an unconsented record cannot be shown
    to a reviewer, which makes it useless as proof even when it is true.
    """

    missing = [
        name
        for name, value in (
            ("organisation", organisation),
            ("respondent_role", respondent_role),
            ("occurred_at", occurred_at),
            ("recorded_by", recorded_by),
            ("stated_problem", stated_problem),
        )
        if not str(value).strip()
    ]
    if missing:
        raise BuyerEvidenceError(
            "BUYER_EVIDENCE_INCOMPLETE",
            "Buyer evidence must identify the organisation, role, time, recorder and problem",
            {"missing": missing},
        )
    if not str(consent_reference).strip():
        raise BuyerEvidenceError(
            "BUYER_CONSENT_MISSING",
            "Buyer evidence requires a recorded consent reference",
        )

    payload = {
        "organisation": organisation,
        "respondent_role": respondent_role,
        "contact_method": str(contact_method),
        "occurred_at": occurred_at,
        "stated_problem": stated_problem,
        "stated_willingness": stated_willingness,
        "verbatim_quotes": sorted(verbatim_quotes),
    }
    content_hash = canonical_hash(payload)
    return BuyerEvidence(
        evidence_id=deterministic_id("BUY", organisation, respondent_role, occurred_at, content_hash),
        organisation=organisation,
        respondent_role=respondent_role,
        contact_method=str(contact_method),
        occurred_at=occurred_at,
        recorded_by=recorded_by,
        consent_reference=consent_reference,
        holds_budget_authority=holds_budget_authority,
        stated_problem=stated_problem,
        stated_willingness=stated_willingness,
        verbatim_quotes=tuple(verbatim_quotes),
        content_hash=content_hash,
        limitations=tuple(limitations),
    )


def qualifies_for_buyer_gate(records: list[BuyerEvidence], *, minimum_organisations: int = 2) -> tuple[bool, list[str]]:
    """Whether buyer evidence is strong enough to support the buyer gate.

    One enthusiastic conversation is the easiest evidence in the world to collect
    and the least informative. The bar is distinct organisations, and at least one
    respondent who actually controls a budget.
    """

    for record in records:
        assert_not_evidence(record.to_dict(), position="buyer evidence")

    reasons: list[str] = []
    organisations = {record.organisation.strip().lower() for record in records if record.organisation.strip()}
    if len(organisations) < minimum_organisations:
        reasons.append(
            f"Buyer evidence spans {len(organisations)} organisation(s); {minimum_organisations} required."
        )
    if not any(record.holds_budget_authority for record in records):
        reasons.append("No respondent holds budget authority.")
    if not any(record.verbatim_quotes for record in records):
        reasons.append("No verbatim account was recorded; paraphrase alone is not testable.")
    return (not reasons), reasons


def to_sv_evidence_item(record: BuyerEvidence) -> dict[str, Any]:
    """Emit in the SV Engine's evidence shape, unreviewed until a human signs it."""

    return {
        "evidence_id": record.evidence_id,
        "title": f"{record.respondent_role} at {record.organisation}",
        "description": record.stated_problem,
        "relevant_claim": record.stated_willingness or record.stated_problem,
        "evidence_class": DIRECT_BUYER_CLASS,
        "source_type": f"buyer_{record.contact_method.lower()}",
        "source_organisation": record.organisation,
        "source_locator": record.consent_reference,
        "content_hash": record.content_hash,
        "date_observed_or_published": record.occurred_at,
        "retrieval_timestamp": record.occurred_at,
        "provenance": f"Recorded by {record.recorded_by}; consent {record.consent_reference}",
        "linked_categories": ["C6_BUYER_DEFINITION"],
        "linked_gates": ["G4_BUYER_CREDIBILITY"],
        "review_state": "PENDING_REVIEW",
        "reviewed_by": "",
        "reviewed_at": "",
        "confidence_contribution": 0.0,
        "contradiction_flag": False,
        "assumptions": [],
        "limitations": list(record.limitations),
    }
