"""Identifying an incumbent is not assessing one.

G7 previously asked only whether any competitor record existed. A record naming an
incumbent with placeholder comparative fields therefore satisfied the gate, which
let machine-retrieved market data - which explicitly records that it has assessed
nothing - carry a build decision. G4 already refuses "unknown" buyer fields; this
holds G7 to the same standard.

Also guards the shipped example inputs, which had drifted out of step with the
engine's reference validation: every documented example failed to evaluate while
the suite stayed green, because the tests used in-code fixtures instead.
"""
from __future__ import annotations

import copy
import glob
import json
from pathlib import Path

import pytest

from sv_engine.fixtures.cases import build_prototype_case
from sv_engine.services.assessment import is_assessed_competitor
from sv_engine.services.engine import SolutionValidationEngine

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_INPUTS = sorted(glob.glob(str(REPO_ROOT / "examples/sv_engine/inputs/*.json")))


class _Competitor:
    def __init__(self, strengths=(), weaknesses=(), differentiation="unknown"):
        self.strengths = tuple(strengths)
        self.weaknesses = tuple(weaknesses)
        self.differentiation = differentiation


def gate_for(payload: dict) -> tuple[str, list[str], str]:
    result = SolutionValidationEngine().evaluate_dict(payload)
    gate = [
        item for item in result.record.gate_assessments
        if item.gate_id == "G7_COMPETITIVE_VIABILITY"
    ][0]
    return gate.status.value, list(gate.unresolved_questions), result.record.verdict.value


def market_style_competitor() -> dict:
    """Mirrors what the market lane emits: identified, explicitly unassessed."""
    return {
        "competitor_id": "MENT-TRANSUNION",
        "name": "TransUnion",
        "alternative_type": "incumbent consumer credit reporting agency",
        "strengths": ["not assessed from regulatory filings"],
        "weaknesses": ["not assessed from regulatory filings"],
        "pricing": "not disclosed in SEC filings",
        "switching_cost": "not assessed from regulatory filings",
        "differentiation": "not assessed from regulatory filings",
        "evidence_ids": [],
    }


@pytest.mark.parametrize(
    ("competitor", "expected"),
    [
        (_Competitor(differentiation="Traceable evidence trail"), True),
        (_Competitor(strengths=["Incumbent scale"]), True),
        (_Competitor(weaknesses=["Manual reinvestigation"]), True),
        (_Competitor(), False),
        (_Competitor(strengths=["unknown"], weaknesses=["N/A"], differentiation="TBD"), False),
        (_Competitor(strengths=["not assessed from regulatory filings"]), False),
    ],
)
def test_placeholder_fields_do_not_count_as_assessment(competitor, expected):
    assert is_assessed_competitor(competitor) is expected


def test_gate_is_unresolved_when_no_competitor_exists():
    payload = copy.deepcopy(build_prototype_case())
    payload["competitors"] = []

    status, unresolved, _verdict = gate_for(payload)

    assert status == "UNRESOLVED"
    assert any("at least one current alternative" in item.lower() for item in unresolved)


def test_identified_but_unassessed_competitor_does_not_pass_the_gate():
    payload = copy.deepcopy(build_prototype_case())
    payload["competitors"] = [market_style_competitor()]

    status, unresolved, verdict = gate_for(payload)

    assert status == "UNRESOLVED"
    assert any("not assessing it" in item for item in unresolved)
    assert verdict != "BUILD PROTOTYPE"


def test_a_real_comparative_judgement_passes_the_gate():
    payload = copy.deepcopy(build_prototype_case())
    competitor = market_style_competitor()
    competitor.update(
        strengths=["Incumbent scale and direct furnisher relationships"],
        weaknesses=["Dispute reinvestigation is manual and opaque to consumers"],
        differentiation="Traceable, auditable reinvestigation evidence trail",
    )
    payload["competitors"] = [competitor]

    status, _unresolved, _verdict = gate_for(payload)

    assert status == "PASS"


@pytest.mark.parametrize("path", EXAMPLE_INPUTS, ids=lambda value: Path(value).name)
def test_shipped_example_inputs_evaluate(path: str):
    """The README documents running these; they must not drift out of step again."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))

    result = SolutionValidationEngine().evaluate_dict(payload)

    assert result.record.verdict.value


def test_example_filenames_match_the_verdict_they_produce():
    expected = {
        "build_prototype.json": "BUILD PROTOTYPE",
        "do_not_build_operability.json": "DO NOT BUILD",
        "validate_further.json": "VALIDATE FURTHER",
    }
    engine = SolutionValidationEngine()
    for path in EXAMPLE_INPUTS:
        name = Path(path).name
        if name not in expected:
            continue
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        assert engine.evaluate_dict(payload).record.verdict.value == expected[name]
