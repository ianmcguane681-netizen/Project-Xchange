from project_exchange.database import init_db
from project_exchange.eos import dashboard_metrics, list_activity, list_notifications, pending_audit_queue
from workers.px_a001_audit.audit_engine import run_audit
from workers.px_l001_library.library_manager import search_library_records, store_approved_record
from workers.px_r001_research.research_scanner import run_market_scan


def test_research_audit_library_workflow(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    research = run_market_scan(
        db_path,
        market="Property Management",
        company="PropertyMe",
        source_url="https://example.com/review",
        source_text="Users repeatedly complain that maintenance repair updates are slow and tenants have to chase responses multiple times.",
    )
    assert len(pending_audit_queue(db_path)) == 1

    audit = run_audit(db_path, research)
    assert audit["decision"] == "approved"
    assert audit["send_to_library"] is True
    assert audit["evidence_checklist"]["source_present"] is True

    library = store_approved_record(db_path, audit, research)
    assert library["status"] == "stored"
    assert library["library_id"].startswith("LIB-")
    assert search_library_records(db_path, "maintenance")

    metrics = dashboard_metrics(db_path)
    assert metrics["library_records"] == 1
    assert metrics["system_health"] == "Healthy"
    assert len(list_activity(db_path)) == 3
    assert len(list_notifications(db_path)) == 3


def test_audit_needs_evidence_without_source(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    research = {
        "id": "RES-TEST-0001",
        "market": "Property Management",
        "company": "PropertyMe",
        "source_url": "",
        "complaint_summary": "Maintenance updates are slow.",
        "workflow_cluster": "Maintenance Communication",
        "evidence_score": 80,
    }

    audit = run_audit(db_path, research)
    assert audit["decision"] == "needs_evidence"
    assert audit["source_verified"] is False
