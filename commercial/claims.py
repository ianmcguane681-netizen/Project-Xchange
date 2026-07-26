"""Public claims must trace to approved evidence.

The pitch is where a carefully evidenced system usually starts lying - not
deliberately, but because marketing copy is written by a different person, in a
different tool, weeks later, from memory. "Cuts resolution time by half" becomes
true by repetition rather than by measurement.

A claim registered here carries the evidence that supports it, or it cannot be
published. Agent-drafted copy is a proposal, never support: an agent asserting a
benefit is not the benefit being demonstrated.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

from commercial.agent_guard import carries_agent_provenance
from rbe_runtime.canonical import canonical_hash, deterministic_id

APPROVED = "APPROVED"


class ClaimAudience(StrEnum):
    PUBLIC_MARKETING = "PUBLIC_MARKETING"
    SALES_COLLATERAL = "SALES_COLLATERAL"
    PRODUCT_DOCUMENTATION = "PRODUCT_DOCUMENTATION"
    INTERNAL = "INTERNAL"


class ClaimStatus(StrEnum):
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    UNREVIEWED_SUPPORT = "UNREVIEWED_SUPPORT"
    AGENT_ASSERTED = "AGENT_ASSERTED"
    CONTRADICTED = "CONTRADICTED"


@dataclass(frozen=True, slots=True)
class Claim:
    claim_id: str
    text: str
    audience: str
    quantitative: bool
    supporting_evidence_ids: tuple[str, ...]
    drafted_by: str

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["supporting_evidence_ids"] = list(self.supporting_evidence_ids)
        return value


@dataclass(frozen=True, slots=True)
class ClaimAssessment:
    claim: dict[str, Any]
    status: str
    reasons: tuple[str, ...]
    supporting_evidence_ids: tuple[str, ...]

    @property
    def publishable(self) -> bool:
        return self.status == ClaimStatus.SUPPORTED

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["reasons"] = list(self.reasons)
        value["supporting_evidence_ids"] = list(self.supporting_evidence_ids)
        value["publishable"] = self.publishable
        return value


def make_claim(
    *,
    text: str,
    audience: ClaimAudience,
    supporting_evidence_ids: tuple[str, ...] = (),
    drafted_by: str = "",
    quantitative: bool | None = None,
) -> Claim:
    if not text.strip():
        raise ValueError("A claim must have text")
    return Claim(
        claim_id=deterministic_id("CLM", text.strip(), str(audience), canonical_hash(sorted(supporting_evidence_ids))),
        text=text.strip(),
        audience=str(audience),
        quantitative=_looks_quantitative(text) if quantitative is None else quantitative,
        supporting_evidence_ids=tuple(sorted(supporting_evidence_ids)),
        drafted_by=drafted_by,
    )


def _looks_quantitative(text: str) -> bool:
    """A claim carrying a number promises a measurement, so it needs one."""

    return any(character.isdigit() for character in text) or any(
        word in text.lower()
        for word in ("faster", "cheaper", "reduces", "cuts", "increases", "doubles", "halves", "%")
    )


PUBLIC_AUDIENCES = {ClaimAudience.PUBLIC_MARKETING, ClaimAudience.SALES_COLLATERAL}


def assess_claim(claim: Claim, evidence_index: dict[str, Any]) -> ClaimAssessment:
    """Decide whether a claim may be published, and say why not when it may not.

    `evidence_index` maps evidence id to the evidence record. A record counts as
    support only when it exists, is approved by a human, and did not come from an
    agent.
    """

    reasons: list[str] = []
    found = {key: evidence_index[key] for key in claim.supporting_evidence_ids if key in evidence_index}
    missing = sorted(set(claim.supporting_evidence_ids) - set(found))
    if missing:
        reasons.append(f"Cited evidence not found: {', '.join(missing)}.")

    agent_backed = sorted(key for key, value in found.items() if carries_agent_provenance(value))
    if agent_backed:
        reasons.append(
            f"Support is agent-generated, which is a proposal rather than proof: {', '.join(agent_backed)}."
        )

    contradicted = sorted(key for key, value in found.items() if _flag(value, "contradiction_flag"))
    if contradicted:
        return ClaimAssessment(
            claim=claim.to_dict(),
            status=ClaimStatus.CONTRADICTED,
            reasons=(f"Cited evidence is flagged as contradicted: {', '.join(contradicted)}.",),
            supporting_evidence_ids=tuple(sorted(found)),
        )

    usable = {key: value for key, value in found.items() if key not in agent_backed}
    approved = sorted(key for key, value in usable.items() if _review_state(value) == APPROVED)
    unapproved = sorted(set(usable) - set(approved))

    if not claim.supporting_evidence_ids:
        reasons.append("No supporting evidence is cited.")

    if agent_backed and not usable:
        status = ClaimStatus.AGENT_ASSERTED
    elif not approved and unapproved:
        status = ClaimStatus.UNREVIEWED_SUPPORT
        reasons.append(f"Supporting evidence is not human-approved: {', '.join(unapproved)}.")
    elif not approved:
        status = ClaimStatus.UNSUPPORTED
    else:
        status = ClaimStatus.SUPPORTED

    # A number promises a measurement. Public numeric claims need approved support
    # specifically, not merely something on file.
    if (
        status == ClaimStatus.SUPPORTED
        and claim.quantitative
        and ClaimAudience(claim.audience) in PUBLIC_AUDIENCES
        and not approved
    ):  # pragma: no cover - defensive; SUPPORTED implies approved
        status = ClaimStatus.UNSUPPORTED

    if status == ClaimStatus.SUPPORTED:
        reasons = [f"Supported by approved evidence: {', '.join(approved)}."]

    return ClaimAssessment(
        claim=claim.to_dict(),
        status=status,
        reasons=tuple(reasons),
        supporting_evidence_ids=tuple(approved),
    )


def _review_state(record: Any) -> str:
    if isinstance(record, dict):
        return str(record.get("review_state") or "")
    return str(getattr(record, "review_state", "") or "")


def _flag(record: Any, name: str) -> bool:
    if isinstance(record, dict):
        return bool(record.get(name))
    return bool(getattr(record, name, False))


def publishable_claims(
    claims: list[Claim], evidence_index: dict[str, Any]
) -> tuple[list[ClaimAssessment], list[ClaimAssessment]]:
    """Split claims into those that may be published and those that may not."""

    assessments = [assess_claim(claim, evidence_index) for claim in claims]
    return (
        [item for item in assessments if item.publishable],
        [item for item in assessments if not item.publishable],
    )
