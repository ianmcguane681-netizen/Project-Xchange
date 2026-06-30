from project_exchange.database import fetch_all, init_db
from project_exchange.eos import (
    add_journal_entry,
    add_milestone,
    component_registry,
    dashboard_metrics,
    list_events,
    list_journal_entries,
    list_milestones,
    pipeline_snapshot,
    worker_registry,
)
from workers.px_a001_audit.audit_engine import run_audit
from workers.px_l001_library.library_manager import store_approved_record
from workers.px_r001_research.research_scanner import run_market_scan


def test_event_bus_and_registries(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    research = run_market_scan(
        db_path,
        market="Property Management",
        company="PropertyMe",
        source_url="https://example.com/review",
        source_text="Users repeatedly complain that maintenance updates are delayed and support responses are slow.",
    )
    audit = run_audit(db_path, research)
    library = store_approved_record(db_path, audit, research)

    event_types = {event["event_type"] for event in list_events(db_path)}
    assert {"ResearchCreated", "AuditApproved", "LibraryStored", "WorkerStarted", "WorkerFinished"} <= event_types
    assert list_events(db_path, worker_id="PX-A001")
    assert worker_registry(db_path)[0]["jobs_completed"] is not None
    assert component_registry(db_path)[0]["version"] == "v3.0"
    assert library["library_id"].startswith("LIB-")


def test_milestones_journal_dashboard_and_pipeline(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    milestone = add_milestone(
        db_path,
        "M-9999",
        "Test Sprint",
        "Test Milestone",
        "Verifies milestone logging.",
        "PX-E002",
        "tests/test_eos.py",
        "Completed",
    )
    journal = add_journal_entry(
        db_path,
        "Test Architecture Decision",
        "Architecture Decision",
        "Events are the durable communication layer.",
        "PX-EOS",
    )

    metrics = dashboard_metrics(db_path)
    assert metrics["worker_count"] == 4
    assert metrics["current_milestone"]
    assert milestone["id"] == "M-9999"
    assert journal["title"] == "Test Architecture Decision"
    assert any(record["id"] == "M-9999" for record in list_milestones(db_path))
    assert list_journal_entries(db_path)
    assert len(pipeline_snapshot(db_path)) == 6
    assert fetch_all(db_path, "events")
