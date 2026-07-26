"""No SV Engine gate may pass on placeholder values.

Companion to GS-CF001's `tests/test_placeholder_gates.py`. The board has now
raised this failure three times in this system:

  * G7 passed on competitor records reading "not assessed from regulatory
    filings" -- identifying an incumbent counted as assessing one.
  * PG-09 passed because an adjudication and a complaint matched each other on
    *both being unclassified*.
  * G4 checked buyer fields for the empty string and the literal "unknown", while
    a shared marker set covering "TBD", "n/a" and "not assessed" already existed
    a few lines above it for G7's benefit. A buyer map naming "TBD" as the
    economic buyer satisfied the buyer credibility gate.

The pattern is always the same: a value meaning "we have not judged this yet" is
read as a judgement. Tests supplying realistic data cannot catch it, so this
module supplies placeholders in every spelling the codebase itself recognises,
and asserts the gates refuse them.
"""
from __future__ import annotations

import copy

import pytest

from sv_engine.fixtures.cases import build_prototype_case
from sv_engine.services.assessment import UNASSESSED_MARKERS, _is_unassessed
from sv_engine.services.engine import SolutionValidationEngine

# Every spelling the codebase recognises as "not judged yet", plus the casing
# variants a human filling in a form would actually type.
PLACEHOLDER_SPELLINGS = ("unknown", "Unknown", "UNKNOWN", "n/a", "N/A", "tbd", "TBD", "not assessed", "")


def gate_status(payload: dict, gate_id: str) -> tuple[str, list[str]]:
    result = SolutionValidationEngine().evaluate_dict(payload)
    gate = [item for item in result.record.gate_assessments if item.gate_id == gate_id][0]
    return gate.status.value, list(gate.unresolved_questions)


def test_every_recognised_marker_is_treated_as_unassessed():
    """The shared helper is the single definition. Gates must use it, not their own."""
    for spelling in PLACEHOLDER_SPELLINGS:
        assert _is_unassessed(spelling) is True, f"{spelling!r} should read as unassessed"
    assert _is_unassessed("Jane Smith, VP Operations") is False
    assert set(UNASSESSED_MARKERS) >= {"unknown", "not assessed", "n/a", "tbd"}


@pytest.mark.parametrize("spelling", [item for item in PLACEHOLDER_SPELLINGS if item])
def test_g4_refuses_a_placeholder_buyer_in_any_spelling(spelling):
    """The hole: only "" and "unknown" were caught, so "TBD" named a buyer.

    This is the gate the buyer evidence lane feeds, so a placeholder passing here
    would convert "we have not spoken to anyone" into a credible buyer.
    """
    payload = copy.deepcopy(build_prototype_case())
    payload["buyer_map"]["economic_buyer"] = spelling

    status, unresolved = gate_status(payload, "G4_BUYER_CREDIBILITY")

    assert status != "PASS"
    assert any("purchase authority" in item or "Buyer identity" in item for item in unresolved)


@pytest.mark.parametrize("field", ["economic_buyer", "budget_source", "purchase_authority"])
def test_every_buyer_field_is_checked_not_just_the_first(field):
    payload = copy.deepcopy(build_prototype_case())
    payload["buyer_map"][field] = "TBD"

    status, _unresolved = gate_status(payload, "G4_BUYER_CREDIBILITY")

    assert status != "PASS"


def test_a_wholly_placeholder_case_reaches_no_positive_verdict():
    """The systemic guard: fill every judgement field with a placeholder."""
    payload = copy.deepcopy(build_prototype_case())
    for field in ("economic_buyer", "budget_source", "purchase_authority"):
        payload["buyer_map"][field] = "TBD"
    for competitor in payload.get("competitors", []):
        competitor["strengths"] = ["not assessed"]
        competitor["weaknesses"] = ["n/a"]
        competitor["differentiation"] = "unknown"

    result = SolutionValidationEngine().evaluate_dict(payload)

    assert result.record.verdict.value != "BUILD"
    passing = {
        item.gate_id for item in result.record.gate_assessments if item.status.value == "PASS"
    }
    assert "G4_BUYER_CREDIBILITY" not in passing
    assert "G7_COMPETITIVE_VIABILITY" not in passing


def test_a_real_buyer_still_passes_g4():
    """The guard must not work by making everything fail."""
    payload = copy.deepcopy(build_prototype_case())

    status, _unresolved = gate_status(payload, "G4_BUYER_CREDIBILITY")

    assert status == "PASS"
