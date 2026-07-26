"""What buyers use and pay today, recorded so it can be weighed.

PG-10, PG-11 and PG-12 have failed in every run of the study, and no dataset
closes them. "Better for Cheaper" needs a number to be cheaper *than*, and that
number only exists once someone has a conversation.

Two design choices carry most of these tests. Placeholders are refused at the
point of entry rather than caught at a gate, because three separate gates in this
system have already counted a placeholder as an answer. And a spend figure must
record how it was obtained, because a number remembered in conversation and a
number read off a contract are not the same evidence.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from commercial.buyer import (
    BuyerEvidenceError,
    ContactMethod,
    SpendBasis,
    is_placeholder,
    qualifies_for_pricing_evidence,
    record_buyer_evidence,
    to_sv_evidence_item,
)
from commercial.cli import main


def conversation(organisation="Rising Point Solutions", **overrides):
    payload = dict(
        organisation=organisation,
        respondent_role="Director of Operations",
        contact_method=ContactMethod.INTERVIEW,
        occurred_at="2026-07-27T10:00:00Z",
        recorded_by="ian.mcguane",
        consent_reference="CONSENT-001",
        holds_budget_authority=True,
        stated_problem="Dispute status is tracked across spreadsheets with no audit trail.",
        stated_willingness="Would switch for a traceable evidence trail.",
        verbatim_quotes=("We cannot tell you who touched a dispute last",),
        current_system="Manual spreadsheets plus a case inbox",
        current_spend="approx 2000 USD/month",
        spend_basis=SpendBasis.STATED,
    )
    payload.update(overrides)
    return record_buyer_evidence(**payload)


# --- Placeholders are refused where they are typed ----------------------------


@pytest.mark.parametrize("value", ["unknown", "TBD", "n/a", "N/A", "none", "not assessed", "-", "?"])
def test_a_placeholder_is_refused_rather_than_stored(value):
    with pytest.raises(BuyerEvidenceError) as error:
        conversation(respondent_role=value)

    assert error.value.code == "BUYER_EVIDENCE_PLACEHOLDER"
    assert "respondent_role" in error.value.details["fields"]


def test_an_empty_field_is_allowed_because_absent_reads_as_absent():
    """The point of refusing placeholders is that empty is the honest way to say
    'not known'. Blocking both would just push people to type 'unknown'."""
    record = conversation(current_system="", current_spend="", spend_basis=SpendBasis.NOT_PROVIDED)

    assert record.current_system == ""
    assert record.spend_basis == SpendBasis.NOT_PROVIDED


def test_a_real_answer_containing_a_placeholder_word_is_not_refused():
    record = conversation(stated_problem="Nobody knows who owns the dispute queue")

    assert "Nobody knows" in record.stated_problem
    assert is_placeholder("Nobody knows who owns the dispute queue") is False


# --- A figure and its basis travel together -----------------------------------


def test_a_spend_figure_must_record_how_it_was_obtained():
    with pytest.raises(BuyerEvidenceError) as error:
        conversation(current_spend="2000 USD/month", spend_basis=SpendBasis.NOT_PROVIDED)

    assert error.value.code == "BUYER_SPEND_BASIS_MISSING"


def test_a_basis_without_a_figure_is_refused():
    """Otherwise the record claims a figure was obtained when none was."""
    with pytest.raises(BuyerEvidenceError) as error:
        conversation(current_spend="", spend_basis=SpendBasis.DOCUMENTED)

    assert error.value.code == "BUYER_SPEND_BASIS_WITHOUT_FIGURE"


# --- What the pricing evidence supports ---------------------------------------


def test_one_conversation_does_not_establish_a_market_rate():
    ok, reasons = qualifies_for_pricing_evidence([conversation()])

    assert ok is False
    assert any("organisation" in reason for reason in reasons)


def test_two_organisations_with_stated_figures_support_pricing():
    ok, reasons = qualifies_for_pricing_evidence(
        [conversation(), conversation(organisation="Matos Credit")]
    )

    assert ok is True, reasons


def test_a_declined_answer_is_silence_not_a_low_price():
    """NOT_PROVIDED must never be counted as a figure, in either direction."""
    records = [
        conversation(),
        conversation(
            organisation="Matos Credit",
            current_spend="",
            spend_basis=SpendBasis.NOT_PROVIDED,
        ),
    ]

    ok, reasons = qualifies_for_pricing_evidence(records)

    assert ok is False
    assert any("1 organisation" in reason for reason in reasons)


def test_estimates_alone_do_not_support_pricing():
    records = [
        conversation(current_spend="maybe 2-3k", spend_basis=SpendBasis.ESTIMATED),
        conversation(
            organisation="Matos Credit", current_spend="a few thousand", spend_basis=SpendBasis.ESTIMATED
        ),
    ]

    ok, reasons = qualifies_for_pricing_evidence(records)

    assert ok is False
    assert any("estimate" in reason for reason in reasons)


def test_naming_the_incumbent_links_the_evidence_to_the_competitive_gate():
    item = to_sv_evidence_item(conversation())

    assert "G7_COMPETITIVE_VIABILITY" in item["linked_gates"]
    assert item["current_spend"] == "approx 2000 USD/month"
    assert item["review_state"] == "PENDING_REVIEW"


def test_evidence_without_an_incumbent_does_not_claim_the_competitive_gate():
    item = to_sv_evidence_item(conversation(current_system="", current_spend="", spend_basis=SpendBasis.NOT_PROVIDED))

    assert item["linked_gates"] == ["G4_BUYER_CREDIBILITY"]


# --- The front door -----------------------------------------------------------


def test_the_cli_records_and_reports(tmp_path: Path, capsys):
    ledger = tmp_path / "buyer.json"
    code = main(
        [
            "--ledger", str(ledger), "record",
            "--organisation", "Rising Point Solutions",
            "--role", "Director of Operations",
            "--occurred-at", "2026-07-27T10:00:00Z",
            "--recorded-by", "ian.mcguane",
            "--consent", "CONSENT-001",
            "--budget-authority",
            "--problem", "No audit trail on disputes",
            "--current-system", "Spreadsheets",
            "--current-spend", "2000 USD/month",
            "--spend-basis", "STATED",
            "--quote", "We cannot tell who touched it last",
        ]
    )

    assert code == 0
    assert json.loads(ledger.read_text(encoding="utf-8"))[0]["current_spend"] == "2000 USD/month"

    main(["--ledger", str(ledger), "status"])
    out = capsys.readouterr().out
    assert "NOT YET" in out  # one conversation proves nothing


def test_the_cli_refuses_a_placeholder_without_writing_anything(tmp_path: Path, capsys):
    ledger = tmp_path / "buyer.json"
    code = main(
        [
            "--ledger", str(ledger), "record",
            "--organisation", "Rising Point Solutions",
            "--role", "TBD",
            "--occurred-at", "2026-07-27T10:00:00Z",
            "--recorded-by", "ian.mcguane",
            "--consent", "CONSENT-001",
            "--problem", "No audit trail",
        ]
    )

    assert code == 1
    assert "BUYER_EVIDENCE_PLACEHOLDER" in capsys.readouterr().out
    assert not ledger.exists()


def test_recording_the_same_conversation_twice_changes_nothing(tmp_path: Path):
    ledger = tmp_path / "buyer.json"
    argv = [
        "--ledger", str(ledger), "record",
        "--organisation", "Matos Credit",
        "--role", "Operations Manager",
        "--occurred-at", "2026-07-27T11:00:00Z",
        "--recorded-by", "ian.mcguane",
        "--consent", "CONSENT-002",
        "--problem", "Disputes handled by hand",
    ]
    main(argv)
    main(argv)

    assert len(json.loads(ledger.read_text(encoding="utf-8"))) == 1
