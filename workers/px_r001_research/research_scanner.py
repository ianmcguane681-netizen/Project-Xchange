from __future__ import annotations

from pathlib import Path

from project_exchange.database import add_changelog, connect, count_rows, utc_now
from project_exchange.eos import add_event, add_notification, worker_run
from project_exchange.ids import next_sequence_id


CLUSTER_KEYWORDS = {
    "Maintenance Communication": ["maintenance", "repair", "response", "update", "tenant"],
    "Billing & Payments": ["invoice", "billing", "payment", "charge", "refund"],
    "Scheduling": ["schedule", "appointment", "calendar", "booking", "delay"],
    "Support Operations": ["support", "ticket", "helpdesk", "response", "service"],
}


def run_market_scan(
    db_path: str | Path,
    market: str,
    source_text: str,
    company: str = "",
    source_url: str = "",
    source_type: str = "pasted_text",
) -> dict[str, object]:
    if not market or not source_text:
        raise ValueError("market and source_text are required")

    with worker_run(db_path, "PX-R001", input_ref=market) as activity:
        cluster = choose_cluster(source_text)
        complaint_summary = summarize_complaint(source_text, cluster)
        evidence_score = estimate_evidence_score(source_text, source_url)

        with connect(db_path) as connection:
            research_id = next_sequence_id("RES", count_rows(connection, "research_records"))
            created_at = utc_now()
            record = {
                "id": research_id,
                "market": market,
                "company": company,
                "source_url": source_url,
                "source_type": source_type,
                "source_text": source_text,
                "complaint_summary": complaint_summary,
                "workflow_cluster": cluster,
                "evidence_score": evidence_score,
                "pipeline_status": "pending_audit",
                "created_at": created_at,
                "recommended_next_step": "send_to_audit",
            }
            connection.execute(
                """
                INSERT INTO research_records
                (id, market, company, source_url, source_type, source_text, complaint_summary, workflow_cluster,
                 evidence_score, pipeline_status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["id"],
                    record["market"],
                    record["company"],
                    record["source_url"],
                    record["source_type"],
                    record["source_text"],
                    record["complaint_summary"],
                    record["workflow_cluster"],
                    record["evidence_score"],
                    record["pipeline_status"],
                    record["created_at"],
                ),
            )
            add_changelog(connection, research_id, "research", f"PX-R001 created research pack for {market}.")
        activity["output_ref"] = research_id
        activity["decision"] = "pending_audit"
        add_event(
            db_path,
            "ResearchCreated",
            "PX-R001",
            "Research pack created",
            "pending_audit",
            research_id,
            payload={"market": market, "workflow_cluster": cluster, "evidence_score": evidence_score},
        )
        add_notification(db_path, "research_created", f"Research pack created: {research_id}", research_id)
    return record


def create_research_record(
    db_path: str | Path,
    market: str,
    company: str,
    source_url: str,
    source_text: str,
    source_type: str,
) -> dict[str, object]:
    return run_market_scan(db_path, market, source_text, company, source_url, source_type)


def text_from_csv(raw: str) -> str:
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    return " ".join(lines[:30])


def extract_structured_research(source_text: str, source_url: str = "") -> dict[str, object]:
    cluster = choose_cluster(source_text)
    return {
        "complaint_summary": summarize_complaint(source_text, cluster),
        "workflow_cluster": cluster,
        "evidence_score": estimate_evidence_score(source_text, source_url),
    }


def choose_cluster(source_text: str) -> str:
    text = source_text.lower()
    best_cluster = "General Operations"
    best_count = 0
    for cluster, keywords in CLUSTER_KEYWORDS.items():
        count = sum(1 for keyword in keywords if keyword in text)
        if count > best_count:
            best_cluster = cluster
            best_count = count
    return best_cluster


def summarize_complaint(source_text: str, cluster: str) -> str:
    compact = " ".join(source_text.strip().split())
    first_sentence = compact.split(".")[0][:180]
    if not first_sentence:
        first_sentence = "Complaint signal requires more detail"
    return f"{cluster}: {first_sentence}."


def estimate_evidence_score(source_text: str, source_url: str = "") -> int:
    score = 35
    words = len(source_text.split())
    if words >= 20:
        score += 20
    if words >= 60:
        score += 15
    if source_url:
        score += 20
    if any(word in source_text.lower() for word in ["repeatedly", "multiple", "again", "always"]):
        score += 10
    return min(score, 100)


def list_research_records(db_path: str | Path) -> list[dict[str, object]]:
    with connect(db_path) as connection:
        rows = connection.execute("SELECT * FROM research_records ORDER BY created_at DESC").fetchall()
    return [dict(row) for row in rows]
