from project_exchange.command_console import run_command
from project_exchange.database import fetch_all, init_db
from project_exchange.head_of_functions import (
    generate_system_recommendations,
    list_execution_plans,
    list_worker_memory,
    monitor_and_recover,
    refresh_worker_memory,
)
from project_exchange.os_services import list_worker_messages, route_worker_message
from workers.px_a001_audit.audit_engine import run_audit


def test_px_h001_seeded_and_command_creates_plan(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    workers = {record["id"] for record in fetch_all(db_path, "workers")}
    assert "PX-H001" in workers

    result = run_command(db_path, "Summarise Library.")
    assert result["head_of_functions"]["id"].startswith("PLAN-")
    assert list_execution_plans(db_path)


def test_px_h001_owns_jobs_and_refreshes_memory(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    result = run_command(db_path, "Research Property Management software.")
    assert result["job"]["status"] == "Completed"

    jobs = fetch_all(db_path, "jobs")
    assert jobs
    assert all(job["created_by"] == "PX-H001" for job in jobs)
    assert any(job["history"] for job in jobs)

    memory = refresh_worker_memory(db_path)
    assert {record["worker_id"] for record in memory} >= {"PX-H001", "PX-R001", "PX-A001", "PX-L001"}
    assert list_worker_memory(db_path)


def test_worker_messages_route_through_head_of_functions(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    routed = route_worker_message(db_path, "PX-R001", "PX-A001", "Research ready.", priority=1, payload={"research_id": "RES-X"})
    assert routed["inbound"]["receiver_worker"] == "PX-H001"
    assert routed["outbound"]["sender_worker"] == "PX-H001"

    messages = list_worker_messages(db_path)
    assert len(messages) == 2
    assert messages[0]["priority"] == 1
    assert messages[0]["status"] in {"sent", "received"}


def test_audit_reasoning_and_recommendations_are_persistent(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    research = {
        "id": "RES-TEST-0001",
        "market": "Property Management",
        "company": "PropertyMe",
        "source_url": "https://example.com/review",
        "source_text": "Users complain that maintenance repair updates are slow and tenants have to chase responses repeatedly.",
        "complaint_summary": "Maintenance repair updates are slow and tenants chase responses repeatedly.",
        "workflow_cluster": "Maintenance Communication",
        "evidence_score": 85,
    }
    audit = run_audit(db_path, research)
    assert audit["audit_id"]
    assert fetch_all(db_path, "audit_reasoning")

    recommendations = generate_system_recommendations(db_path)
    assert recommendations
    assert fetch_all(db_path, "system_recommendations")


def test_head_of_functions_recovery_scan(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    result = monitor_and_recover(db_path)
    assert result["count"] == 0
