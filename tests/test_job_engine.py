from project_exchange.database import fetch_all, init_db
from project_exchange.eos import (
    JobStatus,
    JobType,
    complete_sprint_milestone,
    create_job,
    execute_job,
    job_queue_counts,
    list_failure_history,
    list_jobs,
    list_system_logs,
    retry_job,
    system_analytics,
)


def test_job_lifecycle_and_worker_orchestration(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    job = create_job(
        db_path,
        JobType.RESEARCH_SCAN.value,
        "PX-R001",
        {
            "market": "Property Management",
            "company": "PropertyMe",
            "source_url": "https://example.com/review",
            "source_name": "Verified tenant maintenance communication complaint record",
            "source_text": (
                "Users repeatedly complain that maintenance updates are slow, repair requests remain unresolved, "
                "and tenants chase support multiple times across the documented servicing workflow."
            ),
        },
        priority=1,
    )
    assert job["status"] == JobStatus.PENDING.value

    finished = execute_job(db_path, str(job["id"]))
    assert finished["status"] == JobStatus.COMPLETED.value

    jobs = list_jobs(db_path)
    assert len(jobs) == 3
    assert all(record["status"] == JobStatus.COMPLETED.value for record in jobs)

    event_types = {record["event_type"] for record in fetch_all(db_path, "events")}
    assert {"JobCreated", "JobStarted", "JobFinished", "ResearchCreated", "AuditApproved", "LibraryStored"} <= event_types
    assert job_queue_counts(db_path)[JobStatus.COMPLETED.value] == 3
    assert list_system_logs(db_path)

    analytics = system_analytics(db_path)
    assert analytics["jobs_completed"] == 3
    assert analytics["research_processed"] == 1
    assert analytics["library_growth"] == 1


def test_job_failure_retry_and_recovery_history(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    job = create_job(db_path, JobType.AUDIT_SCAN.value, "PX-A001", {"research_id": "missing"})
    failed = execute_job(db_path, str(job["id"]))
    assert failed["status"] == JobStatus.FAILED.value
    assert list_failure_history(db_path, str(job["id"]))

    retried = retry_job(db_path, str(job["id"]))
    assert retried["status"] == JobStatus.PENDING.value
    assert retried["retries"] == 1


def test_sprint_milestone_auto_journal(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    milestone = complete_sprint_milestone(
        db_path,
        "Sprint 4",
        "Autonomous Execution Layer",
        "Job Engine and execution primitives added.",
        "project_exchange/eos.py",
        components_added="Job Engine",
        version="v4.0",
    )

    assert milestone["id"].startswith("M-")
    journals = fetch_all(db_path, "engineering_journal")
    assert any("Completed Sprint 4" in record["title"] for record in journals)
