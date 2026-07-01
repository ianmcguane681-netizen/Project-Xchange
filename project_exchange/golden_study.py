from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

from project_exchange.database import connect, count_rows, row_to_dict, utc_now
from project_exchange.eos import add_event, add_notification
from project_exchange.ids import next_sequence_id
from project_exchange.provider_base import ProviderResult
from project_exchange.provider_modules.newsapi_provider import NewsAPIProvider
from project_exchange.provider_modules.tavily_serpapi_provider import SerpAPISearchProvider, TavilySearchProvider
from project_exchange.provider_status import provider_ready_for_research


DEFAULT_STUDY_ID = "GS-001"
ENGINEERING_READY_OCI = 85
PROVENANCE_TABLES = ["studies", "study_signals", "study_findings", "finding_audits", "opportunity_records", "study_briefs"]
RUN_SCOPED_TABLES = ["study_signals", "study_findings", "finding_audits", "opportunity_records", "study_briefs"]

STAKEHOLDER_KEYWORDS = {
    "Tenants": ["tenant", "renters", "resident"],
    "Property managers": ["property manager", "manager", "portfolio"],
    "Housing associations": ["housing association", "social housing"],
    "Facilities managers": ["facilities", "facility"],
    "Estate management companies": ["estate management", "estate manager"],
    "Condo / HOA managers": ["hoa", "condo", "strata"],
    "Commercial property managers": ["commercial", "office", "retail unit"],
    "Letting agents": ["letting agent", "lettings", "leasing"],
    "Property owners": ["landlord", "owner"],
    "Maintenance contractors": ["contractor", "maintenance team", "repair vendor"],
}

GS001_REAL_EVIDENCE_QUERIES = [
    "tenant complaint maintenance request no response property management",
    "apartment resident complaints maintenance not fixed property manager",
    "property management company complaints maintenance communication",
    "HOA management complaints maintenance communication",
    "property manager maintenance request delayed tenant complaint",
    "rental property maintenance complaints poor communication",
]

VALID_COMPLAINT_RELEVANCE = {"complaint", "operational_pain", "workflow_inefficiency"}
PRODUCTION_ELIGIBLE_CLASSIFICATIONS = {"verified_complaint", "operational_pain", "workflow_inefficiency"}
SOURCE_TRUST_SCORES = {
    "government": 100,
    "court": 100,
    "ombudsman": 98,
    "consumer_review": 95,
    "verified_review_platform": 90,
    "news": 85,
    "industry_association": 80,
    "research": 80,
    "forum": 70,
    "community": 60,
    "social_media": 60,
    "facebook_group": 40,
    "vendor": 20,
    "marketing": 10,
    "unknown": 0,
}
PAIN_KEYWORDS = [
    "complaint",
    "complain",
    "complains",
    "issue",
    "problem",
    "poor",
    "slow",
    "delayed",
    "no response",
    "unresolved",
    "waiting",
    "broken",
    "repair",
    "maintenance request",
    "frustration",
    "dispute",
    "bad service",
    "ignored",
    "lack of communication",
    "not updated",
]
PROPERTY_MAINTENANCE_CONTEXT_KEYWORDS = [
    "tenant",
    "resident",
    "apartment",
    "landlord",
    "property manager",
    "property management",
    "hoa",
    "maintenance",
    "repair",
    "work order",
    "rental",
    "multifamily",
]

CATEGORY_KEYWORDS = {
    "Maintenance issues": ["maintenance", "repair", "contractor", "work order"],
    "Tenant communication issues": ["communication", "message", "tenant", "update", "response"],
    "Accounting / payment issues": ["payment", "accounting", "invoice", "rent", "arrears"],
    "Reporting problems": ["report", "dashboard", "analytics", "export"],
    "Compliance problems": ["compliance", "regulation", "inspection", "certificate"],
    "Missing integrations": ["integration", "sync", "api", "spreadsheet"],
    "Expensive software complaints": ["expensive", "pricing", "cost", "subscription"],
    "Feature requests": ["feature", "wish", "request", "missing"],
    "Repetitive manual tasks": ["manual", "spreadsheet", "copy", "repetitive"],
    "Poor customer experiences": ["slow", "poor", "bad", "frustrating", "support"],
}

COUNTRY_HINTS = [
    "Ireland",
    "United Kingdom",
    "United States",
    "Canada",
    "Australia",
    "New Zealand",
    "Germany",
    "France",
    "Spain",
]


def get_or_create_default_study(db_path: str | Path) -> dict[str, object]:
    study = get_study(db_path, DEFAULT_STUDY_ID)
    if study:
        get_active_study_run(db_path, DEFAULT_STUDY_ID)
        return study
    return create_study(
        db_path,
        DEFAULT_STUDY_ID,
        "Global Property Management Golden Study",
        "Property Management",
        status="Active",
        scope="Global",
        countries="Global",
        stakeholders=", ".join(STAKEHOLDER_KEYWORDS),
        objective="Find verified, traceable market opportunities backed by repeated complaints and evidence.",
    )


def create_study(
    db_path: str | Path,
    study_id: str,
    name: str,
    market: str,
    scope: str = "",
    countries: str = "",
    stakeholders: str = "",
    objective: str = "",
    status: str = "Active",
    notes: str = "",
    data_origin: str = "demo",
    study_mode: str = "demo",
    production_confirmed: bool = False,
) -> dict[str, object]:
    mode = study_mode if study_mode in {"demo", "production"} else "demo"
    if mode == "production" and not production_confirmed:
        raise ValueError("Production GS-001 creation requires explicit confirmation.")
    if mode == "production" and data_origin == "demo":
        data_origin = "manual"
    existing_study = get_study(db_path, study_id)
    if existing_study:
        with connect(db_path) as connection:
            active = connection.execute(
                "SELECT study_mode FROM study_runs WHERE study_id = ? AND status = 'active' ORDER BY created_at DESC LIMIT 1",
                (study_id,),
            ).fetchone()
        if active and active["study_mode"] != mode:
            raise ValueError("Use switch_study_run_mode to change GS-001 run mode.")
    provenance = provenance_values(data_origin, "PX-H001")
    with connect(db_path) as connection:
        now = utc_now()
        connection.execute(
            """
            INSERT INTO studies
            (id, name, market, scope, countries, stakeholders, objective, status, started_at, lead_worker,
             research_worker, audit_worker, library_worker, notes, study_mode, data_origin, verification_status, is_demo,
             source_confidence, created_by_worker, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                market = excluded.market,
                scope = excluded.scope,
                countries = excluded.countries,
                stakeholders = excluded.stakeholders,
                objective = excluded.objective,
                status = excluded.status,
                notes = excluded.notes,
                study_mode = excluded.study_mode,
                data_origin = excluded.data_origin,
                verification_status = excluded.verification_status,
                is_demo = excluded.is_demo,
                last_updated = excluded.last_updated
            """,
            (
                study_id,
                name,
                market,
                scope,
                countries,
                stakeholders,
                objective,
                status,
                now,
                "PX-H001",
                "PX-R001",
                "PX-A001",
                "PX-L001",
                notes,
                mode,
                provenance["data_origin"],
                provenance["verification_status"],
                1 if provenance["is_demo"] else 0,
                provenance["source_confidence"],
                provenance["created_by_worker"],
                now,
            ),
        )
    add_event(db_path, "StudyCreated", "PX-H001", "Golden Study created", status, study_id)
    if not get_active_study_run(db_path, study_id):
        create_study_run(db_path, study_id, mode, provenance["data_origin"], "Initial Golden Study run.")
    return get_study(db_path, study_id) or {}


def get_study(db_path: str | Path, study_id: str) -> dict[str, object] | None:
    with connect(db_path) as connection:
        row = connection.execute("SELECT * FROM studies WHERE id = ?", (study_id,)).fetchone()
    return row_to_dict(row) if row else None


def list_studies(db_path: str | Path) -> list[dict[str, object]]:
    with connect(db_path) as connection:
        rows = connection.execute("SELECT * FROM studies ORDER BY started_at DESC").fetchall()
    return [row_to_dict(row) for row in rows]


def list_study_runs(db_path: str | Path, study_id: str = DEFAULT_STUDY_ID) -> list[dict[str, object]]:
    with connect(db_path) as connection:
        rows = connection.execute(
            "SELECT * FROM study_runs WHERE study_id = ? ORDER BY created_at DESC",
            (study_id,),
        ).fetchall()
    return [row_to_dict(row) for row in rows]


def get_active_study_run(db_path: str | Path, study_id: str = DEFAULT_STUDY_ID) -> dict[str, object] | None:
    with connect(db_path) as connection:
        row = connection.execute(
            "SELECT * FROM study_runs WHERE study_id = ? AND status = 'active' ORDER BY created_at DESC LIMIT 1",
            (study_id,),
        ).fetchone()
    if not row:
        study = get_study(db_path, study_id)
        if not study:
            return None
        return create_study_run(
            db_path,
            study_id,
            str(study.get("study_mode") or "demo"),
            str(study.get("data_origin") or "demo"),
            "Auto-created active study run.",
        )
    run = row_to_dict(row)
    assign_legacy_records_to_runs(db_path, study_id, str(run["id"]))
    return run


def create_study_run(
    db_path: str | Path,
    study_id: str,
    study_mode: str,
    data_origin: str,
    notes: str = "",
) -> dict[str, object]:
    mode = study_mode if study_mode in {"demo", "production"} else "demo"
    origin = normalize_data_origin(data_origin)
    if mode == "production" and origin == "demo":
        origin = "manual"
    provenance = provenance_values(origin, "PX-H001")
    with connect(db_path) as connection:
        active = connection.execute(
            "SELECT id FROM study_runs WHERE study_id = ? AND status = 'active'",
            (study_id,),
        ).fetchone()
        if active:
            raise ValueError(f"Study {study_id} already has an active run: {active['id']}")
        run_id = next_sequence_id("GSR", count_rows(connection, "study_runs"))
        now = utc_now()
        connection.execute(
            """
            INSERT INTO study_runs
            (id, study_id, study_mode, status, created_at, data_origin, verification_status, is_demo, notes, created_by_worker)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                study_id,
                mode,
                "active",
                now,
                provenance["data_origin"],
                provenance["verification_status"],
                1 if provenance["is_demo"] else 0,
                notes,
                "PX-H001",
            ),
        )
    add_event(db_path, "StudyRunCreated", "PX-H001", "Golden Study run created", mode, run_id)
    return get_study_run(db_path, run_id)


def get_study_run(db_path: str | Path, run_id: str) -> dict[str, object]:
    with connect(db_path) as connection:
        row = connection.execute("SELECT * FROM study_runs WHERE id = ?", (run_id,)).fetchone()
    if row is None:
        raise ValueError(f"Study run not found: {run_id}")
    return row_to_dict(row)


def close_active_study_run(db_path: str | Path, study_id: str, reason: str = "") -> dict[str, object] | None:
    run = get_active_study_run(db_path, study_id)
    if not run:
        return None
    with connect(db_path) as connection:
        connection.execute(
            "UPDATE study_runs SET status = 'closed', closed_at = ?, notes = ? WHERE id = ?",
            (utc_now(), reason or str(run.get("notes") or ""), run["id"]),
        )
    add_event(db_path, "StudyRunClosed", "PX-H001", "Golden Study run closed", reason, str(run["id"]))
    return get_study_run(db_path, str(run["id"]))


def switch_study_run_mode(
    db_path: str | Path,
    study_id: str,
    target_mode: str,
    production_confirmed: bool = False,
) -> dict[str, object]:
    mode = target_mode if target_mode in {"demo", "production"} else "demo"
    if mode == "production" and not production_confirmed:
        raise ValueError("Production GS-001 creation requires explicit confirmation.")
    active = get_active_study_run(db_path, study_id)
    if active and active["study_mode"] == mode:
        return active
    if active:
        if active["study_mode"] == "demo":
            archive_run_records(db_path, study_id, str(active["id"]), demo_only=True)
        close_active_study_run(db_path, study_id, f"Switched to {mode} run.")
    run = create_study_run(
        db_path,
        study_id,
        mode,
        "manual" if mode == "production" else "demo",
        f"Active {mode} run for {study_id}.",
    )
    with connect(db_path) as connection:
        connection.execute(
            """
            UPDATE studies
            SET study_mode = ?, data_origin = ?, verification_status = ?, is_demo = ?, last_updated = ?
            WHERE id = ?
            """,
            (
                mode,
                "manual" if mode == "production" else "demo",
                "pending_review" if mode == "production" else "unverified",
                0 if mode == "production" else 1,
                utc_now(),
                study_id,
            ),
        )
    return run


def archive_run_records(db_path: str | Path, study_id: str, study_run_id: str, demo_only: bool = True) -> list[dict[str, object]]:
    archived = []
    with connect(db_path) as connection:
        for table_name in RUN_SCOPED_TABLES:
            demo_clause = "AND is_demo = 1" if demo_only else ""
            rows = connection.execute(
                f"""
                SELECT id FROM {table_name}
                WHERE study_id = ? AND study_run_id = ? AND status != 'archived'
                {demo_clause}
                """,
                (study_id, study_run_id),
            ).fetchall()
            archived.extend({"table": table_name, "id": row["id"]} for row in rows)
    for row in archived:
        archive_record(db_path, str(row["table"]), str(row["id"]))
    return archived


def archive_all_demo_data(db_path: str | Path, study_id: str = DEFAULT_STUDY_ID) -> dict[str, object]:
    """Archive demo records and demo runs while preserving traceability."""
    archived: list[dict[str, object]] = []
    with connect(db_path) as connection:
        for table_name in RUN_SCOPED_TABLES:
            rows = connection.execute(
                f"""
                SELECT id FROM {table_name}
                WHERE study_id = ? AND is_demo = 1 AND status != 'archived'
                """,
                (study_id,),
            ).fetchall()
            archived.extend({"table": table_name, "id": row["id"]} for row in rows)
    for row in archived:
        archive_record(db_path, str(row["table"]), str(row["id"]))

    now = utc_now()
    with connect(db_path) as connection:
        demo_runs = connection.execute(
            """
            SELECT id, status FROM study_runs
            WHERE study_id = ? AND study_mode = 'demo' AND status != 'archived'
            """,
            (study_id,),
        ).fetchall()
        for run in demo_runs:
            connection.execute(
                """
                UPDATE study_runs
                SET status = 'archived', closed_at = COALESCE(closed_at, ?), notes = ?
                WHERE id = ?
                """,
                (now, "Demo data archived through Golden Study cleanup action.", run["id"]),
            )
        counts = {
            table_name: sum(1 for row in archived if row["table"] == table_name)
            for table_name in RUN_SCOPED_TABLES
        }
    add_event(
        db_path,
        "DemoDataArchived",
        "PX-H001",
        "Golden Study demo data archived instead of deleted",
        json.dumps(counts, ensure_ascii=False),
        study_id,
    )
    return {
        "study_id": study_id,
        "status": "archived",
        "records_archived": len(archived),
        "runs_archived": len(demo_runs),
        "counts": counts,
    }


def archive_current_production_run_and_start_fresh(db_path: str | Path, study_id: str = DEFAULT_STUDY_ID) -> dict[str, object]:
    active = get_active_study_run(db_path, study_id)
    if not active or active.get("study_mode") != "production":
        raise ValueError("Archive-and-reset is only available for an active production run.")
    run_id = str(active["id"])
    archived_records = archive_run_records(db_path, study_id, run_id, demo_only=False)
    note = "Archived before evidence-quality rerun. Records preserved for traceability under original study_run_id."
    with connect(db_path) as connection:
        connection.execute(
            "UPDATE study_runs SET status = 'archived', closed_at = ?, notes = ? WHERE id = ?",
            (utc_now(), note, run_id),
        )
    new_run = create_study_run(
        db_path,
        study_id,
        "production",
        "manual",
        "Clean production run started after evidence-quality reset.",
    )
    with connect(db_path) as connection:
        connection.execute(
            """
            UPDATE studies
            SET study_mode = 'production', data_origin = 'manual', verification_status = 'pending_review',
                is_demo = 0, last_updated = ?
            WHERE id = ?
            """,
            (utc_now(), study_id),
        )
    add_event(db_path, "ProductionRunArchived", "PX-H001", "Current production run archived. New clean production run started.", run_id, study_id)
    return {
        "status": "completed",
        "message": "Current production run archived. New clean production run started.",
        "archived_run_id": run_id,
        "new_run_id": new_run["id"],
        "records_archived": len(archived_records),
        "archived_records": archived_records,
    }


def delete_archived_demo_data(db_path: str | Path, study_id: str = DEFAULT_STUDY_ID) -> dict[str, object]:
    deleted: dict[str, int] = {}
    with connect(db_path) as connection:
        for table_name in RUN_SCOPED_TABLES:
            rows = connection.execute(
                f"SELECT id FROM {table_name} WHERE study_id = ? AND is_demo = 1 AND status = 'archived'",
                (study_id,),
            ).fetchall()
            deleted[table_name] = len(rows)
            connection.execute(
                f"DELETE FROM {table_name} WHERE study_id = ? AND is_demo = 1 AND status = 'archived'",
                (study_id,),
            )
        runs = connection.execute(
            "SELECT id FROM study_runs WHERE study_id = ? AND is_demo = 1 AND status = 'archived'",
            (study_id,),
        ).fetchall()
        deleted["study_runs"] = len(runs)
        connection.execute(
            "DELETE FROM study_runs WHERE study_id = ? AND is_demo = 1 AND status = 'archived'",
            (study_id,),
        )
    add_event(db_path, "ArchivedDemoDataDeleted", "PX-H001", "Archived demo data deleted by admin action.", str(sum(deleted.values())), study_id)
    return {"status": "completed", "deleted": deleted, "records_deleted": sum(deleted.values())}


def assign_legacy_records_to_runs(db_path: str | Path, study_id: str, active_run_id: str) -> None:
    demo_run_id = ensure_demo_history_run(db_path, study_id)
    with connect(db_path) as connection:
        for table_name in RUN_SCOPED_TABLES:
            columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()}
            if "study_run_id" not in columns:
                continue
            connection.execute(
                f"UPDATE {table_name} SET study_run_id = ? WHERE study_id = ? AND study_run_id IS NULL AND is_demo = 1",
                (demo_run_id, study_id),
            )
            connection.execute(
                f"UPDATE {table_name} SET study_run_id = ? WHERE study_id = ? AND study_run_id IS NULL AND COALESCE(is_demo, 0) = 0",
                (active_run_id, study_id),
            )


def ensure_demo_history_run(db_path: str | Path, study_id: str) -> str:
    with connect(db_path) as connection:
        row = connection.execute(
            "SELECT id FROM study_runs WHERE study_id = ? AND study_mode = 'demo' ORDER BY created_at ASC LIMIT 1",
            (study_id,),
        ).fetchone()
        if row:
            return str(row["id"])
        run_id = next_sequence_id("GSR", count_rows(connection, "study_runs"))
        now = utc_now()
        connection.execute(
            """
            INSERT INTO study_runs
            (id, study_id, study_mode, status, created_at, data_origin, verification_status, is_demo, notes, created_by_worker)
            VALUES (?, ?, 'demo', 'archived', ?, 'demo', 'unverified', 1, ?, 'PX-H001')
            """,
            (run_id, study_id, now, "Legacy demo/history run."),
        )
    return run_id


def create_signal(
    db_path: str | Path,
    raw_text: str,
    study_id: str = DEFAULT_STUDY_ID,
    source_url: str = "",
    source_name: str = "",
    source_type: str = "manual",
    source_date: str = "",
    country: str = "",
    stakeholder_type: str = "",
    company_product: str = "",
    data_origin: str = "demo",
    source_confidence: float | None = None,
) -> dict[str, object]:
    if not raw_text.strip():
        raise ValueError("Signal raw_text is required")
    study = get_or_create_default_study(db_path) if study_id == DEFAULT_STUDY_ID else get_study(db_path, study_id)
    if not study:
        raise ValueError(f"Study not found: {study_id}")
    active_run = get_active_study_run(db_path, study_id)
    if not active_run:
        raise ValueError(f"Study has no active run: {study_id}")
    origin = normalize_data_origin(data_origin)
    if source_url.strip() and origin == "demo":
        origin = "manual"
    if origin != "demo":
        if origin == "demo":
            raise ValueError("Production evidence cannot use demo data_origin.")
        if not (source_url.strip() or source_name.strip()):
            raise ValueError("Non-demo evidence requires a Source URL or Source name.")
        quality = evidence_quality_profile(f"{source_name}\n{raw_text}")
        if not quality["accepted_complaint_evidence"]:
            raise ValueError("Production evidence must describe a real complaint, operational pain, or workflow inefficiency in property maintenance context.")
        if str(active_run["study_mode"]) != "production":
            raise ValueError("Start a production run before adding production evidence.")
        if demo_records_count(db_path, study_id, str(active_run["id"])) > 0:
            raise ValueError("Archive demo records before adding production evidence.")
    elif str(active_run["study_mode"]) == "production":
        raise ValueError("Production studies cannot contain demo records.")
    elif non_demo_records_count(db_path, study_id, str(active_run["id"])) > 0:
        raise ValueError("Demo evidence cannot be added after production evidence has started.")
    enriched = enrich_signal(raw_text, country, stakeholder_type, company_product)
    provenance = provenance_values(origin, "PX-R001", source_confidence)
    if origin != "demo":
        provenance["verification_status"] = "pending_review"
        provenance["is_demo"] = False
    with connect(db_path) as connection:
        signal_id = next_sequence_id("SIG", count_rows(connection, "study_signals"))
        now = utc_now()
        connection.execute(
            """
            INSERT INTO study_signals
            (id, study_id, study_run_id, source_url, source_name, source_type, source_date, country, stakeholder_type,
             company_product, raw_text, complaint_category, summary, sentiment, evidence_strength,
             duplicate_group, status, created_at, data_origin, verification_status, is_demo, source_confidence,
             created_by_worker, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                signal_id,
                study_id,
                active_run["id"],
                source_url,
                source_name,
                source_type,
                source_date,
                enriched["country"],
                enriched["stakeholder_type"],
                enriched["company_product"],
                raw_text,
                enriched["complaint_category"],
                enriched["summary"],
                enriched["sentiment"],
                enriched["evidence_strength"],
                enriched["duplicate_group"],
                "active",
                now,
                provenance["data_origin"],
                provenance["verification_status"],
                1 if provenance["is_demo"] else 0,
                provenance["source_confidence"],
                provenance["created_by_worker"],
                now,
            ),
        )
    add_event(db_path, "StudySignalCreated", "PX-R001", "PX-R001 created study signal", study_id, signal_id)
    return get_signal(db_path, signal_id)


def get_signal(db_path: str | Path, signal_id: str) -> dict[str, object]:
    with connect(db_path) as connection:
        row = connection.execute("SELECT * FROM study_signals WHERE id = ?", (signal_id,)).fetchone()
    if row is None:
        raise ValueError(f"Signal not found: {signal_id}")
    return row_to_dict(row)


def list_signals(
    db_path: str | Path,
    study_id: str = DEFAULT_STUDY_ID,
    study_run_id: str | None = None,
    include_archived: bool = False,
    include_demo: bool = False,
) -> list[dict[str, object]]:
    run_id = study_run_id or str((get_active_study_run(db_path, study_id) or {}).get("id") or "")
    where, params = run_filter(study_id, run_id, include_archived, include_demo)
    with connect(db_path) as connection:
        rows = connection.execute(f"SELECT * FROM study_signals WHERE {where} ORDER BY created_at DESC", params).fetchall()
    return [row_to_dict(row) for row in rows]


def enrich_signal(raw_text: str, country: str, stakeholder_type: str, company_product: str) -> dict[str, object]:
    text = raw_text.strip()
    category = consolidate_category(text, choose_from_keywords(text, CATEGORY_KEYWORDS, "Poor customer experiences"))
    inferred_country = country or infer_country(text)
    inferred_stakeholder = stakeholder_type or choose_from_keywords(text, STAKEHOLDER_KEYWORDS, "Property managers")
    product = company_product or infer_product(text)
    sentiment = "negative" if any(word in text.lower() for word in ["complain", "slow", "poor", "expensive", "frustrating", "missing"]) else "mixed"
    strength = evidence_strength(text, bool(country or inferred_country), bool(product))
    summary = summarize(text)
    duplicate_group = normalize_group(f"{category} {summary}")
    return {
        "country": inferred_country,
        "stakeholder_type": inferred_stakeholder,
        "company_product": product,
        "complaint_category": category,
        "summary": summary,
        "sentiment": sentiment,
        "evidence_strength": strength,
        "duplicate_group": duplicate_group,
    }


def consolidate_category(text: str, category: str) -> str:
    lower = text.lower()
    maintenance_terms = ["maintenance", "repair", "contractor", "coordination"]
    communication_terms = ["communication", "update", "response", "tenant", "chase", "follow-up", "manual", "slow"]
    if any(term in lower for term in maintenance_terms) and any(term in lower for term in communication_terms):
        return "Maintenance communication issues"
    return category


def choose_from_keywords(text: str, groups: dict[str, list[str]], fallback: str) -> str:
    lower = text.lower()
    best = fallback
    best_score = 0
    for group, keywords in groups.items():
        score = sum(1 for keyword in keywords if keyword.lower() in lower)
        if score > best_score:
            best = group
            best_score = score
    return best


def infer_country(text: str) -> str:
    lower = text.lower()
    for country in COUNTRY_HINTS:
        if country.lower() in lower:
            return country
    return "Unknown"


def infer_product(text: str) -> str:
    matches = re.findall(r"\b[A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)?\b", text)
    ignored = {"Property", "Tenant", "Maintenance", "Ireland", "United Kingdom", "United States"}
    products = [match for match in matches if match not in ignored]
    return ", ".join(products[:3])


def evidence_strength(text: str, has_country: bool, has_product: bool) -> int:
    words = len(text.split())
    score = 35
    if words >= 20:
        score += 20
    if words >= 50:
        score += 15
    if has_country:
        score += 10
    if has_product:
        score += 10
    if any(word in text.lower() for word in ["repeatedly", "multiple", "always", "every week", "again"]):
        score += 10
    return min(score, 100)


def summarize(text: str) -> str:
    compact = " ".join(text.split())
    return compact.split(".")[0][:220] or "Evidence requires review"


def normalize_group(text: str) -> str:
    tokens = [token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 3]
    important = tokens[:10]
    return "-".join(important) or "general"


def generate_findings(db_path: str | Path, study_id: str = DEFAULT_STUDY_ID, min_signals: int = 2) -> list[dict[str, object]]:
    active_run = get_active_study_run(db_path, study_id)
    include_demo = bool(active_run and active_run.get("study_mode") == "demo")
    signals = [signal for signal in list_signals(db_path, study_id, include_demo=include_demo) if signal["status"] == "active"]
    if active_run and active_run.get("study_mode") == "production":
        min_signals = max(min_signals, 3)
        signals = [signal for signal in signals if is_accepted_production_signal(signal)]
    groups: dict[str, list[dict[str, object]]] = {}
    for signal in signals:
        key = str(signal["complaint_category"] or "Market problem")
        groups.setdefault(key, []).append(signal)

    created = []
    for grouped_signals in groups.values():
        if len(grouped_signals) < min_signals:
            continue
        finding = upsert_finding(db_path, study_id, grouped_signals)
        created.append(finding)
    add_event(db_path, "StudyFindingsGenerated", "PX-R001", "PX-R001 generated study findings", str(len(created)), study_id)
    return created


def upsert_finding(db_path: str | Path, study_id: str, signals: list[dict[str, object]]) -> dict[str, object]:
    study_run_id = str(signals[0].get("study_run_id") or "")
    category = str(signals[0]["complaint_category"] or "Market problem")
    theme = category
    signal_ids = [str(signal["id"]) for signal in signals]
    sources = sorted({source_domain_or_identity(signal) for signal in signals})
    countries = sorted({str(signal.get("country") or "Unknown") for signal in signals})
    stakeholders = sorted({str(signal.get("stakeholder_type") or "Unknown") for signal in signals})
    products = sorted({str(signal.get("company_product") or "") for signal in signals if signal.get("company_product")})
    confidence = min(100, round((sum(int(signal["evidence_strength"] or 0) for signal in signals) / len(signals)) + min(len(signals) * 5, 20)))
    problem = f"{category} appears repeatedly across {len(signals)} signals from {len(sources)} independent sources."
    evidence_summary = " | ".join(str(signal["summary"]) for signal in signals[:3])
    contains_demo = any(bool(signal.get("is_demo")) for signal in signals)
    non_demo_only = not contains_demo
    accepted_only = all(is_accepted_production_signal(signal) for signal in signals) if non_demo_only else False
    required_signal_count = 2 if contains_demo else 3
    sufficient = len(signals) >= required_signal_count and len(sources) >= 2 and non_demo_only and accepted_only
    status = "Demo Finding" if contains_demo and len(signals) >= 2 else "pending_audit" if sufficient else "Insufficient Evidence"
    data_origin = "demo" if contains_demo else "verified_import"
    verification_status = "unverified" if contains_demo else "pending_review"
    confidence_reasoning = (
        f"{len(signals)} supporting signals, {len(sources)} independent sources, "
        f"{len(countries)} countries, {len(stakeholders)} stakeholder groups. "
        f"{'Contains demo evidence; rehearsal only.' if contains_demo else 'Accepted complaint evidence only.' if accepted_only else 'Production signals did not pass complaint evidence gate.'}"
    )

    with connect(db_path) as connection:
        existing = connection.execute(
            "SELECT * FROM study_findings WHERE study_id = ? AND study_run_id = ? AND theme = ? AND complaint_category = ? AND status != 'archived'",
            (study_id, study_run_id, theme, category),
        ).fetchone()
        now = utc_now()
        if existing:
            finding_id = existing["id"]
            connection.execute(
                """
                UPDATE study_findings
                SET signal_count = ?, independent_source_count = ?, countries = ?, stakeholder_types = ?,
                    products_mentioned = ?, representative_signals = ?, evidence_summary = ?,
                    research_confidence = ?, confidence_score = ?, country_count = ?, stakeholder_count = ?,
                    supporting_evidence_count = ?, contradictory_evidence_count = ?, confidence_reasoning = ?,
                    status = ?, data_origin = ?, verification_status = ?, is_demo = ?, source_confidence = ?,
                    last_updated = ?
                WHERE id = ?
                """,
                (
                    len(signals),
                    len(sources),
                    json.dumps(countries),
                    json.dumps(stakeholders),
                    json.dumps(products),
                    json.dumps(signal_ids),
                    evidence_summary,
                    confidence,
                    confidence,
                    len(countries),
                    len(stakeholders),
                    len(signals),
                    0,
                    confidence_reasoning,
                    status,
                    data_origin,
                    verification_status,
                    1 if contains_demo else 0,
                    confidence,
                    now,
                    finding_id,
                ),
            )
        else:
            finding_id = next_sequence_id("FND", count_rows(connection, "study_findings"))
            connection.execute(
                """
                INSERT INTO study_findings
                (id, study_id, study_run_id, theme, problem_statement, complaint_category, signal_count,
                 independent_source_count, countries, stakeholder_types, products_mentioned,
                 representative_signals, evidence_summary, research_confidence, confidence_score, country_count,
                 stakeholder_count, supporting_evidence_count, contradictory_evidence_count, confidence_reasoning,
                 status, created_at, data_origin, verification_status, is_demo, source_confidence, created_by_worker,
                 last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    finding_id,
                    study_id,
                    study_run_id,
                    theme,
                    problem,
                    category,
                    len(signals),
                    len(sources),
                    json.dumps(countries),
                    json.dumps(stakeholders),
                    json.dumps(products),
                    json.dumps(signal_ids),
                    evidence_summary,
                    confidence,
                    confidence,
                    len(countries),
                    len(stakeholders),
                    len(signals),
                    0,
                    confidence_reasoning,
                    status,
                    now,
                    data_origin,
                    verification_status,
                    1 if contains_demo else 0,
                    confidence,
                    "PX-R001",
                    now,
                ),
            )
    return get_finding(db_path, finding_id)


def get_finding(db_path: str | Path, finding_id: str) -> dict[str, object]:
    with connect(db_path) as connection:
        row = connection.execute("SELECT * FROM study_findings WHERE id = ?", (finding_id,)).fetchone()
    if row is None:
        raise ValueError(f"Finding not found: {finding_id}")
    return row_to_dict(row)


def list_findings(
    db_path: str | Path,
    study_id: str = DEFAULT_STUDY_ID,
    study_run_id: str | None = None,
    include_archived: bool = False,
    include_demo: bool = False,
) -> list[dict[str, object]]:
    run_id = study_run_id or str((get_active_study_run(db_path, study_id) or {}).get("id") or "")
    where, params = run_filter(study_id, run_id, include_archived, include_demo)
    with connect(db_path) as connection:
        rows = connection.execute(f"SELECT * FROM study_findings WHERE {where} ORDER BY created_at DESC", params).fetchall()
    return [row_to_dict(row) for row in rows]


def calculate_oci(scores: dict[str, int]) -> int:
    if "traceability_score" in scores:
        oci = round(
            scores["evidence_score"] * 0.25
            + scores["frequency_score"] * 0.15
            + scores["market_size_score"] * 0.15
            + scores["pain_severity_score"] * 0.15
            + scores["competition_gap_score"] * 0.10
            + scores["traceability_score"] * 0.20
        )
        if scores["traceability_score"] < 100:
            return min(oci, 60)
        return oci
    return round(
        scores["evidence_score"] * 0.20
        + scores["frequency_score"] * 0.15
        + scores["market_size_score"] * 0.15
        + scores["pain_severity_score"] * 0.15
        + scores["competition_gap_score"] * 0.10
        + (100 - scores["build_complexity_score"]) * 0.10
        + scores["commercial_potential_score"] * 0.10
        + scores["strategic_fit_score"] * 0.05
    )


def audit_finding(db_path: str | Path, finding_id: str) -> dict[str, object]:
    finding = get_finding(db_path, finding_id)
    is_demo_finding = bool(finding.get("is_demo"))
    if is_demo_finding and finding["status"] == "Insufficient Evidence" and len(_loads_list(finding.get("representative_signals"))) >= 2:
        with connect(db_path) as connection:
            connection.execute(
                "UPDATE study_findings SET status = ?, last_updated = ? WHERE id = ?",
                ("Demo Finding", utc_now(), finding_id),
            )
        finding = get_finding(db_path, finding_id)
    if finding["status"] not in {"pending_audit", "Demo Finding"}:
        raise ValueError("Finding is not auditable until it has at least 2 supporting non-demo signals from 2 independent sources.")
    if is_demo_finding and finding["status"] != "Demo Finding":
        raise ValueError("Demo findings must use the demo rehearsal audit path.")
    scores = score_finding(finding)
    signals = [get_signal(db_path, str(signal_id)) for signal_id in _loads_list(finding.get("representative_signals"))]
    contains_demo = any(bool(signal.get("is_demo")) for signal in signals) or bool(finding.get("is_demo"))
    traceability_complete = traceability_complete_for_signals(signals)
    accepted_production_signals = [signal for signal in signals if is_accepted_production_signal(signal)]
    independent_domains = {source_domain_or_identity(signal) for signal in accepted_production_signals}
    trust_scores = [int(signal_quality_metadata(signal).get("source_trust_score") or 0) for signal in accepted_production_signals]
    average_trust_score = round(sum(trust_scores) / len(trust_scores), 1) if trust_scores else 0
    excluded_classes = [
        str(signal_quality_metadata(signal).get("classification") or "unknown")
        for signal in signals
        if signal_quality_metadata(signal).get("classification") not in PRODUCTION_ELIGIBLE_CLASSIFICATIONS
    ]
    production_requirements_met = (
        contains_demo
        or (
            len(accepted_production_signals) >= 3
            and len(independent_domains) >= 2
            and average_trust_score >= 80
            and traceability_complete
            and len(accepted_production_signals) == len(signals)
        )
    )
    scores["traceability_score"] = 100 if traceability_complete else 40
    oci = calculate_oci(scores)
    if contains_demo:
        oci = 0
    decision = (
        "Demo Audited"
        if contains_demo
        else "Approve Opportunity"
        if oci >= 80 and production_requirements_met
        else "Needs More Evidence"
        if oci >= 60 or not production_requirements_met
        else "Reject"
    )
    missing = []
    if int(finding["independent_source_count"] or 0) < 2:
        missing.append("More independent sources")
    if len(accepted_production_signals) < 3 and not contains_demo:
        missing.append("At least 3 accepted complaint/pain signals required")
    if len(independent_domains) < 2 and not contains_demo:
        missing.append("At least 2 independent source domains required")
    if average_trust_score < 80 and not contains_demo:
        missing.append("Average source trust score must be at least 80")
    if not contains_demo and len(accepted_production_signals) != len(signals):
        missing.append("Only complaint, operational pain, or workflow inefficiency evidence can support approval")
    if len(_loads_list(finding.get("countries"))) < 2:
        missing.append("More country coverage")
    if contains_demo:
        missing.append("Non-demo verified evidence required")
    if not traceability_complete:
        missing.append("Complete traceability to sources required")
    reasoning = (
        f"Finding has {finding['signal_count']} signals, {finding['independent_source_count']} independent sources, "
        f"average trust score {average_trust_score}, traceability score {scores['traceability_score']}, "
        f"excluded classes {excluded_classes or 'none'}, OCI {oci}, decision {decision}."
    )
    with connect(db_path) as connection:
        audit_id = next_sequence_id("FAD", count_rows(connection, "finding_audits"))
        now = utc_now()
        connection.execute(
            """
            INSERT INTO finding_audits
            (id, study_id, study_run_id, finding_id, decision, evidence_score, frequency_score, market_size_score,
             pain_severity_score, competition_gap_score, build_complexity_score, commercial_potential_score,
             strategic_fit_score, traceability_score, opportunity_confidence_index, final_oci, score_breakdown,
             oci_reasoning, missing_evidence_warnings, contradictions, missing_evidence, reasoning_summary,
             recommendation, status, created_at, data_origin, verification_status, is_demo, source_confidence,
             created_by_worker, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                audit_id,
                finding["study_id"],
                finding.get("study_run_id"),
                finding_id,
                decision,
                scores["evidence_score"],
                scores["frequency_score"],
                scores["market_size_score"],
                scores["pain_severity_score"],
                scores["competition_gap_score"],
                scores["build_complexity_score"],
                scores["commercial_potential_score"],
                scores["strategic_fit_score"],
                scores["traceability_score"],
                oci,
                oci,
                json.dumps(scores, ensure_ascii=False),
                explain_oci(scores, oci, contains_demo),
                json.dumps(missing, ensure_ascii=False),
                "No direct contradictions detected.",
                ", ".join(missing) if missing else "None",
                reasoning,
                "Create demo opportunity for rehearsal." if decision == "Demo Audited" else "Approve into Approved Opportunities." if decision == "Approve Opportunity" else "Collect more evidence before approval.",
                "Demo Audited" if contains_demo else "active",
                now,
                "demo" if contains_demo else "verified_import",
                "unverified" if contains_demo else "verified",
                1 if contains_demo else 0,
                scores["evidence_score"],
                "PX-A001",
                now,
            ),
        )
        connection.execute("UPDATE study_findings SET status = ? WHERE id = ?", ("Demo Audited" if contains_demo else "audited", finding_id))
    add_event(db_path, "FindingAudited", "PX-A001", "PX-A001 audited finding", decision, audit_id)
    return get_finding_audit(db_path, audit_id)


def score_finding(finding: dict[str, object]) -> dict[str, int]:
    signal_count = int(finding.get("signal_count") or 0)
    source_count = int(finding.get("independent_source_count") or 0)
    countries = len(_loads_list(finding.get("countries")))
    confidence = int(finding.get("research_confidence") or 0)
    category = str(finding.get("complaint_category") or "").lower()
    build_complexity = 35 if any(word in category for word in ["communication", "report", "manual", "integration"]) else 55
    return {
        "evidence_score": min(100, confidence),
        "frequency_score": min(100, signal_count * 35),
        "market_size_score": min(100, 55 + countries * 15 + source_count * 5),
        "pain_severity_score": 90 if any(word in category for word in ["maintenance", "payment", "communication", "expensive"]) else 75,
        "competition_gap_score": 80,
        "build_complexity_score": build_complexity,
        "commercial_potential_score": 85,
        "strategic_fit_score": 90,
    }


def traceability_complete_for_signals(signals: list[dict[str, object]]) -> bool:
    return bool(signals) and all(signal.get("source_url") or signal.get("source_name") for signal in signals)


def explain_oci(scores: dict[str, int], oci: int, contains_demo: bool) -> str:
    if contains_demo:
        return "OCI forced to 0 because demo evidence cannot approve an opportunity."
    if scores.get("traceability_score", 0) < 100:
        return f"OCI capped at {oci} because traceability is incomplete."
    return f"OCI {oci} derived from evidence, frequency, market size, pain severity, competition gap, and traceability scores."


def get_finding_audit(db_path: str | Path, audit_id: str) -> dict[str, object]:
    with connect(db_path) as connection:
        row = connection.execute("SELECT * FROM finding_audits WHERE id = ?", (audit_id,)).fetchone()
    if row is None:
        raise ValueError(f"Finding audit not found: {audit_id}")
    return row_to_dict(row)


def list_finding_audits(
    db_path: str | Path,
    study_id: str = DEFAULT_STUDY_ID,
    study_run_id: str | None = None,
    include_archived: bool = False,
    include_demo: bool = False,
) -> list[dict[str, object]]:
    run_id = study_run_id or str((get_active_study_run(db_path, study_id) or {}).get("id") or "")
    where, params = run_filter(study_id, run_id, include_archived, include_demo)
    with connect(db_path) as connection:
        rows = connection.execute(f"SELECT * FROM finding_audits WHERE {where} ORDER BY created_at DESC", params).fetchall()
    return [row_to_dict(row) for row in rows]


def approve_audited_opportunities(db_path: str | Path, study_id: str = DEFAULT_STUDY_ID) -> list[dict[str, object]]:
    approved = []
    active_run = get_active_study_run(db_path, study_id)
    run_id = str((active_run or {}).get("id") or "")
    is_demo_run = bool(active_run and active_run.get("study_mode") == "demo")
    with connect(db_path) as connection:
        rows = connection.execute(
            f"""
            SELECT finding_audits.*
            FROM finding_audits
            LEFT JOIN opportunity_records ON opportunity_records.audit_id = finding_audits.id
            WHERE finding_audits.study_id = ?
              AND finding_audits.study_run_id = ?
              AND finding_audits.status != 'archived'
              AND finding_audits.is_demo = ?
              AND finding_audits.decision = ?
              AND opportunity_records.id IS NULL
            ORDER BY finding_audits.created_at ASC
            """,
            (study_id, run_id, 1 if is_demo_run else 0, "Demo Audited" if is_demo_run else "Approve Opportunity"),
        ).fetchall()
    for row in rows:
        audit = row_to_dict(row)
        if bool(audit.get("is_demo")) and not is_demo_run:
            continue
        approved.append(create_opportunity_from_audit(db_path, audit))
    add_event(db_path, "OpportunitiesApproved", "PX-L001", "PX-L001 approved audited opportunities", str(len(approved)), study_id)
    return approved


def approve_opportunities(db_path: str | Path, study_id: str = DEFAULT_STUDY_ID) -> list[dict[str, object]]:
    return approve_audited_opportunities(db_path, study_id)


def promote_approved_opportunities(db_path: str | Path, study_id: str = DEFAULT_STUDY_ID) -> list[dict[str, object]]:
    return approve_audited_opportunities(db_path, study_id)


def create_opportunity_from_audit(db_path: str | Path, audit: dict[str, object]) -> dict[str, object]:
    finding = get_finding(db_path, str(audit["finding_id"]))
    signals = [get_signal(db_path, str(signal_id)) for signal_id in _loads_list(finding.get("representative_signals"))]
    is_demo_opportunity = bool(audit.get("is_demo")) or bool(finding.get("is_demo")) or any(bool(signal.get("is_demo")) for signal in signals)
    active_run = get_active_study_run(db_path, str(audit["study_id"]))
    if is_demo_opportunity and not (active_run and active_run.get("study_mode") == "demo" and audit.get("study_run_id") == active_run.get("id")):
        raise ValueError("Demo data cannot be approved into a real Opportunity.")
    now = utc_now()
    with connect(db_path) as connection:
        opportunity_id = next_sequence_id("OPP", count_rows(connection, "opportunity_records"))
        oci = int(audit["opportunity_confidence_index"] or 0)
        status = "Demo Opportunity" if is_demo_opportunity else "Approved Opportunity"
        engineering_status = "Demo Opportunity" if is_demo_opportunity else "Engineering Specification Required"
        traceability_complete = traceability_complete_for_signals(signals)
        connection.execute(
            """
            INSERT INTO opportunity_records
            (id, study_id, study_run_id, industry, market, problem, evidence_summary, evidence_count, independent_sources,
             countries, products_mentioned, stakeholder_types, customer_segments, current_solutions,
             strengths_existing_solutions, weaknesses_existing_solutions, opportunity_confidence_index,
             commercial_potential, estimated_market_size, estimated_build_complexity, recommended_component,
             recommended_pricing_model, recommended_market_entry, engineering_recommendation, problem_scope,
             target_users, required_inputs, expected_outputs, system_boundaries, traceability_chain_complete,
             non_demo_evidence_only, audit_id, finding_id, status, engineering_status, owner, version, created_at,
             last_updated, data_origin, verification_status, is_demo, source_confidence, created_by_worker)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                opportunity_id,
                audit["study_id"],
                audit.get("study_run_id"),
                "Property Management",
                "Property Management",
                finding["problem_statement"],
                finding["evidence_summary"],
                finding["signal_count"],
                finding["independent_source_count"],
                finding["countries"],
                finding["products_mentioned"],
                finding["stakeholder_types"],
                finding["stakeholder_types"],
                finding["products_mentioned"],
                "Existing products have market presence and workflow coverage.",
                "Repeated complaints indicate gaps in speed, communication, cost, or usability.",
                oci,
                "Demo" if is_demo_opportunity else "High" if oci >= ENGINEERING_READY_OCI else "Medium",
                "Global niche-to-large SaaS opportunity",
                "Low" if int(audit["build_complexity_score"] or 100) <= 40 else "Medium",
                recommended_component(finding),
                "Subscription with usage-based tiers",
                "Start with a narrow verified workflow and one stakeholder segment.",
                "",
                "",
                "",
                "",
                "",
                "",
                1 if traceability_complete else 0,
                0 if is_demo_opportunity else 1,
                audit["id"],
                finding["id"],
                status,
                engineering_status,
                "PX-H001",
                "v1.0",
                now,
                now,
                "demo" if is_demo_opportunity else "verified_import",
                "unverified" if is_demo_opportunity else "verified",
                1 if is_demo_opportunity else 0,
                audit.get("source_confidence"),
                "PX-L001",
            ),
        )
        connection.execute("UPDATE study_findings SET status = ? WHERE id = ?", ("Demo Opportunity" if is_demo_opportunity else "opportunity_approved", finding["id"]))
    add_notification(db_path, "demo_opportunity_created" if is_demo_opportunity else "opportunity_approved", f"{'Demo opportunity created' if is_demo_opportunity else 'Opportunity approved'}: {opportunity_id}", opportunity_id)
    return get_opportunity(db_path, opportunity_id)


def mark_engineering_ready(db_path: str | Path, opportunity_id: str, spec: dict[str, object]) -> dict[str, object]:
    opportunity = get_opportunity(db_path, opportunity_id)
    is_demo_opportunity = bool(opportunity.get("is_demo"))
    required = [
        "recommended_component",
        "engineering_recommendation",
        "problem_scope",
        "target_users",
        "required_inputs",
        "expected_outputs",
        "system_boundaries",
    ]
    merged = {field: spec.get(field) or opportunity.get(field) for field in required}
    missing = [field for field, value in merged.items() if not value]
    chain = traceability_chain(db_path, opportunity_id)
    non_demo = not any(bool(record.get("is_demo")) for record in [chain["opportunity"], chain["audit"], chain["finding"], *chain["signals"]])
    traceability_complete = bool(chain["signals"]) and bool(chain["sources"])
    if missing or (not is_demo_opportunity and not non_demo) or not traceability_complete:
        return {"status": "blocked", "missing_fields": missing, "non_demo_evidence_only": non_demo, "traceability_chain_complete": traceability_complete}
    with connect(db_path) as connection:
        connection.execute(
            """
            UPDATE opportunity_records
            SET engineering_status = ?, status = ?, engineering_recommendation = ?, problem_scope = ?,
                target_users = ?, required_inputs = ?, expected_outputs = ?, system_boundaries = ?,
                traceability_chain_complete = ?, non_demo_evidence_only = ?, last_updated = ?
            WHERE id = ?
            """,
            (
                "Demo Engineering Ready" if is_demo_opportunity else "Engineering Ready",
                "Demo Engineering Ready" if is_demo_opportunity else "Engineering Ready",
                merged["engineering_recommendation"],
                merged["problem_scope"],
                merged["target_users"],
                merged["required_inputs"],
                merged["expected_outputs"],
                merged["system_boundaries"],
                1,
                1,
                utc_now(),
                opportunity_id,
            ),
        )
    return get_opportunity(db_path, opportunity_id)


def recommended_component(finding: dict[str, object]) -> str:
    category = str(finding.get("complaint_category") or "").lower()
    if "maintenance" in category:
        return "Maintenance Communication Component"
    if "payment" in category or "accounting" in category:
        return "Payment Reconciliation Component"
    if "report" in category:
        return "Property Reporting Component"
    if "integration" in category:
        return "Integration Sync Component"
    return "Workflow Automation Component"


def get_opportunity(db_path: str | Path, opportunity_id: str) -> dict[str, object]:
    with connect(db_path) as connection:
        row = connection.execute("SELECT * FROM opportunity_records WHERE id = ?", (opportunity_id,)).fetchone()
    if row is None:
        raise ValueError(f"Opportunity not found: {opportunity_id}")
    return row_to_dict(row)


def list_opportunities(
    db_path: str | Path,
    study_id: str = DEFAULT_STUDY_ID,
    study_run_id: str | None = None,
    include_archived: bool = False,
    include_demo: bool = False,
) -> list[dict[str, object]]:
    run_id = study_run_id or str((get_active_study_run(db_path, study_id) or {}).get("id") or "")
    where, params = run_filter(study_id, run_id, include_archived, include_demo)
    with connect(db_path) as connection:
        rows = connection.execute(f"SELECT * FROM opportunity_records WHERE {where} ORDER BY opportunity_confidence_index DESC, created_at DESC", params).fetchall()
    return [row_to_dict(row) for row in rows]


def archive_record(db_path: str | Path, table_name: str, record_id: str) -> dict[str, object]:
    allowed = {
        "study_signals": "id",
        "study_findings": "id",
        "finding_audits": "id",
        "opportunity_records": "id",
        "study_briefs": "id",
    }
    if table_name not in allowed:
        raise ValueError(f"Unsupported archive table: {table_name}")
    with connect(db_path) as connection:
        row = connection.execute(f"SELECT * FROM {table_name} WHERE {allowed[table_name]} = ?", (record_id,)).fetchone()
        if row is None:
            raise ValueError(f"Record not found: {record_id}")
        record = row_to_dict(row)
        now = utc_now()
        previous_status = str(record.get("status") or "")
        connection.execute(
            f"""
            UPDATE {table_name}
            SET status = ?, verification_status = ?, archive_reason = ?, archived_at = ?, archived_by = ?,
                previous_status = ?, last_updated = ?
            WHERE {allowed[table_name]} = ?
            """,
            ("archived", "archived", "Archived instead of deleted.", now, "PX-H001", previous_status, now, record_id),
        )
        if bool(record.get("is_demo")):
            connection.execute(
                """
                INSERT INTO demo_archive (table_name, record_id, record_json, archive_reason, archived_at, archived_by)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (table_name, record_id, json.dumps(record, ensure_ascii=False), "Archived demo data.", now, "PX-H001"),
            )
    add_event(db_path, "RecordArchived", "PX-H001", "Record archived instead of deleted", table_name, record_id)
    return {"table": table_name, "id": record_id, "status": "archived"}


def traceability_chain(db_path: str | Path, opportunity_id: str, include_archived: bool = False) -> dict[str, object]:
    opportunity = get_opportunity(db_path, opportunity_id)
    active_run = get_active_study_run(db_path, str(opportunity["study_id"]))
    if not include_archived:
        if opportunity.get("status") == "archived":
            raise ValueError("Archived opportunity traceability requires include_archived=True.")
        if active_run and opportunity.get("study_run_id") != active_run.get("id"):
            raise ValueError("Opportunity is not part of the active study run.")
    audit = get_finding_audit(db_path, str(opportunity["audit_id"]))
    finding = get_finding(db_path, str(opportunity["finding_id"]))
    signal_ids = _loads_list(finding.get("representative_signals"))
    signals = [get_signal(db_path, str(signal_id)) for signal_id in signal_ids]
    if not include_archived:
        signals = [signal for signal in signals if signal.get("status") != "archived" and signal.get("study_run_id") == opportunity.get("study_run_id")]
    sources = [
        {
            "signal_id": signal["id"],
            "source_url": signal.get("source_url"),
            "source_name": signal.get("source_name"),
            "source_type": signal.get("source_type"),
        }
        for signal in signals
    ]
    return {"opportunity": opportunity, "audit": audit, "finding": finding, "signals": signals, "sources": sources}


def finding_evidence(db_path: str | Path, finding_id: str, include_archived: bool = False) -> dict[str, object]:
    finding = get_finding(db_path, finding_id)
    if not include_archived and finding.get("status") == "archived":
        raise ValueError("Archived finding evidence requires include_archived=True.")
    signals = [get_signal(db_path, str(signal_id)) for signal_id in _loads_list(finding.get("representative_signals"))]
    if not include_archived:
        signals = [signal for signal in signals if signal.get("status") != "archived" and signal.get("study_run_id") == finding.get("study_run_id")]
    return {"finding": finding, "signals": signals}


def study_progress(
    db_path: str | Path,
    study_id: str = DEFAULT_STUDY_ID,
    study_run_id: str | None = None,
    include_archived: bool = False,
    include_demo: bool = False,
) -> dict[str, object]:
    study = get_study(db_path, study_id)
    active_run = get_active_study_run(db_path, study_id)
    run_id = study_run_id or str((active_run or {}).get("id") or "")
    run = get_study_run(db_path, run_id) if run_id else None
    signals = list_signals(db_path, study_id, run_id, include_archived, include_demo)
    findings = list_findings(db_path, study_id, run_id, include_archived, include_demo)
    audits = list_finding_audits(db_path, study_id, run_id, include_archived, include_demo)
    opportunities = list_opportunities(db_path, study_id, run_id, include_archived, include_demo)
    archives = archived_count(db_path, study_id, run_id)
    demo_count = demo_records_count(db_path, study_id, run_id, include_archived)
    pending_verification = sum(1 for row in [*signals, *findings, *audits, *opportunities] if row.get("verification_status") in {"unverified", "pending_review", "pending_verification"})
    avg_oci_values = [int(opportunity.get("opportunity_confidence_index") or 0) for opportunity in opportunities]
    return {
        "study_id": study_id,
        "active_run_id": run_id,
        "run_status": str((run or {}).get("status") or ""),
        "study_mode": str((run or study or {}).get("study_mode") or "demo"),
        "signals_collected": len(signals),
        "findings_created": len(findings),
        "audits_completed": len(audits),
        "opportunities_approved": len([opportunity for opportunity in opportunities if opportunity["status"] in {"Approved Opportunity", "Engineering Ready", "Demo Opportunity", "Demo Engineering Ready"}]),
        "opportunities_rejected": len([audit for audit in audits if audit["decision"] == "Reject"]),
        "countries_covered": sorted({str(signal.get("country") or "Unknown") for signal in signals}),
        "stakeholders_covered": sorted({str(signal.get("stakeholder_type") or "Unknown") for signal in signals}),
        "source_coverage": len({str(signal.get("source_url") or signal.get("source_name") or signal["id"]) for signal in signals}),
        "engineering_ready": [opportunity for opportunity in opportunities if opportunity.get("engineering_status") in {"Engineering Ready", "Demo Engineering Ready"}],
        "top_opportunities": opportunities[:5],
        "weak_evidence": [finding for finding in findings if int(finding.get("research_confidence") or 0) < 75],
        "average_oci": round(sum(avg_oci_values) / len(avg_oci_values), 1) if avg_oci_values else 0,
        "high_priority_opportunities": [opportunity for opportunity in opportunities if int(opportunity.get("opportunity_confidence_index") or 0) >= ENGINEERING_READY_OCI],
        "archived_count": archives,
        "demo_records_count": demo_count,
        "verification_pending_count": pending_verification,
    }


def production_pipeline_statuses(progress: dict[str, object]) -> dict[str, str]:
    signals = int(progress.get("signals_collected") or 0)
    findings = int(progress.get("findings_created") or 0)
    audits = int(progress.get("audits_completed") or 0)
    opportunities = int(progress.get("opportunities_approved") or 0)
    specs = len(progress.get("top_opportunities") or []) if opportunities else 0
    engineering_ready = len(progress.get("engineering_ready") or [])

    return {
        "Evidence Collection": "Completed" if signals else "Active",
        "Signal Detection": "Completed" if signals else "Locked",
        "Finding Generation": "Completed" if findings else "Active" if signals else "Locked",
        "Audit": "Completed" if audits else "Active" if findings else "Locked",
        "Opportunity": "Completed" if opportunities else "Active" if audits else "Locked",
        "Engineering Spec": "Completed" if engineering_ready else "Active" if opportunities or specs else "Locked",
        "Prototype": "Locked",
        "Internal Validation": "Locked",
        "External Validation": "Locked",
        "Commercial Ready": "Locked",
    }


def evidence_quality_dashboard(signals: list[dict[str, object]], skipped: list[dict[str, object]] | None = None) -> dict[str, object]:
    qualities = [signal_quality_metadata(signal) for signal in signals]
    eligible = [quality for quality in qualities if quality.get("production_eligible")]
    trust_scores = [int(quality.get("source_trust_score") or 0) for quality in eligible]
    domains = {source_domain_or_identity(signal) for signal, quality in zip(signals, qualities) if quality.get("production_eligible")}
    classifications = [str(quality.get("classification") or "unknown") for quality in qualities]
    skipped = skipped or []
    return {
        "total_pulled": len(signals) + len(skipped),
        "accepted_production_signals": len(eligible),
        "market_context": classifications.count("market_context"),
        "vendor_content": classifications.count("vendor_content"),
        "community_signals": classifications.count("community_signal"),
        "rejected": len([quality for quality in qualities if not quality.get("production_eligible")]) + len(skipped),
        "duplicates": len([item for item in skipped if item.get("reason") == "duplicate"]),
        "average_trust_score": round(sum(trust_scores) / len(trust_scores), 1) if trust_scores else 0,
        "independent_domains": len(domains),
        "production_readiness": "Ready for finding generation" if len(eligible) >= 3 and len(domains) >= 2 and (round(sum(trust_scores) / len(trust_scores), 1) if trust_scores else 0) >= 80 else "Needs stronger evidence",
    }


def archived_count(db_path: str | Path, study_id: str, study_run_id: str | None = None) -> int:
    run_id = study_run_id or str((get_active_study_run(db_path, study_id) or {}).get("id") or "")
    total = 0
    with connect(db_path) as connection:
        for table_name in RUN_SCOPED_TABLES:
            total += int(connection.execute(f"SELECT COUNT(*) AS count FROM {table_name} WHERE study_id = ? AND study_run_id = ? AND status = 'archived'", (study_id, run_id)).fetchone()["count"])
    return total


def generate_executive_brief(db_path: str | Path, study_id: str = DEFAULT_STUDY_ID) -> dict[str, object]:
    study = get_or_create_default_study(db_path) if study_id == DEFAULT_STUDY_ID else get_study(db_path, study_id)
    if not study:
        raise ValueError(f"Study not found: {study_id}")
    active_run = get_active_study_run(db_path, study_id)
    include_demo = bool(active_run and active_run.get("study_mode") == "demo")
    progress = study_progress(db_path, study_id)
    risks = []
    if not progress["countries_covered"]:
        risks.append("No country coverage yet.")
    if progress["signals_collected"] < 2:
        risks.append("Not enough repeated evidence for opportunity creation.")
    if progress["audits_completed"] == 0:
        risks.append("No findings audited yet.")
    missing = []
    if len(progress["countries_covered"]) < 2:
        missing.append("More countries")
    if progress["source_coverage"] < 2:
        missing.append("More independent sources")
    recommendation = (
        "Move engineering-ready opportunities into component planning."
        if progress["engineering_ready"]
        else "Collect more independent signals, then audit findings with repeated evidence."
    )
    body = (
        f"Study ID: {study_id}\n"
        f"Industry: Property Management\n"
        f"Market: {study['market']}\n"
        f"Signals collected: {progress['signals_collected']} signals\n"
        f"Findings created: {progress['findings_created']}\n"
        f"Audits completed: {progress['audits_completed']}\n"
        f"Approved Opportunities: {progress['opportunities_approved']}\n"
        f"Engineering Ready Opportunities: {len(progress['engineering_ready'])}\n"
        f"Countries covered: {', '.join(progress['countries_covered']) or 'None'}\n"
        f"Stakeholder types covered: {', '.join(progress['stakeholders_covered']) or 'None'}\n"
        f"Independent sources count: {progress['source_coverage']}\n"
        f"Highest OCI opportunities: {len(progress['top_opportunities'])}\n"
        f"Recommended next action: "
        f"{'Move engineering-ready opportunities into specification review.' if progress['engineering_ready'] else 'Collect verified non-demo evidence and audit only sufficiently supported findings.'}"
    )
    with connect(db_path) as connection:
        brief_id = next_sequence_id("GSB", count_rows(connection, "study_briefs"))
        connection.execute(
            """
            INSERT INTO study_briefs
            (id, study_id, study_run_id, brief_type, title, body, metrics, top_opportunities, risks, missing_evidence,
             engineering_recommendation, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                brief_id,
                study_id,
                str((active_run or {}).get("id") or ""),
                "executive",
                f"Executive Brief - {study_id}",
                body,
                json.dumps(progress, ensure_ascii=False),
                json.dumps(progress["top_opportunities"], ensure_ascii=False),
                json.dumps(risks, ensure_ascii=False),
                json.dumps(missing, ensure_ascii=False),
                recommendation,
                utc_now(),
            ),
        )
    add_event(db_path, "GoldenStudyBriefCreated", "PX-H001", "PX-H001 generated Golden Study executive brief", study_id, brief_id)
    return get_study_brief(db_path, brief_id)


def get_study_brief(db_path: str | Path, brief_id: str) -> dict[str, object]:
    with connect(db_path) as connection:
        row = connection.execute("SELECT * FROM study_briefs WHERE id = ?", (brief_id,)).fetchone()
    if row is None:
        raise ValueError(f"Study brief not found: {brief_id}")
    return row_to_dict(row)


def list_study_briefs(
    db_path: str | Path,
    study_id: str = DEFAULT_STUDY_ID,
    study_run_id: str | None = None,
    include_archived: bool = False,
    include_demo: bool = False,
) -> list[dict[str, object]]:
    run_id = study_run_id or str((get_active_study_run(db_path, study_id) or {}).get("id") or "")
    clauses = ["study_id = ?", "study_run_id = ?"]
    params: list[object] = [study_id, run_id]
    if not include_archived:
        clauses.append("(archived_at IS NULL OR archived_at = '')")
    if not include_demo:
        clauses.append("is_demo = 0")
    with connect(db_path) as connection:
        rows = connection.execute(f"SELECT * FROM study_briefs WHERE {' AND '.join(clauses)} ORDER BY created_at DESC", tuple(params)).fetchall()
    return [row_to_dict(row) for row in rows]


def run_research_batch(db_path: str | Path, raw_items: list[dict[str, object]], study_id: str = DEFAULT_STUDY_ID) -> dict[str, object]:
    signals = [
        create_signal(
            db_path,
            str(item.get("raw_text") or ""),
            study_id,
            str(item.get("source_url") or ""),
            str(item.get("source_name") or ""),
            str(item.get("source_type") or "manual"),
            str(item.get("source_date") or ""),
            str(item.get("country") or ""),
            str(item.get("stakeholder_type") or ""),
            str(item.get("company_product") or ""),
            str(item.get("data_origin") or "demo"),
            item.get("source_confidence"),
        )
        for item in raw_items
        if str(item.get("raw_text") or "").strip()
    ]
    findings = generate_findings(db_path, study_id)
    return {"signals": signals, "findings": findings}


def pull_real_market_evidence(
    db_path: str | Path,
    study_id: str = DEFAULT_STUDY_ID,
    providers: list[object] | None = None,
    max_sources: int = 10,
) -> dict[str, object]:
    active_run = get_active_study_run(db_path, study_id)
    if not active_run or active_run.get("study_mode") != "production":
        return {
            "status": "blocked",
            "message": "Real market evidence can only be pulled in Production Mode.",
            "sources_searched": 0,
            "candidate_results_found": 0,
            "signals_stored": 0,
            "skipped_duplicates": 0,
            "skipped_missing_source_or_text": 0,
            "skipped_not_complaint_or_pain_evidence": 0,
            "skipped_market_size_generic_or_marketing": 0,
            "providers_used": [],
            "active_run_id": "",
            "queries": GS001_REAL_EVIDENCE_QUERIES,
            "stored_signal_ids": [],
            "skipped": [],
            "signals": [],
            "technical_details": {},
        }
    if providers is None:
        readiness = provider_ready_for_research()
        if not readiness["ready"]:
            return {
                "status": "blocked",
                "message": str(readiness["message"]),
                "sources_searched": 0,
                "candidate_results_found": 0,
                "signals_stored": 0,
                "skipped_duplicates": 0,
                "skipped_missing_source_or_text": 0,
                "skipped_not_complaint_or_pain_evidence": 0,
                "skipped_market_size_generic_or_marketing": 0,
                "providers_used": [],
                "active_run_id": str(active_run["id"]),
                "queries": GS001_REAL_EVIDENCE_QUERIES,
                "stored_signal_ids": [],
                "skipped": [],
                "signals": [],
                "technical_details": readiness,
            }
        providers = configured_gs001_evidence_providers()

    retrieved_at = utc_now()
    provider_names: list[str] = []
    candidates: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []
    skipped_openai = 0
    sources_searched = 0
    for query in GS001_REAL_EVIDENCE_QUERIES:
        sources_searched += 1
        command = {
            "study": study_id,
            "industry": "Residential Property Management",
            "market": "United States",
            "keyword": query,
            "focus": "Maintenance Communication",
            "objective": "collect real, source-backed evidence of recurring problems, complaints, inefficiencies, or unmet needs",
        }
        for provider in providers:
            provider_name = str(getattr(provider, "name", provider.__class__.__name__))
            if "openai" in provider_name.lower():
                skipped_openai += 1
                skipped.append({"reason": "openai_not_evidence", "provider": provider_name, "query": query})
                continue
            if provider_name not in provider_names:
                provider_names.append(provider_name)
            try:
                results = provider.search(command)  # type: ignore[attr-defined]
            except Exception:
                skipped.append({"reason": "provider_failed", "provider": provider_name, "query": query})
                continue
            for result in results:
                normalized = normalize_provider_result(result, query, retrieved_at)
                candidates.append(normalized)
                if len(candidates) >= max_sources:
                    break
            if len(candidates) >= max_sources:
                break
        if len(candidates) >= max_sources:
            break

    stored = []
    skipped_missing = 0
    skipped_duplicates = 0
    skipped_not_pain = 0
    skipped_market_generic = 0
    for candidate in candidates[:max_sources]:
        if "openai" in str(candidate.get("provider_name") or "").lower():
            skipped_openai += 1
            skipped.append({"reason": "openai_not_evidence", "candidate": candidate})
            continue
        has_source_url = bool(str(candidate.get("source_url") or "").strip())
        has_source_title = bool(str(candidate.get("original_title") or "").strip())
        if not (has_source_url or has_source_title):
            skipped_missing += 1
            skipped.append({"reason": "missing_source", "candidate": candidate})
            continue
        if not str(candidate.get("raw_text") or "").strip():
            skipped_missing += 1
            skipped.append({"reason": "missing_raw_text", "candidate": candidate})
            continue
        if not bool(candidate.get("accepted_complaint_evidence")):
            reason = str(candidate.get("skip_reason") or "not_complaint_or_pain_evidence")
            if reason == "market_size_generic_or_marketing":
                skipped_market_generic += 1
            else:
                skipped_not_pain += 1
                reason = "not_complaint_or_pain_evidence"
            skipped.append({"reason": reason, "candidate": candidate})
            continue
        if signal_duplicate_exists(
            db_path,
            study_id,
            str(active_run["id"]),
            str(candidate.get("source_url") or ""),
            str(candidate.get("raw_text") or ""),
        ):
            skipped_duplicates += 1
            skipped.append({"reason": "duplicate", "candidate": candidate})
            continue
        signal = create_signal(
            db_path,
            str(candidate["raw_text"]),
            study_id,
            str(candidate.get("source_url") or ""),
            str(candidate.get("source_name") or ""),
            str(candidate.get("source_type") or "search_result"),
            str(candidate.get("source_date") or retrieved_at),
            "United States",
            str(candidate.get("stakeholder_type") or "Unknown"),
            "",
            "provider",
            candidate.get("source_confidence"),  # type: ignore[arg-type]
        )
        with connect(db_path) as connection:
            connection.execute(
                "UPDATE study_signals SET verification_status = ?, last_updated = ? WHERE id = ?",
                ("pending_verification", utc_now(), signal["id"]),
            )
        stored.append(get_signal(db_path, str(signal["id"])))

    status = "completed" if stored else "empty"
    message = "Research Run Complete" if stored else "No source-backed evidence found for this run."
    result = {
        "status": status,
        "message": message,
        "sources_searched": sources_searched,
        "candidate_results_found": len(candidates),
        "signals_stored": len(stored),
        "skipped_duplicates": skipped_duplicates,
        "skipped_missing_source_or_text": skipped_missing,
        "skipped_not_complaint_or_pain_evidence": skipped_not_pain,
        "skipped_market_size_generic_or_marketing": skipped_market_generic,
        "skipped_openai_only": skipped_openai,
        "providers_used": provider_names,
        "active_run_id": str(active_run["id"]),
        "queries": GS001_REAL_EVIDENCE_QUERIES,
        "stored_signal_ids": [str(signal["id"]) for signal in stored],
        "skipped": skipped,
        "signals": stored,
        "technical_details": {
            "study_id": study_id,
            "study_run_id": active_run["id"],
            "queries": GS001_REAL_EVIDENCE_QUERIES,
            "retrieved_at": retrieved_at,
            "skipped": skipped,
            "candidates": candidates,
        },
    }
    add_event(db_path, "GoldenStudyEvidencePulled", "PX-R001", message, str(len(stored)), study_id)
    return result


def normalize_provider_result(result: ProviderResult | object, query: str, retrieved_at: str) -> dict[str, object]:
    provider_name = str(getattr(result, "provider", "") or getattr(result, "name", "") or "Unknown Provider")
    title = str(getattr(result, "title", "") or "").strip()
    url = str(getattr(result, "url", "") or "").strip()
    snippet = str(getattr(result, "snippet", "") or "").strip()
    raw_text = snippet if snippet else ""
    quality = evidence_quality_profile(f"{title}\n{snippet}", query, url, title)
    source_type = normalize_source_type(str(getattr(result, "source_type", "") or ""), url, title)
    return {
        "provider_name": provider_name,
        "query": query,
        "retrieved_at": retrieved_at,
        "original_title": title,
        "source_url": url,
        "source_name": encode_provider_signal_metadata(provider_name, query, retrieved_at, title, quality),
        "source_type": source_type,
        "source_date": retrieved_at,
        "country": "United States",
        "stakeholder_type": infer_gs001_stakeholder(f"{title} {snippet}"),
        "raw_text": raw_text,
        "summary": summarize(snippet or title),
        "source_confidence": rough_provider_evidence_strength(provider_name, url, snippet),
        **quality,
    }


def encode_provider_signal_metadata(
    provider_name: str,
    original_query: str,
    retrieved_at: str,
    original_title: str,
    quality: dict[str, object] | None = None,
) -> str:
    metadata = {
        "metadata_type": "provider_evidence",
        "provider_name": provider_name,
        "original_query": original_query,
        "retrieved_at": retrieved_at,
        "original_title": original_title,
    }
    if quality:
        metadata.update(
            {
                "evidence_relevance": quality.get("evidence_relevance"),
                "classification": quality.get("classification"),
                "production_eligible": quality.get("production_eligible"),
                "source_type": quality.get("source_type_detected"),
                "source_trust_score": quality.get("source_trust_score"),
                "why_accepted": quality.get("why_accepted"),
                "pain_keywords_matched": quality.get("pain_keywords_matched", []),
                "context_keywords_matched": quality.get("context_keywords_matched", []),
            }
        )
    return json.dumps(metadata, sort_keys=True)


def keyword_matches(text: str, keywords: list[str]) -> list[str]:
    lower = text.lower()
    return [keyword for keyword in keywords if keyword in lower]


def detect_source_type(url: str = "", title: str = "", text: str = "") -> str:
    lower = " ".join([url, title, text]).lower()
    if any(word in lower for word in ["court", "filing", "lawsuit", "docket"]):
        return "court"
    if any(word in lower for word in ["gov", "regulator", "government", "attorney general"]):
        return "government"
    if "ombudsman" in lower:
        return "ombudsman"
    if any(word in lower for word in ["consumeraffairs", "consumer affairs", "bbb.org", "better business bureau"]):
        return "consumer_review"
    if any(word in lower for word in ["trustpilot", "g2.com", "capterra", "software advice"]):
        return "verified_review_platform"
    if any(word in lower for word in ["facebook", "discord", "instagram", "tiktok", "threads.net"]):
        return "facebook_group" if "facebook" in lower else "social_media"
    if any(word in lower for word in ["reddit", "linkedin", "x.com", "twitter"]):
        return "social_media"
    if any(word in lower for word in ["forum", "community"]):
        return "forum"
    if any(word in lower for word in ["research", "university", "institute", "white paper"]):
        return "research"
    if any(word in lower for word in ["news", "reuters", "apnews", "bbc", "guardian", "nyt", "wsj", "forbes"]):
        return "news"
    if any(word in lower for word in ["blog", "help.", "support.", "docs.", "features", "pricing", "demo", "vendor"]):
        return "vendor"
    if any(word in lower for word in ["marketing", "landing page", "sales page"]):
        return "marketing"
    return "unknown"


def source_trust_score(source_type: str, url: str = "", title: str = "", text: str = "") -> int:
    lower = " ".join([url, title, text]).lower()
    if "housing ombudsman" in lower:
        return 98
    if "consumer affairs" in lower or "consumeraffairs" in lower or "bbb.org" in lower or "better business bureau" in lower:
        return 95
    return SOURCE_TRUST_SCORES.get(source_type, 0)


def evidence_quality_profile(text: str, query: str = "", url: str = "", title: str = "") -> dict[str, object]:
    combined = text.strip()
    lower = combined.lower()
    source_type = detect_source_type(url, title, combined)
    trust_score = source_trust_score(source_type, url, title, combined)
    pain_matches = keyword_matches(combined, PAIN_KEYWORDS)
    context_matches = keyword_matches(combined, PROPERTY_MAINTENANCE_CONTEXT_KEYWORDS)
    strong_complaint = bool(pain_matches and context_matches)
    strong_pain_language = any(
        keyword in lower
        for keyword in [
            "complaint",
            "complain",
            "complains",
            "issue",
            "problem",
            "poor",
            "slow",
            "delayed",
            "no response",
            "unresolved",
            "waiting",
            "broken",
            "frustration",
            "dispute",
            "bad service",
            "ignored",
            "lack of communication",
            "not updated",
        ]
    )

    if source_type in {"vendor", "marketing"} or any(word in lower for word in ["book a demo", "request demo", "our platform", "software solution", "features include", "pricing page"]):
        classification = "vendor_content"
        relevance = "vendor_marketing"
        reason = "Vendor-authored guidance. Useful background information only."
    elif source_type in {"social_media", "facebook_group"}:
        classification = "community_signal"
        relevance = "unknown"
        reason = "Community discussion. Requires independent verification."
    elif any(word in lower for word in ["market size", "market report", "forecast", "cagr", "industry revenue", "statistics", "funding", "investment", "industry trends", "software trends"]):
        classification = "market_context"
        relevance = "market_size_only"
        reason = "Market context only; not direct complaint evidence."
    elif source_type == "research":
        classification = "research_report"
        relevance = "generic_article"
        reason = "Research report; background context only unless corroborated by complaint evidence."
    elif source_type == "news" and not strong_complaint:
        classification = "news_report"
        relevance = "generic_article"
        reason = "News report without direct complaint evidence."
    elif any(word in lower for word in ["article", "guide", "overview", "best practices", "tips"]) and not strong_pain_language:
        classification = "market_context"
        relevance = "generic_article"
        reason = "Generic article; useful context but not independent complaint evidence."
    elif any(word in lower for word in ["complaint", "complain", "complains", "bad service", "no response", "not updated"]):
        classification = "verified_complaint" if source_type in {"consumer_review", "verified_review_platform", "government", "court", "ombudsman", "news"} else "operational_pain"
        relevance = "complaint"
        reason = "Independent complaint matching GS-001." if classification == "verified_complaint" else "Complaint or pain evidence from a lower-trust source."
    elif any(word in lower for word in ["issue", "problem", "poor", "slow", "delayed", "unresolved", "waiting", "broken", "repair", "frustration", "dispute", "ignored"]):
        classification = "operational_pain"
        relevance = "operational_pain"
        reason = "Operational pain evidence matching GS-001."
    elif any(word in lower for word in ["manual", "workflow", "work order", "lack of communication", "maintenance request"]):
        classification = "workflow_inefficiency"
        relevance = "workflow_inefficiency"
        reason = "Workflow inefficiency evidence matching GS-001."
    else:
        classification = "unknown"
        relevance = "unknown"
        reason = "Unknown evidence class; not production eligible."

    production_eligible = classification in PRODUCTION_ELIGIBLE_CLASSIFICATIONS and bool(pain_matches) and bool(context_matches)
    if production_eligible:
        why = f"{reason} Matched pain keywords and property-maintenance context."
        skip_reason = ""
    elif classification in {"market_context", "vendor_content", "news_report", "research_report"}:
        why = reason
        skip_reason = "market_size_generic_or_marketing"
    elif classification == "community_signal":
        why = reason
        skip_reason = "not_complaint_or_pain_evidence"
    else:
        why = "Rejected: missing complaint/pain language or property-maintenance context."
        skip_reason = "not_complaint_or_pain_evidence"
    return {
        "classification": classification,
        "production_eligible": production_eligible,
        "source_type_detected": source_type,
        "source_trust_score": trust_score,
        "evidence_relevance": relevance,
        "pain_keywords_matched": pain_matches,
        "context_keywords_matched": context_matches,
        "why_accepted": why,
        "accepted_complaint_evidence": production_eligible,
        "skip_reason": skip_reason,
    }


def signal_quality_metadata(signal: dict[str, object]) -> dict[str, object]:
    metadata = provider_signal_metadata(signal)
    if metadata.get("classification") or metadata.get("evidence_relevance"):
        classification = metadata.get("classification") or {
            "complaint": "verified_complaint",
            "operational_pain": "operational_pain",
            "workflow_inefficiency": "workflow_inefficiency",
            "market_size_only": "market_context",
            "vendor_marketing": "vendor_content",
            "generic_article": "market_context",
        }.get(str(metadata.get("evidence_relevance") or ""), "unknown")
        production_eligible = bool(metadata.get("production_eligible"))
        if "production_eligible" not in metadata:
            production_eligible = classification in PRODUCTION_ELIGIBLE_CLASSIFICATIONS and bool(metadata.get("pain_keywords_matched")) and bool(metadata.get("context_keywords_matched"))
        return {
            "classification": classification,
            "production_eligible": production_eligible,
            "source_type_detected": metadata.get("source_type") or "unknown",
            "source_trust_score": int(metadata.get("source_trust_score") or 0),
            "evidence_relevance": metadata.get("evidence_relevance"),
            "pain_keywords_matched": metadata.get("pain_keywords_matched") or [],
            "context_keywords_matched": metadata.get("context_keywords_matched") or [],
            "why_accepted": metadata.get("why_accepted") or "",
            "accepted_complaint_evidence": production_eligible,
        }
    return evidence_quality_profile(
        f"{signal.get('source_name') or ''}\n{signal.get('summary') or ''}\n{signal.get('raw_text') or ''}",
        str(signal.get("query") or ""),
        str(signal.get("source_url") or ""),
        str(signal.get("source_name") or ""),
    )


def source_domain_or_identity(signal: dict[str, object]) -> str:
    url = str(signal.get("source_url") or "").strip()
    if url:
        parsed = urlparse(url)
        return parsed.netloc.lower().removeprefix("www.") or url
    return str(signal.get("source_name") or signal.get("id") or "unknown")


def is_accepted_production_signal(signal: dict[str, object]) -> bool:
    if bool(signal.get("is_demo")):
        return False
    if str(signal.get("data_origin") or "") == "demo":
        return False
    quality = signal_quality_metadata(signal)
    return bool(quality.get("production_eligible")) and quality.get("classification") in PRODUCTION_ELIGIBLE_CLASSIFICATIONS


def provider_signal_metadata(signal: dict[str, object]) -> dict[str, object]:
    raw = signal.get("source_name")
    if not isinstance(raw, str) or not raw.strip().startswith("{"):
        return {}
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    if isinstance(parsed, dict) and parsed.get("metadata_type") == "provider_evidence":
        return parsed
    return {}


def signal_trace_card_view_model(signal: dict[str, object]) -> dict[str, str]:
    metadata = provider_signal_metadata(signal)
    source_name = (
        signal.get("source_name")
        or signal.get("source_url")
        or metadata.get("provider_name")
        or "Unknown source"
    )
    if metadata.get("original_title"):
        source_name = metadata["original_title"]
    provider = metadata.get("provider_name") or signal.get("provider_name") or "Unknown provider"
    query = metadata.get("original_query") or signal.get("query") or "Not recorded"
    retrieved = metadata.get("retrieved_at") or signal.get("retrieved_at") or signal.get("source_date") or "Not recorded"
    raw_text = signal.get("raw_text") or signal.get("summary") or "No evidence quote recorded."
    quality = signal_quality_metadata(signal)
    return {
        "source_name": str(source_name),
        "provider": str(provider),
        "query": str(query),
        "retrieved": str(retrieved),
        "source_url": str(signal.get("source_url") or "No source URL"),
        "raw_text": str(raw_text),
        "country": str(signal.get("country") or "Unknown"),
        "stakeholder": str(signal.get("stakeholder_type") or "Unknown"),
        "verification_status": str(signal.get("verification_status") or "Not recorded"),
        "evidence_strength": str(signal.get("evidence_strength") or 0),
        "classification": str(quality.get("classification") or "unknown"),
        "source_type": str(quality.get("source_type_detected") or "unknown"),
        "source_trust_score": str(quality.get("source_trust_score") or 0),
        "production_eligible": "YES" if quality.get("production_eligible") else "NO",
        "evidence_relevance": str(quality.get("evidence_relevance") or "unknown"),
        "why_accepted": str(quality.get("why_accepted") or "Not recorded"),
        "pain_keywords_matched": ", ".join(str(item) for item in quality.get("pain_keywords_matched", []) or []) or "None",
        "context_keywords_matched": ", ".join(str(item) for item in quality.get("context_keywords_matched", []) or []) or "None",
    }


def configured_gs001_evidence_providers() -> list[object]:
    providers: list[object] = []
    for provider in [TavilySearchProvider(), SerpAPISearchProvider(), NewsAPIProvider()]:
        try:
            status = provider.status()
        except Exception:
            continue
        if getattr(status, "status", "") == "connected":
            providers.append(provider)
    return providers


def infer_gs001_stakeholder(text: str) -> str:
    lower = text.lower()
    if any(word in lower for word in ["tenant", "resident", "renter", "apartment"]):
        return "Tenant"
    if any(word in lower for word in ["property manager", "property management", "manager"]):
        return "Property Manager"
    if any(word in lower for word in ["owner", "landlord", "investor"]):
        return "Property Owner"
    if any(word in lower for word in ["hoa", "board", "association"]):
        return "HOA Board"
    if any(word in lower for word in ["contractor", "maintenance technician", "repair"]):
        return "Maintenance Contractor"
    if any(word in lower for word in ["software", "platform", "buyer", "vendor"]):
        return "Software Buyer"
    return "Unknown"


def normalize_source_type(source_type: str, url: str, title: str) -> str:
    lower = " ".join([source_type, url, title]).lower()
    if "news" in lower:
        return "news"
    if any(word in lower for word in ["forum", "reddit", "community"]):
        return "forum"
    if any(word in lower for word in ["review", "trustpilot", "g2", "capterra"]):
        return "review"
    if any(word in lower for word in ["article", "blog"]):
        return "article"
    if source_type:
        return "search_result"
    return "unknown"


def rough_provider_evidence_strength(provider_name: str, url: str, text: str) -> int:
    score = 45
    if url:
        score += 15
    if len(text) > 160:
        score += 15
    if any(word in text.lower() for word in ["complaint", "complain", "issue", "problem", "maintenance", "communication", "request"]):
        score += 15
    if provider_name.lower() in {"tavily", "serpapi", "newsapi"}:
        score += 10
    return min(score, 100)


def signal_duplicate_exists(db_path: str | Path, study_id: str, study_run_id: str, source_url: str, raw_text: str) -> bool:
    with connect(db_path) as connection:
        if source_url.strip():
            url_match = connection.execute(
                """
                SELECT COUNT(*) AS count FROM study_signals
                WHERE study_id = ? AND study_run_id = ? AND source_url = ?
                """,
                (study_id, study_run_id, source_url),
            ).fetchone()["count"]
            if int(url_match):
                return True
        text_match = connection.execute(
            """
            SELECT COUNT(*) AS count FROM study_signals
            WHERE study_id = ? AND study_run_id = ? AND raw_text = ?
            """,
            (study_id, study_run_id, raw_text),
        ).fetchone()["count"]
    return bool(int(text_match))


def run_audit_batch(db_path: str | Path, study_id: str = DEFAULT_STUDY_ID) -> list[dict[str, object]]:
    audits = []
    active_run = get_active_study_run(db_path, study_id)
    include_demo = bool(active_run and active_run.get("study_mode") == "demo")
    for finding in list_findings(db_path, study_id, include_demo=include_demo):
        demo_rehearsal_ready = bool(finding.get("is_demo")) and finding.get("status") == "Insufficient Evidence" and len(_loads_list(finding.get("representative_signals"))) >= 2
        if finding["status"] in {"pending_audit", "Demo Finding"} or demo_rehearsal_ready:
            audits.append(audit_finding(db_path, str(finding["id"])))
    return audits


def findings_feedback(findings: list[dict[str, object]]) -> tuple[str, str]:
    count = len(findings)
    if count:
        return "success", f"{count} findings generated"
    return "warning", "No findings generated. Need at least 2 supporting signals."


def audit_batch_feedback(audits: list[dict[str, object]], findings: list[dict[str, object]]) -> tuple[str, str]:
    count = len(audits)
    if count:
        return "success", f"{count} audits completed"
    demo_ready = any(bool(finding.get("is_demo")) and finding.get("status") in {"Demo Finding", "Demo Audited", "Demo Opportunity"} for finding in findings)
    if demo_ready:
        return "success", "Demo audit rehearsal completed safely."
    return "warning", "No auditable findings found"


def approval_feedback(opportunities: list[dict[str, object]], demo_present: bool = False) -> tuple[str, str]:
    count = len(opportunities)
    if count:
        if all(bool(opportunity.get("is_demo")) for opportunity in opportunities):
            return "success", f"{count} demo opportunities created"
        return "success", f"{count} opportunities approved"
    if demo_present:
        return "warning", "No demo opportunities available for rehearsal."
    return "warning", "No approved opportunities available"


def demo_warning_active(db_path: str | Path, study_id: str = DEFAULT_STUDY_ID) -> bool:
    return demo_records_count(db_path, study_id) > 0


def demo_records_count(
    db_path: str | Path,
    study_id: str = DEFAULT_STUDY_ID,
    study_run_id: str | None = None,
    include_archived: bool = False,
) -> int:
    run_id = study_run_id or str((get_active_study_run(db_path, study_id) or {}).get("id") or "")
    archived_sql = "" if include_archived else "AND status != 'archived'"
    with connect(db_path) as connection:
        total = 0
        for table_name in ["study_signals", "study_findings", "finding_audits", "opportunity_records"]:
            total += int(
                connection.execute(
                    f"SELECT COUNT(*) AS count FROM {table_name} WHERE study_id = ? AND study_run_id = ? AND is_demo = 1 {archived_sql}",
                    (study_id, run_id),
                ).fetchone()["count"]
            )
    return total


def non_demo_records_count(
    db_path: str | Path,
    study_id: str = DEFAULT_STUDY_ID,
    study_run_id: str | None = None,
    include_archived: bool = False,
) -> int:
    run_id = study_run_id or str((get_active_study_run(db_path, study_id) or {}).get("id") or "")
    archived_sql = "" if include_archived else "AND status != 'archived'"
    with connect(db_path) as connection:
        total = 0
        for table_name in ["study_signals", "study_findings", "finding_audits", "opportunity_records"]:
            total += int(
                connection.execute(
                    f"SELECT COUNT(*) AS count FROM {table_name} WHERE study_id = ? AND study_run_id = ? AND is_demo = 0 {archived_sql}",
                    (study_id, run_id),
                ).fetchone()["count"]
            )
    return total


def run_filter(study_id: str, study_run_id: str, include_archived: bool, include_demo: bool) -> tuple[str, tuple[object, ...]]:
    clauses = ["study_id = ?", "study_run_id = ?"]
    params: list[object] = [study_id, study_run_id]
    if not include_archived:
        clauses.append("status != 'archived'")
    if not include_demo:
        clauses.append("is_demo = 0")
    return " AND ".join(clauses), tuple(params)


def validate_golden_study_integrity(db_path: str | Path, study_id: str = DEFAULT_STUDY_ID) -> dict[str, object]:
    study = get_study(db_path, study_id)
    active_run = get_active_study_run(db_path, study_id)
    active_run_id = str((active_run or {}).get("id") or "")
    signals = list_signals(db_path, study_id, active_run_id, include_archived=False, include_demo=True)
    findings = list_findings(db_path, study_id, active_run_id, include_archived=False, include_demo=True)
    audits = list_finding_audits(db_path, study_id, active_run_id, include_archived=False, include_demo=True)
    opportunities = list_opportunities(db_path, study_id, active_run_id, include_archived=False, include_demo=True)
    production_progress = study_progress(db_path, study_id, active_run_id, include_archived=False, include_demo=False)
    checks = []
    def check(name: str, passed: bool, recommended_fix: str, **extra: object) -> None:
        row = {"check": name, "passed": passed, "recommended_fix": "" if passed else recommended_fix}
        row.update(extra)
        checks.append(row)

    runs = list_study_runs(db_path, study_id)
    active_runs = [run for run in runs if run.get("status") == "active"]
    check(
        "Only one active run exists per study",
        len(active_runs) == 1,
        "Close duplicate active study runs so only one run is active.",
        active_count=len(active_runs),
    )
    for table_name in RUN_SCOPED_TABLES:
        missing = missing_run_id_count(db_path, table_name, study_id)
        check(
            f"All {table_name} records belong to a study run",
            missing == 0,
            f"Assign legacy {table_name} rows to their demo or production study run.",
            missing_count=missing,
        )
    production_mode = str((active_run or study or {}).get("study_mode") or "demo") == "production"
    active_records = [*signals, *findings, *audits, *opportunities]
    check(
        "Active production run contains no demo records",
        not production_mode or not any(bool(row.get("is_demo")) and row.get("status") != "archived" for row in active_records),
        "Switch to a clean production run or archive demo records under their demo run.",
    )
    check(
        "Production KPIs exclude demo and archived records",
        not production_mode or (production_progress["demo_records_count"] == 0 and production_progress["archived_count"] == 0),
        "Calculate production KPIs from the active production run with include_demo=False and include_archived=False.",
    )
    check(
        "Engineering Ready metrics are active production only",
        not production_mode or all(
            not bool(row.get("is_demo")) and row.get("study_run_id") == active_run_id and row.get("status") != "archived"
            for row in production_progress["engineering_ready"]
        ),
        "Filter Engineering Ready metrics to the active production run only.",
    )
    check(
        "OCI metrics are active production only",
        not production_mode or all(
            not bool(row.get("is_demo")) and row.get("study_run_id") == active_run_id and row.get("status") != "archived"
            for row in production_progress["top_opportunities"]
        ),
        "Filter OCI metrics to active non-demo production opportunities.",
    )
    check(
        "No demo record is approved",
        not production_mode or not any(bool(row.get("is_demo")) and row.get("status") in {"Approved Opportunity", "Engineering Ready", "opportunity_approved"} for row in active_records),
        "Archive demo records and rerun approval with non-demo evidence only.",
    )
    check(
        "No demo record is Engineering Ready",
        not production_mode or not any(bool(row.get("is_demo")) and (row.get("engineering_status") == "Engineering Ready" or row.get("status") == "Engineering Ready") for row in opportunities),
        "Remove Engineering Ready status from demo records and archive them.",
    )
    for signal in signals:
        if not bool(signal.get("is_demo")) and signal.get("status") != "archived":
            check(
                f"Non-demo signal {signal['id']} has source",
                bool(signal.get("source_url") or signal.get("source_name")),
                "Add a source URL or source name to the signal.",
            )
    for finding in findings:
        check(
            f"Finding {finding['id']} links to signals",
            bool(_loads_list(finding.get("representative_signals"))),
            "Regenerate findings from sourced signals.",
        )
    for audit in audits:
        check(f"Audit {audit['id']} links to finding", bool(audit.get("finding_id")), "Rerun audit from a valid finding.")
        check(f"Audit {audit['id']} has explainable OCI", bool(audit.get("score_breakdown") and audit.get("oci_reasoning")), "Rerun audit to create score breakdown and reasoning.")
        check(f"Demo audit {audit['id']} is not approved", not production_mode or not (bool(audit.get("is_demo")) and audit.get("decision") == "Approve Opportunity"), "Archive demo audit and approve only non-demo evidence.")
    for opportunity in opportunities:
        try:
            chain = traceability_chain(db_path, str(opportunity["id"]), include_archived=False)
            chain_complete = bool(chain["audit"] and chain["finding"] and chain["signals"] and chain["sources"])
            non_demo = not any(bool(record.get("is_demo")) for record in [chain["opportunity"], chain["audit"], chain["finding"], *chain["signals"]])
            source_complete = all(source.get("source_url") or source.get("source_name") for source in chain["sources"])
        except Exception:
            chain_complete = False
            non_demo = False
            source_complete = False
        required = ["recommended_component", "engineering_recommendation", "problem_scope", "target_users", "required_inputs", "expected_outputs", "system_boundaries"]
        missing_engineering = [field for field in required if not opportunity.get(field)]
        check(f"Opportunity {opportunity['id']} links to audit", bool(opportunity.get("audit_id")), "Recreate opportunity from an audited finding.")
        check(f"Opportunity {opportunity['id']} traces to sources", chain_complete and source_complete, "View Evidence Chain and add missing source metadata.")
        check(f"Opportunity {opportunity['id']} uses non-demo evidence", non_demo, "Archive demo evidence and approve from production evidence only.")
        check(
            f"Engineering Ready {opportunity['id']} has required fields",
            opportunity.get("engineering_status") != "Engineering Ready" or not missing_engineering,
            f"Complete engineering fields: {', '.join(missing_engineering)}.",
        )
    archived_preserved = True
    with connect(db_path) as connection:
        archived_rows = connection.execute("SELECT COUNT(*) AS count FROM demo_archive").fetchone()["count"]
        archived_demo_runs = connection.execute("SELECT COUNT(*) AS count FROM study_runs WHERE study_id = ? AND study_mode = 'demo' AND status IN ('closed', 'archived')", (study_id,)).fetchone()["count"]
    check("Archived demo records are preserved", archived_preserved, "Do not hard-delete archived demo records.", count=int(archived_rows))
    check("Archived demo run remains traceable", int(archived_demo_runs) > 0 or production_mode is False, "Close demo runs instead of deleting them when switching to production.", count=int(archived_demo_runs))
    failed = [check for check in checks if not check["passed"]]
    return {"passed": not failed, "failed_count": len(failed), "checks": checks}


def missing_run_id_count(db_path: str | Path, table_name: str, study_id: str) -> int:
    if table_name not in RUN_SCOPED_TABLES:
        raise ValueError(f"Unsupported run scoped table: {table_name}")
    with connect(db_path) as connection:
        return int(
            connection.execute(
                f"SELECT COUNT(*) AS count FROM {table_name} WHERE study_id = ? AND (study_run_id IS NULL OR study_run_id = '')",
                (study_id,),
            ).fetchone()["count"]
        )


def normalize_data_origin(data_origin: str) -> str:
    return data_origin if data_origin in {"demo", "manual", "verified_import", "provider"} else "demo"


def provenance_values(data_origin: str, worker_id: str, source_confidence: float | None = None) -> dict[str, object]:
    origin = normalize_data_origin(data_origin)
    is_demo = origin == "demo"
    verification_status = "unverified" if is_demo else "pending_review"
    return {
        "data_origin": origin,
        "verification_status": verification_status,
        "is_demo": is_demo,
        "source_confidence": source_confidence,
        "created_by_worker": worker_id,
    }


def _loads_list(raw: object) -> list[object]:
    if not raw:
        return []
    try:
        parsed = json.loads(str(raw))
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []
