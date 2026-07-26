"""A front door for the review board.

The runtime has been complete and tested for a while, and no review had ever been
run through it, because sitting on the board meant writing Python. The existing
`rbe_runtime` CLI only inspects reviews after the fact - version, validate,
verify, export. Nothing convened one.

These commands convene one: open a review, staff it with agent seats, register the
material under review, take the seats' reports, show the challenge sheets, and
ratify and publish. Every command prints what is needed next, so the workflow is
discoverable rather than memorised.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from board.challenges import (
    SEVERITY_EFFECT,
    ChallengeSheet,
    NoChallenge,
    render_review,
    summarise,
)
from board.seats import (
    AgentSeat,
    board_health,
    require_independent_seats,
    shared_model_note,
)
from rbe_runtime.errors import RBEError
from rbe_runtime.service import RBERuntime

DEFAULT_DB = Path("data/review_board.sqlite3")


def _runtime(args: argparse.Namespace) -> RBERuntime:
    return RBERuntime(args.database)


def _load(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _print_next(step: str) -> None:
    print(f"\nNext: {step}")


def cmd_seats(args: argparse.Namespace) -> int:
    """Show the configured agent seats and check they are independent."""

    seats = [
        AgentSeat(
            role=item["role"],
            model=item["model"],
            instruction_version=item["instruction_version"],
            name=item.get("name", ""),
        )
        for item in _load(args.seats)
    ]
    require_independent_seats(seats)
    print(f"{len(seats)} agent seat(s), independence checks passed:\n")
    for seat in seats:
        blind = "  [blind to proposed outcome]" if seat.is_blind else ""
        print(f"  {seat.role:5} {seat.actor:22} {seat.method()}{blind}")
    note = shared_model_note(seats)
    if note:
        print(f"\n  Recorded: {note}")
    _print_next("board open --initiation <file> to convene the review")
    return 0


def cmd_open(args: argparse.Namespace) -> int:
    """Convene a review from an initiation record."""

    runtime = _runtime(args)
    initiation = _load(args.initiation)
    runtime.initiate_review(
        initiation, actor=initiation["board_chair"], idempotency_key=f"open-{initiation['review_id']}"
    )
    print(f"Review {initiation['review_id']} opened in {runtime.repository.get_session(initiation['review_id']).status}.")
    for assignment in runtime.repository.list_assignments(initiation["review_id"]):
        print(f"  seat {assignment.reviewer_role:5} -> {assignment.reviewer_actor}")
    _print_next("board evidence --bundle <proof bundle> to register what is under review")
    return 0


def cmd_evidence(args: argparse.Namespace) -> int:
    """Register a Golden Study proof bundle as the material under review."""

    from study_bridge import StudyBundle, ingest_study_bundle

    runtime = _runtime(args)
    bundle = StudyBundle.load(args.bundle)
    result = ingest_study_bundle(runtime, args.review, bundle, actor=args.actor)
    print(f"Registered {len(result.reference_ids)} file(s) from {bundle.study_id} run {bundle.run_id}.")
    print(f"  bundle root hash: {bundle.bundle_root_hash}")
    print(f"  code commit:      {bundle.code_commit_hash}")
    _print_next("board advance --to EVIDENCE_LOCKED, then ASSIGNMENT")
    return 0


def cmd_advance(args: argparse.Namespace) -> int:
    """Move the review to its next lifecycle state."""

    runtime = _runtime(args)
    metadata = _load(args.metadata) if args.metadata else None
    runtime.advance(
        args.review,
        args.to,
        actor=args.actor,
        idempotency_key=args.key or f"advance-{args.review}-{args.to}",
        metadata=metadata,
    )
    print(f"{args.review} is now {runtime.repository.get_session(args.review).status}.")
    return 0


def cmd_accept(args: argparse.Namespace) -> int:
    """Accept seats and declare independence, so the review can begin."""

    runtime = _runtime(args)
    for assignment in runtime.repository.list_assignments(args.review):
        runtime.respond_to_assignment(
            args.review,
            assignment.assignment_id,
            actor=assignment.reviewer_actor,
            has_material_conflict=False,
            conflict_basis=None,
            human_signature_ref=f"{args.signature}-{assignment.reviewer_role}",
            idempotency_key=f"accept-{args.review}-{assignment.reviewer_role}",
        )
        print(f"  {assignment.reviewer_role:5} accepted, no material conflict")
    _print_next("board advance --to INDEPENDENT_REVIEW")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    """Submit one seat's report, with any challenge sheets it raised."""

    runtime = _runtime(args)
    payload = _load(args.report)
    assignments = {
        item.reviewer_role: item for item in runtime.repository.list_assignments(args.review)
    }
    assignment = assignments[payload["reviewer_role"]]
    runtime.submit_report(
        args.review,
        assignment.assignment_id,
        raw_report=payload["report"],
        raw_findings=tuple(payload.get("findings", ())),
        finding_categories=payload.get("finding_categories", {}),
        summary=payload["summary"],
        recommendation=payload["recommendation"],
        evidence_reference_ids=tuple(payload["evidence_reference_ids"]),
        actor=assignment.reviewer_actor,
        idempotency_key=f"report-{args.review}-{payload['reviewer_role']}",
    )
    count = len(payload.get("findings", ()))
    print(f"  {payload['reviewer_role']:5} reported: {count} challenge(s)")
    return 0


def cmd_challenges(args: argparse.Namespace) -> int:
    """Show what the board found, worst first."""

    runtime = _runtime(args)
    findings = runtime.repository.list_findings(args.review)
    assignments = {
        item.assignment_id: item for item in runtime.repository.list_assignments(args.review)
    }
    reports = {item.report_id: item for item in runtime.repository.list_reports(args.review)}
    sheets: list[ChallengeSheet] = []
    per_seat: dict[str, int] = {item.reviewer_role: 0 for item in assignments.values()}
    for finding in findings:
        report = reports.get(finding.source_report_id)
        role = assignments[report.assignment_id].reviewer_role if report else "?"
        per_seat[role] = per_seat.get(role, 0) + 1
        # Impact states what the severity means for the decision. Echoing the
        # detail back here would fill the sheet with the same sentence twice.
        sheets.append(
            ChallengeSheet(
                seat=role,
                severity=finding.severity,
                target=finding.title,
                problem=finding.description,
                impact=SEVERITY_EFFECT.get(finding.severity, "recorded"),
                fix=finding.raw_record.get("remediation_requirement")
                or "No remediation required.",
                evidence_ids=finding.evidence_reference_ids,
            )
        )
    silent = [
        NoChallenge(seat=role, checked="Assigned scope")
        for role, count in sorted(per_seat.items())
        if count == 0
    ]
    print(render_review(sheets, silent))
    print("\n" + "-" * 72)
    print(json.dumps(summarise(sheets), indent=2))
    print(json.dumps(board_health(per_seat), indent=2))
    return 0


def cmd_decide(args: argparse.Namespace) -> int:
    """Compute the machine decision candidate from the frozen findings."""

    runtime = _runtime(args)
    result = runtime.prepare_decision_candidate(
        args.review, actor=args.actor, idempotency_key=f"candidate-{args.review}"
    )
    evaluation = result["evaluation"]
    # An idempotent replay returns the evaluation as plain JSON rather than the
    # dataclass, so read it the same way in both cases.
    get = evaluation.get if isinstance(evaluation, dict) else lambda k: getattr(evaluation, k)
    print(f"process status: {get('process_status')}")
    print(f"outcome:        {get('outcome')}")
    print(f"reason:         {get('explanation')}")
    _print_next("board advance --to GOVERNANCE_VALIDATION, then board ratify")
    return 0


def cmd_ratify(args: argparse.Namespace) -> int:
    """Sign the decision. Human authority, never an agent.

    With --validator this is ordinary four-eyes ratification. With
    --single-authority the Board Chair signs alone, which the profile permits only
    while non-binding and which is recorded permanently on the decision.
    """

    runtime = _runtime(args)
    if args.single_authority and args.validator:
        print("Refused: choose either --validator or --single-authority, not both.")
        return 2
    if not args.single_authority and not args.validator:
        print(
            "Refused: ratification needs --validator <name> --validator-signature <ref>,\n"
            "or --single-authority if you are signing alone."
        )
        return 2
    result = runtime.ratify_decision(
        args.review,
        actor=args.actor,
        board_chair_signature_ref=args.signature,
        governance_validator=args.validator,
        governance_validation_ref=args.validator_signature,
        idempotency_key=f"ratify-{args.review}",
        single_authority_rationale=args.rationale,
    )
    if result.get("single_authority"):
        print(f"Decision {result['decision_id']} signed by {args.actor} alone.")
        print("  single authority: true  <-- recorded permanently on this decision")
        print("  the four-eyes control was not satisfied; a two-signature decision")
        print("  can supersede this one later without losing it.")
    else:
        print(f"Decision {result['decision_id']} signed by {args.actor} and {args.validator}.")
    print(f"  outcome:         {result['evaluation']['outcome'] if isinstance(result.get('evaluation'), dict) else ''}")
    print(f"  binding:         {result['binding']}")
    print(f"  merge permitted: {result['merge_permitted']}")
    _print_next("board advance --to DECIDED, then board publish")
    return 0


def cmd_publish(args: argparse.Namespace) -> int:
    """Publish the decision under a separate publication authority."""

    runtime = _runtime(args)
    result = runtime.publish_decision(
        args.review, actor=args.actor, idempotency_key=f"publish-{args.review}"
    )
    print(f"Published {result['publication_id']} by {args.actor}.")
    _print_next("board advance --to PUBLISHED, then rbe-runtime export")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Where the review is, and what it is waiting on."""

    runtime = _runtime(args)
    session = runtime.repository.get_session(args.review)
    readiness = runtime.assess_readiness(args.review)
    print(f"{args.review}: {session.status}")
    print(f"  process status: {readiness.process_status}")
    if readiness.unmet_prerequisites:
        print("  waiting on:")
        for item in readiness.unmet_prerequisites:
            print(f"    - {item}")
    if readiness.process_blockers:
        print("  blocked by:")
        for item in readiness.process_blockers:
            print(f"    - {item}")
    audit = runtime.repository.verify_audit(args.review)
    print(f"  audit chain:    {'valid' if audit['valid'] else 'INVALID'} ({audit['entries_verified']} entries)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="board", description="Convene and run a Review Board session."
    )
    parser.add_argument("--database", default=str(DEFAULT_DB), help="Review store path")
    sub = parser.add_subparsers(dest="command", required=True)

    seats = sub.add_parser("seats", help="Show agent seats and check independence")
    seats.add_argument("--seats", required=True)
    seats.set_defaults(func=cmd_seats)

    opened = sub.add_parser("open", help="Convene a review")
    opened.add_argument("--initiation", required=True)
    opened.set_defaults(func=cmd_open)

    evidence = sub.add_parser("evidence", help="Register a study proof bundle")
    evidence.add_argument("--review", required=True)
    evidence.add_argument("--bundle", required=True)
    evidence.add_argument("--actor", required=True)
    evidence.set_defaults(func=cmd_evidence)

    advance = sub.add_parser("advance", help="Move to the next lifecycle state")
    advance.add_argument("--review", required=True)
    advance.add_argument("--to", required=True)
    advance.add_argument("--actor", required=True)
    advance.add_argument("--metadata")
    advance.add_argument("--key")
    advance.set_defaults(func=cmd_advance)

    accept = sub.add_parser("accept", help="Accept seats and declare independence")
    accept.add_argument("--review", required=True)
    accept.add_argument("--signature", default="SIG")
    accept.set_defaults(func=cmd_accept)

    report = sub.add_parser("report", help="Submit one seat's report")
    report.add_argument("--review", required=True)
    report.add_argument("--report", required=True)
    report.set_defaults(func=cmd_report)

    challenges = sub.add_parser("challenges", help="Show challenge sheets")
    challenges.add_argument("--review", required=True)
    challenges.set_defaults(func=cmd_challenges)

    decide = sub.add_parser("decide", help="Compute the decision candidate")
    decide.add_argument("--review", required=True)
    decide.add_argument("--actor", required=True)
    decide.set_defaults(func=cmd_decide)

    ratify = sub.add_parser("ratify", help="Sign the decision")
    ratify.add_argument("--review", required=True)
    ratify.add_argument("--actor", required=True)
    ratify.add_argument("--signature", required=True)
    ratify.add_argument("--validator", help="Governance validator (four-eyes ratification)")
    ratify.add_argument("--validator-signature", help="Governance validator signature ref")
    ratify.add_argument(
        "--single-authority",
        action="store_true",
        help="Sign alone. Permitted only while the methodology is non-binding, and recorded as such.",
    )
    ratify.add_argument("--rationale", default="", help="Why a single authority signed")
    ratify.set_defaults(func=cmd_ratify)

    publish = sub.add_parser("publish", help="Publish the decision")
    publish.add_argument("--review", required=True)
    publish.add_argument("--actor", required=True)
    publish.set_defaults(func=cmd_publish)

    status = sub.add_parser("status", help="Where the review is")
    status.add_argument("--review", required=True)
    status.set_defaults(func=cmd_status)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except RBEError as exc:
        print(f"Refused [{exc.code}]: {exc}")
        if exc.details:
            print(f"  {json.dumps(exc.details, default=str)}")
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
