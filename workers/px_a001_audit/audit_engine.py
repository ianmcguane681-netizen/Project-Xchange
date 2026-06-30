from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from difflib import SequenceMatcher
import json
import re

from project_exchange.database import add_changelog, connect, count_rows, utc_now
from project_exchange.eos import add_event, add_notification, worker_run
from project_exchange.ids import next_sequence_id
from project_exchange.llm import get_llm_provider


class AuditDecision(StrEnum):
    APPROVED = "approved"
    NEEDS_EVIDENCE = "needs_evidence"
    DUPLICATE = "duplicate"
    REJECTED = "rejected"
    ARCHIVE = "archive"


REQUIRED_FIELDS = ["id", "market", "complaint_summary", "workflow_cluster", "evidence_score"]


def run_audit(db_path: str | Path, research_record: dict[str, object]) -> dict[str, object]:
    with worker_run(db_path, "PX-A001", input_ref=str(research_record.get("id") or "")) as activity:
        missing = [field for field in REQUIRED_FIELDS if not research_record.get(field)]
        evidence_checklist = build_evidence_checklist(research_record, missing)
        source_verified = evidence_checklist["source_present"]
        duplicate_risk = calculate_duplicate_risk(db_path, research_record)
        evidence_score = int(research_record.get("evidence_score") or 0)
        ai_reasoning = ai_audit_reasoning(research_record, evidence_checklist, duplicate_risk)
        confidence_score = calculate_confidence(evidence_score, evidence_checklist, duplicate_risk, missing, ai_reasoning)
        decision = choose_decision(confidence_score, source_verified, duplicate_risk, missing, ai_reasoning)

        with connect(db_path) as connection:
            audit_id = next_sequence_id("AUD", count_rows(connection, "audit_records"))
            created_at = utc_now()
            audit_notes = build_audit_notes(missing, evidence_checklist, duplicate_risk, ai_reasoning)
            connection.execute(
                """
                INSERT INTO audit_records
                (id, research_id, decision, confidence_score, duplicate_flag, source_verified, duplicate_risk,
                 evidence_checklist, reasoning_summary, audit_notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit_id,
                    research_record.get("id"),
                    decision.value,
                    confidence_score,
                    1 if duplicate_risk == "high" else 0,
                    1 if source_verified else 0,
                    duplicate_risk,
                    json.dumps(evidence_checklist),
                    audit_notes,
                    audit_notes,
                    created_at,
                ),
            )
            connection.execute(
                "UPDATE research_records SET pipeline_status = ? WHERE id = ?",
                ("approved_queue" if decision == AuditDecision.APPROVED else decision.value, research_record.get("id")),
            )
            connection.execute(
                """
                INSERT INTO audit_reasoning
                (audit_id, audit_score, evidence_matrix, source_quality, evidence_summary, supporting_sources,
                 contradictions, missing_evidence, duplicate_risk, bias_detection, confidence_explanation,
                 recommendation, raw_reasoning, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit_id,
                    confidence_score,
                    json.dumps(evidence_checklist, ensure_ascii=False),
                    "verified" if source_verified else "weak",
                    evidence_summary(research_record, evidence_checklist),
                    str(research_record.get("source_url") or "Manual/local source"),
                    str(ai_reasoning.get("contradictions") or "No explicit contradictions detected."),
                    ", ".join(missing) if missing else "None",
                    duplicate_risk,
                    str(ai_reasoning.get("bias") or "unknown"),
                    f"Confidence {confidence_score}: evidence {evidence_score}, duplicate risk {duplicate_risk}, missing fields {len(missing)}.",
                    str(ai_reasoning.get("recommendation") or decision.value),
                    json.dumps(ai_reasoning, ensure_ascii=False),
                    created_at,
                ),
            )
            add_changelog(connection, audit_id, "audit", f"PX-A001 audit completed with decision {decision.value}.")

        report = {
            "audit_id": audit_id,
            "research_id": research_record.get("id"),
            "decision": decision.value,
            "confidence_score": confidence_score,
            "source_verified": source_verified,
            "duplicate_risk": duplicate_risk,
            "evidence_checklist": evidence_checklist,
            "ai_reasoning": ai_reasoning,
            "reasoning_summary": audit_notes,
            "send_to_library": decision == AuditDecision.APPROVED,
            "created_at": created_at,
        }
        activity["output_ref"] = audit_id
        activity["decision"] = decision.value
        event_type = {
            AuditDecision.APPROVED: "AuditApproved",
            AuditDecision.REJECTED: "AuditRejected",
            AuditDecision.NEEDS_EVIDENCE: "AuditNeedsEvidence",
            AuditDecision.DUPLICATE: "AuditDuplicate",
            AuditDecision.ARCHIVE: "AuditArchived",
        }[decision]
        add_event(
            db_path,
            event_type,
            "PX-A001",
            "Audit completed",
            decision.value,
            audit_id,
            payload={"research_id": research_record.get("id"), "confidence_score": confidence_score},
        )
        add_notification(db_path, "audit_completed", f"Audit completed: {audit_id} ({decision.value})", audit_id)
    return report


def calculate_duplicate_risk(db_path: str | Path, research_record: dict[str, object]) -> str:
    summary = str(research_record.get("complaint_summary") or "")
    market = str(research_record.get("market") or "")
    current_id = str(research_record.get("id") or "")
    if not summary:
        return "low"

    with connect(db_path) as connection:
        rows = connection.execute(
            "SELECT id, market, complaint_summary FROM research_records WHERE id != ?",
            (current_id,),
        ).fetchall()

    current_tokens = token_set(summary)
    highest = 0.0
    for row in rows:
        if row["market"] != market:
            continue
        candidate = str(row["complaint_summary"])
        sequence_ratio = SequenceMatcher(None, summary.lower(), candidate.lower()).ratio()
        candidate_tokens = token_set(candidate)
        token_overlap = len(current_tokens & candidate_tokens) / max(len(current_tokens | candidate_tokens), 1)
        highest = max(highest, (sequence_ratio * 0.65) + (token_overlap * 0.35))

    if highest >= 0.82:
        return "high"
    if highest >= 0.62:
        return "medium"
    return "low"


def calculate_confidence(
    evidence_score: int,
    evidence_checklist: dict[str, bool],
    duplicate_risk: str,
    missing_fields: list[str],
    ai_reasoning: dict[str, object] | None = None,
) -> int:
    confidence = min(max(evidence_score, 0), 100)
    confidence += 8 if evidence_checklist["source_present"] else -18
    confidence += 5 if evidence_checklist["clear_workflow"] else -8
    confidence += 4 if evidence_checklist["commercial_relevance"] else -6
    confidence += 4 if evidence_checklist["specific_complaint"] else -8
    confidence -= 25 if duplicate_risk == "high" else 8 if duplicate_risk == "medium" else 0
    confidence -= len(missing_fields) * 12
    if ai_reasoning:
        confidence = round((confidence * 0.7) + (int(ai_reasoning.get("confidence") or confidence) * 0.3))
    return min(max(confidence, 0), 100)


def choose_decision(
    confidence_score: int,
    source_verified: bool,
    duplicate_risk: str,
    missing_fields: list[str],
    ai_reasoning: dict[str, object] | None = None,
) -> AuditDecision:
    if missing_fields:
        return AuditDecision.REJECTED
    if duplicate_risk == "high":
        return AuditDecision.DUPLICATE
    if ai_reasoning and ai_reasoning.get("recommendation") in {"reject", "needs_review"} and confidence_score < 75:
        return AuditDecision.NEEDS_EVIDENCE
    if not source_verified or confidence_score < 60:
        return AuditDecision.NEEDS_EVIDENCE
    return AuditDecision.APPROVED


def build_evidence_checklist(research_record: dict[str, object], missing: list[str]) -> dict[str, bool]:
    summary = str(research_record.get("complaint_summary") or "")
    workflow = str(research_record.get("workflow_cluster") or "")
    market = str(research_record.get("market") or "")
    return {
        "required_fields_complete": not missing,
        "source_present": bool(research_record.get("source_url")),
        "clear_workflow": bool(workflow and workflow != "General Operations"),
        "specific_complaint": len(summary.split()) >= 6,
        "commercial_relevance": bool(market and int(research_record.get("evidence_score") or 0) >= 50),
    }


def evidence_summary(research_record: dict[str, object], evidence_checklist: dict[str, bool]) -> str:
    passed = [key for key, value in evidence_checklist.items() if value]
    failed = [key for key, value in evidence_checklist.items() if not value]
    return (
        f"Research {research_record.get('id')} in {research_record.get('market') or 'unknown market'} "
        f"passed {', '.join(passed) or 'no checks'}; failed {', '.join(failed) or 'no checks'}."
    )


def token_set(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 3}


def ai_audit_reasoning(
    research_record: dict[str, object],
    evidence_checklist: dict[str, bool],
    duplicate_risk: str,
) -> dict[str, object]:
    provider = get_llm_provider()
    payload = {
        **research_record,
        "evidence_checklist": evidence_checklist,
        "duplicate_risk": duplicate_risk,
        "source_count": len(str(research_record.get("source_text") or "").split("\n")),
    }
    return provider.reason("Audit research credibility, source quality, bias, confidence and recommendation.", payload)


def build_audit_notes(
    missing: list[str],
    evidence_checklist: dict[str, bool],
    duplicate_risk: str,
    ai_reasoning: dict[str, object] | None = None,
) -> str:
    notes = []
    if missing:
        notes.append(f"Missing required fields: {', '.join(missing)}.")
    notes.append("Source present." if evidence_checklist["source_present"] else "Source missing or not verified.")
    if evidence_checklist["clear_workflow"]:
        notes.append("Workflow cluster is clear.")
    if evidence_checklist["commercial_relevance"]:
        notes.append("Commercial relevance is plausible.")
    notes.append(f"Duplicate risk is {duplicate_risk}.")
    if ai_reasoning:
        notes.append(
            f"AI reasoning: credibility {ai_reasoning.get('credibility')}, "
            f"source quality {ai_reasoning.get('source_quality')}, "
            f"bias {ai_reasoning.get('bias')}, recommendation {ai_reasoning.get('recommendation')}."
        )
    return " ".join(notes)


def list_audit_records(db_path: str | Path) -> list[dict[str, object]]:
    with connect(db_path) as connection:
        rows = connection.execute("SELECT * FROM audit_records ORDER BY created_at DESC").fetchall()
    return [dict(row) for row in rows]


def update_audit_decision(
    db_path: str | Path,
    audit_id: str,
    decision: AuditDecision,
    note: str = "",
) -> dict[str, object]:
    with connect(db_path) as connection:
        row = connection.execute("SELECT * FROM audit_records WHERE id = ?", (audit_id,)).fetchone()
        if row is None:
            raise ValueError(f"Audit not found: {audit_id}")
        notes = " ".join(part for part in [row["audit_notes"], note] if part)
        connection.execute(
            """
            UPDATE audit_records
            SET decision = ?, audit_notes = ?, reasoning_summary = ?
            WHERE id = ?
            """,
            (decision.value, notes, notes, audit_id),
        )
        connection.execute(
            "UPDATE research_records SET pipeline_status = ? WHERE id = ?",
            ("approved_queue" if decision == AuditDecision.APPROVED else decision.value, row["research_id"]),
        )
        add_changelog(connection, audit_id, "audit", f"Audit decision manually updated to {decision.value}.")
    add_notification(db_path, "audit_completed", f"Audit decision updated: {audit_id} ({decision.value})", audit_id)
    add_event(
        db_path,
        "AuditDecisionUpdated",
        "PX-A001",
        "Audit decision manually updated",
        decision.value,
        audit_id,
    )
    return {
        "audit_id": audit_id,
        "research_id": row["research_id"],
        "decision": decision.value,
        "confidence_score": row["confidence_score"],
        "source_verified": bool(row["source_verified"]),
        "duplicate_risk": row["duplicate_risk"] or ("high" if row["duplicate_flag"] else "low"),
        "reasoning_summary": notes,
        "send_to_library": decision == AuditDecision.APPROVED,
        "created_at": row["created_at"],
    }
