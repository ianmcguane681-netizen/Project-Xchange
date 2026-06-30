from __future__ import annotations

from pathlib import Path
import json

from project_exchange.database import add_changelog, connect, count_rows, utc_now
from project_exchange.eos import add_event, add_notification, worker_run
from project_exchange.ids import next_sequence_id


def store_approved_record(
    db_path: str | Path,
    audit_report: dict[str, object],
    research_record: dict[str, object],
) -> dict[str, object]:
    if audit_report.get("decision") != "approved" or not audit_report.get("send_to_library"):
        raise ValueError("Only approved audit reports can be stored in the Library")

    with worker_run(db_path, "PX-L001", input_ref=str(audit_report.get("audit_id") or "")) as activity:
        title = f"{research_record.get('market', 'Unknown Market')} - {research_record.get('workflow_cluster', 'Workflow')}"
        summary = str(research_record.get("complaint_summary") or "")
        category = str(research_record.get("workflow_cluster") or "Uncategorized")
        tags = build_tags(research_record)

        with connect(db_path) as connection:
            library_id = next_sequence_id("LIB", count_rows(connection, "library_records"))
            version = f"v1.0.{count_rows(connection, 'library_records') + 1}"
            now = utc_now()
            audit_history = json.dumps([audit_report.get("audit_id")])
            connection.execute(
                """
                INSERT INTO library_records
                (id, source_audit_id, title, category, tags, summary, canonical_status, version,
                 audit_history, origin_research_id, researched_by, audited_by, prompt_id, related_companies,
                 related_industries, related_opportunities, worker_history, milestone_refs, source_tracking,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    library_id,
                    audit_report.get("audit_id"),
                    title,
                    category,
                    ",".join(tags),
                    summary,
                    "canonical",
                    version,
                    audit_history,
                    research_record.get("id") or audit_report.get("research_id") or "",
                    "PX-R001",
                    "PX-A001",
                    str(research_record.get("prompt_id") or ""),
                    str(research_record.get("company") or ""),
                    str(research_record.get("market") or ""),
                    json.dumps([summary], ensure_ascii=False),
                    json.dumps(["PX-R001", "PX-A001", "PX-L001"], ensure_ascii=False),
                    str(research_record.get("milestone_ref") or ""),
                    json.dumps({"source_url": research_record.get("source_url") or "", "source_type": research_record.get("source_type") or ""}, ensure_ascii=False),
                    now,
                    now,
                ),
            )
            connection.execute(
                "UPDATE research_records SET pipeline_status = ? WHERE id = ?",
                ("stored_in_library", research_record.get("id")),
            )
            changelog = f"Added approved {category} record from {audit_report.get('audit_id')}."
            add_changelog(connection, library_id, "library", changelog)

        activity["output_ref"] = library_id
        activity["decision"] = "stored"
        add_event(
            db_path,
            "LibraryStored",
            "PX-L001",
            "Library record stored",
            "stored",
            library_id,
            payload={"source_audit_id": audit_report.get("audit_id"), "category": category, "tags": tags},
        )
        add_notification(db_path, "library_updated", f"Library updated: {library_id}", library_id)
        return {
            "library_id": library_id,
            "source_audit_id": audit_report.get("audit_id"),
            "status": "stored",
            "version": version,
            "category": category,
            "tags": tags,
            "changelog": changelog,
            "created_at": now,
        }


def build_tags(research_record: dict[str, object]) -> list[str]:
    tags = {
        str(research_record.get("market") or "").strip().lower().replace(" ", "-"),
        str(research_record.get("workflow_cluster") or "").strip().lower().replace(" ", "-"),
    }
    return sorted(tag for tag in tags if tag)


def list_library_records(db_path: str | Path) -> list[dict[str, object]]:
    with connect(db_path) as connection:
        rows = connection.execute("SELECT * FROM library_records ORDER BY created_at DESC").fetchall()
    return [dict(row) for row in rows]


def search_library_records(
    db_path: str | Path,
    query: str = "",
    category: str = "",
    tag: str = "",
    worker: str = "",
    company: str = "",
    market: str = "",
    source: str = "",
    min_confidence: int | None = None,
) -> list[dict[str, object]]:
    records = list_library_records(db_path)
    query_lower = query.lower().strip()
    category_lower = category.lower().strip()
    tag_lower = tag.lower().strip()
    worker_lower = worker.lower().strip()
    company_lower = company.lower().strip()
    market_lower = market.lower().strip()
    source_lower = source.lower().strip()
    filtered = []
    for record in records:
        haystack = " ".join(
            str(record.get(field) or "")
            for field in [
                "title",
                "category",
                "tags",
                "summary",
                "canonical_status",
                "version",
                "related_companies",
                "related_industries",
                "related_opportunities",
                "source_tracking",
                "worker_history",
            ]
        ).lower()
        if query_lower and query_lower not in haystack:
            continue
        if category_lower and category_lower != str(record.get("category") or "").lower():
            continue
        if tag_lower and tag_lower not in str(record.get("tags") or "").lower():
            continue
        if worker_lower and worker_lower not in haystack:
            continue
        if company_lower and company_lower not in haystack:
            continue
        if market_lower and market_lower not in haystack:
            continue
        if source_lower and source_lower not in str(record.get("source_audit_id") or "").lower():
            continue
        if min_confidence is not None and min_confidence > 0:
            # Library records do not yet denormalize confidence; keep the filter API stable for later.
            pass
        filtered.append(record)
    return filtered


def approved_audit_queue(db_path: str | Path) -> list[dict[str, object]]:
    with connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT audit_records.*
            FROM audit_records
            LEFT JOIN library_records ON library_records.source_audit_id = audit_records.id
            WHERE audit_records.decision = 'approved'
              AND library_records.id IS NULL
            ORDER BY audit_records.created_at DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]
