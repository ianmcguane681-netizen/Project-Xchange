"""Record a buyer conversation, and see what it does and does not prove.

The study can retrieve complaints, court records and coded judgments without
anyone leaving the room. It cannot retrieve a buyer. PG-10, PG-11 and PG-12 have
failed in every run since the study began, and they will keep failing until
somebody has a conversation and writes down what was said.

This is the front door for that. It refuses placeholders rather than storing
them, because a field reading "TBD" has already been counted as an answer by
three separate gates in this system.

    commercial record   --organisation "..." --role "..." ...
    commercial status                 what the recorded conversations support
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from commercial.buyer import (
    BuyerEvidence,
    BuyerEvidenceError,
    ContactMethod,
    SpendBasis,
    qualifies_for_buyer_gate,
    qualifies_for_pricing_evidence,
    record_buyer_evidence,
    to_sv_evidence_item,
)

DEFAULT_LEDGER = Path("data/buyer_evidence.json")


def _load(path: Path) -> list[BuyerEvidence]:
    if not path.is_file():
        return []
    return [BuyerEvidence(**row) for row in json.loads(path.read_text(encoding="utf-8"))]


def _save(path: Path, records: list[BuyerEvidence]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([record.to_dict() for record in records], indent=2) + "\n", encoding="utf-8"
    )


def cmd_record(args: argparse.Namespace) -> int:
    path = Path(args.ledger)
    records = _load(path)
    try:
        record = record_buyer_evidence(
            organisation=args.organisation,
            respondent_role=args.role,
            contact_method=ContactMethod(args.method),
            occurred_at=args.occurred_at,
            recorded_by=args.recorded_by,
            consent_reference=args.consent,
            holds_budget_authority=args.budget_authority,
            stated_problem=args.problem,
            stated_willingness=args.willingness,
            verbatim_quotes=tuple(args.quote or ()),
            current_system=args.current_system,
            current_spend=args.current_spend,
            spend_basis=SpendBasis(args.spend_basis),
        )
    except BuyerEvidenceError as error:
        print(f"Refused [{error.code}]: {error}")
        if error.details:
            print(f"  {json.dumps(error.details)}")
        return 1

    if any(item.content_hash == record.content_hash for item in records):
        print("Already recorded; nothing changed.")
        return 0
    records.append(record)
    _save(path, records)
    print(f"Recorded {record.evidence_id} - {record.respondent_role} at {record.organisation}")
    print(f"  written to {path}")
    print("\nNext: commercial status")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    records = _load(Path(args.ledger))
    if not records:
        print("No buyer conversations recorded.")
        print("\nPG-10, PG-11 and PG-12 cannot pass until someone has one.")
        return 0

    organisations = sorted({record.organisation for record in records})
    print(f"{len(records)} conversation(s) across {len(organisations)} organisation(s)")
    for record in records:
        spend = (
            f"{record.current_spend} ({record.spend_basis.lower()})"
            if record.current_spend
            else "not provided"
        )
        budget = "budget holder" if record.holds_budget_authority else "no budget authority"
        print(f"  {record.organisation} - {record.respondent_role} [{budget}]")
        print(f"      uses:  {record.current_system or 'not stated'}")
        print(f"      pays:  {spend}")

    buyer_ok, buyer_reasons = qualifies_for_buyer_gate(records)
    price_ok, price_reasons = qualifies_for_pricing_evidence(records)
    print(f"\nG4 buyer credibility:   {'SUPPORTED' if buyer_ok else 'NOT YET'}")
    for reason in buyer_reasons:
        print(f"    - {reason}")
    print(f"PG-11/12 pricing:       {'SUPPORTED' if price_ok else 'NOT YET'}")
    for reason in price_reasons:
        print(f"    - {reason}")

    if args.export:
        target = Path(args.export)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps([to_sv_evidence_item(record) for record in records], indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"\nSV Engine evidence written to {target} (PENDING_REVIEW until a human signs it)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="commercial", description="Record buyer conversations.")
    parser.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    sub = parser.add_subparsers(dest="command", required=True)

    record = sub.add_parser("record", help="Record one conversation")
    record.add_argument("--organisation", required=True)
    record.add_argument("--role", required=True, help="Their role, not their name")
    record.add_argument("--method", default=ContactMethod.INTERVIEW, choices=[str(item) for item in ContactMethod])
    record.add_argument("--occurred-at", required=True, help="ISO timestamp of the conversation")
    record.add_argument("--recorded-by", required=True)
    record.add_argument("--consent", required=True, help="Reference to their recorded consent")
    record.add_argument("--budget-authority", action="store_true", help="They control a budget")
    record.add_argument("--problem", required=True, help="The problem in their words")
    record.add_argument("--willingness", default="", help="What they said about paying")
    record.add_argument("--current-system", default="", help="What they use today")
    record.add_argument("--current-spend", default="", help="What they pay today")
    record.add_argument(
        "--spend-basis",
        default=SpendBasis.NOT_PROVIDED,
        choices=[str(item) for item in SpendBasis],
        help="How the spend figure was obtained",
    )
    record.add_argument("--quote", action="append", help="Verbatim quote; repeatable")
    record.set_defaults(func=cmd_record)

    status = sub.add_parser("status", help="What the conversations so far support")
    status.add_argument("--export", help="Write SV Engine evidence items to this path")
    status.set_defaults(func=cmd_status)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
