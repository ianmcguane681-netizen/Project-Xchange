from __future__ import annotations

import json
import time
import traceback
from contextlib import contextmanager
try:
    from enum import StrEnum
except ImportError:  # Python 3.10 Streamlit Cloud compatibility.
    from enum import Enum

    class StrEnum(str, Enum):
        pass
from pathlib import Path
from typing import Iterator

from project_exchange.database import connect, count_rows, row_to_dict, utc_now
from project_exchange.ids import next_sequence_id


SYSTEM_STARTED_AT = time.perf_counter()


class WorkerStatus(StrEnum):
    IDLE = "Idle"
    WORKING = "Working"
    RUNNING = "Running"
    WAITING = "Waiting"
    OFFLINE = "Offline"
    PAUSED = "Paused"
    FAILED = "Failed"
    COMPLETED = "Completed"


class JobStatus(StrEnum):
    PENDING = "Pending"
    RUNNING = "Running"
    WAITING = "Waiting"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"


class JobType(StrEnum):
    RESEARCH_SCAN = "Research Scan"
    INTERNET_RESEARCH = "Internet Research"
    AUDIT_SCAN = "Audit Scan"
    LIBRARY_STORE = "Library Store"
    PROMPT_TEST = "Prompt Test"
    PROMPT_APPROVAL = "Prompt Approval"
    COMPONENT_BUILD = "Component Build"
    WORKER_UPDATE = "Operator Update"
    SYSTEM_SCAN = "System Scan"


def set_worker_status(db_path: str | Path, worker_id: str, status: WorkerStatus) -> None:
    with connect(db_path) as connection:
        connection.execute(
            "UPDATE workers SET status = ? WHERE id = ?",
            (status.value, worker_id),
        )


def add_notification(
    db_path: str | Path,
    event_type: str,
    message: str,
    entity_id: str | None = None,
    severity: str = "info",
) -> None:
    with connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO notifications (event_type, message, entity_id, severity, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (event_type, message, entity_id, severity, utc_now()),
        )
    add_event(db_path, event_type, None, event_type, message, entity_id=entity_id, success=True)


def add_event(
    db_path: str | Path,
    event_type: str,
    worker_id: str | None,
    action: str,
    result: str | None = None,
    entity_id: str | None = None,
    duration_ms: int | None = None,
    success: bool = True,
    error: str | None = None,
    payload: dict[str, object] | None = None,
) -> None:
    with connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO events
            (event_type, worker_id, action, result, entity_id, duration_ms, success, error, payload, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_type,
                worker_id,
                action,
                result,
                entity_id,
                duration_ms,
                1 if success else 0,
                error,
                json.dumps(payload or {}, ensure_ascii=False),
                utc_now(),
            ),
        )


def add_log(
    db_path: str | Path,
    severity: str,
    details: str,
    worker_id: str | None = None,
    job_id: str | None = None,
    duration_ms: int | None = None,
    status: str | None = None,
) -> None:
    with connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO system_logs (timestamp, worker_id, job_id, severity, duration_ms, details, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (utc_now(), worker_id, job_id, severity, duration_ms, details, status),
        )


def create_job(
    db_path: str | Path,
    job_type: str,
    assigned_worker: str | None = None,
    payload: dict[str, object] | None = None,
    priority: int = 3,
    max_retries: int = 2,
    dependencies: list[str] | None = None,
    parent_job_id: str = "",
    created_by: str = "PX-H001",
) -> dict[str, object]:
    with connect(db_path) as connection:
        job_id = next_sequence_id("JOB", count_rows(connection, "jobs"))
        now = utc_now()
        history = [{"timestamp": now, "status": JobStatus.PENDING.value, "actor": created_by, "message": "Job created"}]
        connection.execute(
            """
            INSERT INTO jobs
            (id, job_type, priority, status, assigned_worker, payload, dependencies, history, parent_job_id,
             created_by, retries, max_retries, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                job_type,
                priority,
                JobStatus.PENDING.value,
                assigned_worker,
                json.dumps(payload or {}, ensure_ascii=False),
                json.dumps(dependencies or [], ensure_ascii=False),
                json.dumps(history, ensure_ascii=False),
                parent_job_id,
                created_by,
                0,
                max_retries,
                now,
            ),
        )
    add_event(db_path, "JobCreated", assigned_worker, "Job created", JobStatus.PENDING.value, job_id, payload=payload)
    add_log(db_path, "info", f"Created job {job_id}: {job_type}", assigned_worker, job_id, status=JobStatus.PENDING.value)
    return get_job(db_path, job_id)


def get_job(db_path: str | Path, job_id: str) -> dict[str, object]:
    with connect(db_path) as connection:
        row = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if row is None:
        raise ValueError(f"Job not found: {job_id}")
    job = row_to_dict(row)
    job["payload_dict"] = _loads(job.get("payload"))
    job["result_dict"] = _loads(job.get("result"))
    return job


def list_jobs(db_path: str | Path, status: str = "", worker_id: str = "", limit: int = 200) -> list[dict[str, object]]:
    clauses = []
    values: list[object] = []
    if status:
        clauses.append("status = ?")
        values.append(status)
    if worker_id:
        clauses.append("assigned_worker = ?")
        values.append(worker_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    values.append(limit)
    with connect(db_path) as connection:
        rows = connection.execute(
            f"SELECT * FROM jobs {where} ORDER BY priority ASC, created_at DESC LIMIT ?",
            values,
        ).fetchall()
    return [row_to_dict(row) for row in rows]


def job_queue_counts(db_path: str | Path) -> dict[str, int]:
    counts = {status.value: 0 for status in JobStatus}
    with connect(db_path) as connection:
        rows = connection.execute("SELECT status, COUNT(*) AS count FROM jobs GROUP BY status").fetchall()
    for row in rows:
        counts[row["status"]] = int(row["count"])
    return counts


def start_job(db_path: str | Path, job_id: str) -> dict[str, object]:
    now = utc_now()
    job = get_job(db_path, job_id)
    with connect(db_path) as connection:
        connection.execute(
            "UPDATE jobs SET status = ?, started_at = COALESCE(started_at, ?) WHERE id = ?",
            (JobStatus.RUNNING.value, now, job_id),
        )
    if job.get("assigned_worker"):
        set_worker_status(db_path, str(job["assigned_worker"]), WorkerStatus.WORKING)
    add_event(db_path, "JobStarted", str(job.get("assigned_worker") or ""), "Job started", JobStatus.RUNNING.value, job_id)
    add_log(db_path, "info", f"Started job {job_id}", str(job.get("assigned_worker") or ""), job_id, status=JobStatus.RUNNING.value)
    append_job_history(db_path, job_id, JobStatus.RUNNING.value, str(job.get("assigned_worker") or "PX-H001"), "Job started")
    return get_job(db_path, job_id)


def complete_job(db_path: str | Path, job_id: str, result: dict[str, object] | None = None) -> dict[str, object]:
    job = get_job(db_path, job_id)
    duration_ms = duration_from_started(job)
    with connect(db_path) as connection:
        connection.execute(
            """
            UPDATE jobs
            SET status = ?, result = ?, finished_at = ?, duration_ms = ?
            WHERE id = ?
            """,
            (JobStatus.COMPLETED.value, json.dumps(result or {}, ensure_ascii=False), utc_now(), duration_ms, job_id),
        )
    if job.get("assigned_worker"):
        set_worker_status(db_path, str(job["assigned_worker"]), WorkerStatus.IDLE)
    add_event(db_path, "JobFinished", str(job.get("assigned_worker") or ""), "Job finished", JobStatus.COMPLETED.value, job_id, duration_ms=duration_ms, payload=result)
    add_log(db_path, "info", f"Completed job {job_id}", str(job.get("assigned_worker") or ""), job_id, duration_ms, JobStatus.COMPLETED.value)
    append_job_history(db_path, job_id, JobStatus.COMPLETED.value, str(job.get("assigned_worker") or "PX-H001"), "Job completed")
    return get_job(db_path, job_id)


def fail_job(
    db_path: str | Path,
    job_id: str,
    error: str,
    stack_trace: str = "",
    recovery_suggestion: str = "Review the input, then retry the job.",
) -> dict[str, object]:
    job = get_job(db_path, job_id)
    duration_ms = duration_from_started(job)
    with connect(db_path) as connection:
        connection.execute(
            """
            UPDATE jobs
            SET status = ?, failure_reason = ?, recovery_suggestion = ?, finished_at = ?, duration_ms = ?
            WHERE id = ?
            """,
            (JobStatus.FAILED.value, error, recovery_suggestion, utc_now(), duration_ms, job_id),
        )
        connection.execute(
            """
            INSERT INTO failure_history (job_id, worker_id, error, stack_trace, recovery_suggestion, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (job_id, job.get("assigned_worker"), error, stack_trace, recovery_suggestion, utc_now()),
        )
    if job.get("assigned_worker"):
        set_worker_status(db_path, str(job["assigned_worker"]), WorkerStatus.FAILED)
    add_event(db_path, "Error", str(job.get("assigned_worker") or ""), "Job failed", JobStatus.FAILED.value, job_id, duration_ms=duration_ms, success=False, error=error)
    add_log(db_path, "error", error, str(job.get("assigned_worker") or ""), job_id, duration_ms, JobStatus.FAILED.value)
    append_job_history(db_path, job_id, JobStatus.FAILED.value, str(job.get("assigned_worker") or "PX-H001"), error)
    return get_job(db_path, job_id)


def retry_job(db_path: str | Path, job_id: str) -> dict[str, object]:
    job = get_job(db_path, job_id)
    retries = int(job.get("retries") or 0)
    max_retries = int(job.get("max_retries") or 0)
    if retries >= max_retries:
        raise ValueError(f"Job {job_id} has reached max retries")
    with connect(db_path) as connection:
        connection.execute(
            """
            UPDATE jobs
            SET status = ?, retries = retries + 1, failure_reason = NULL, recovery_suggestion = NULL,
                started_at = NULL, finished_at = NULL, duration_ms = NULL
            WHERE id = ?
            """,
            (JobStatus.PENDING.value, job_id),
        )
    add_event(db_path, "JobRetried", str(job.get("assigned_worker") or ""), "Job queued for retry", JobStatus.PENDING.value, job_id)
    add_log(db_path, "warning", f"Retry queued for job {job_id}", str(job.get("assigned_worker") or ""), job_id, status=JobStatus.PENDING.value)
    append_job_history(db_path, job_id, JobStatus.PENDING.value, "PX-H001", "Job queued for retry")
    return get_job(db_path, job_id)


def cancel_job(db_path: str | Path, job_id: str) -> dict[str, object]:
    job = get_job(db_path, job_id)
    with connect(db_path) as connection:
        connection.execute(
            "UPDATE jobs SET status = ?, finished_at = ? WHERE id = ?",
            (JobStatus.CANCELLED.value, utc_now(), job_id),
        )
    add_event(db_path, "JobCancelled", str(job.get("assigned_worker") or ""), "Job cancelled", JobStatus.CANCELLED.value, job_id)
    add_log(db_path, "warning", f"Cancelled job {job_id}", str(job.get("assigned_worker") or ""), job_id, status=JobStatus.CANCELLED.value)
    append_job_history(db_path, job_id, JobStatus.CANCELLED.value, "PX-H001", "Job cancelled")
    return get_job(db_path, job_id)


def resume_job(db_path: str | Path, job_id: str) -> dict[str, object]:
    with connect(db_path) as connection:
        connection.execute(
            "UPDATE jobs SET status = ?, failure_reason = NULL, recovery_suggestion = NULL WHERE id = ?",
            (JobStatus.PENDING.value, job_id),
        )
    add_event(db_path, "JobResumed", None, "Job resumed", JobStatus.PENDING.value, job_id)
    append_job_history(db_path, job_id, JobStatus.PENDING.value, "PX-H001", "Job resumed")
    return get_job(db_path, job_id)


def append_job_history(db_path: str | Path, job_id: str, status: str, actor: str, message: str) -> None:
    job = get_job(db_path, job_id)
    history = []
    raw_history = job.get("history")
    if raw_history:
        try:
            parsed = json.loads(str(raw_history))
            history = parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            history = []
    history.append({"timestamp": utc_now(), "status": status, "actor": actor, "message": message})
    with connect(db_path) as connection:
        connection.execute(
            "UPDATE jobs SET history = ? WHERE id = ?",
            (json.dumps(history, ensure_ascii=False), job_id),
        )


def restart_worker(db_path: str | Path, worker_id: str) -> None:
    set_worker_status(db_path, worker_id, WorkerStatus.IDLE)
    add_event(db_path, "WorkerRestarted", worker_id, "Worker restarted", WorkerStatus.IDLE.value, worker_id)
    add_log(db_path, "warning", f"Restarted worker {worker_id}", worker_id, status=WorkerStatus.IDLE.value)


def execute_job(db_path: str | Path, job_id: str) -> dict[str, object]:
    job = start_job(db_path, job_id)
    payload = _loads(job.get("payload"))
    try:
        result = dispatch_job(db_path, str(job["job_type"]), payload)
    except Exception as exc:
        return fail_job(
            db_path,
            job_id,
            str(exc),
            traceback.format_exc(),
            recovery_suggestion_for(str(job["job_type"]), str(exc)),
        )
    return complete_job(db_path, job_id, result)


def dispatch_job(db_path: str | Path, job_type: str, payload: dict[str, object]) -> dict[str, object]:
    if job_type in {JobType.RESEARCH_SCAN.value, JobType.INTERNET_RESEARCH.value}:
        from project_exchange.os_services import add_knowledge_edge, send_worker_message
        from project_exchange.research_engine import run_internet_research

        result = run_internet_research(db_path, payload)
        research = result["research"]
        package = result["package"]
        add_knowledge_edge(db_path, "research", str(research["id"]), "created_package", "research_package", str(package["id"]))
        audit_job = create_job(
            db_path,
            JobType.AUDIT_SCAN.value,
            "PX-A001",
            {"research_id": research["id"]},
            priority=2,
        )
        send_worker_message(db_path, "PX-R001", "PX-A001", f"Research {research['id']} ready for audit.", str(audit_job["id"]))
        audit_result = execute_job(db_path, str(audit_job["id"]))
        return {"research": research, "package": package, "next_job": audit_result}

    if job_type == JobType.AUDIT_SCAN.value:
        from project_exchange.os_services import add_knowledge_edge, send_worker_message
        from workers.px_a001_audit.audit_engine import run_audit
        from workers.px_r001_research.research_scanner import list_research_records

        research_id = str(payload.get("research_id") or "")
        research = next((record for record in list_research_records(db_path) if record["id"] == research_id), None)
        if not research:
            raise ValueError(f"Research record not found: {research_id}")
        audit = run_audit(db_path, research)
        add_knowledge_edge(db_path, "research", research_id, "audited_by", "audit", str(audit["audit_id"]))
        if audit.get("send_to_library"):
            library_job = create_job(
                db_path,
                JobType.LIBRARY_STORE.value,
                "PX-L001",
                {"audit_id": audit["audit_id"], "research_id": research_id},
                priority=2,
            )
            send_worker_message(db_path, "PX-A001", "PX-L001", f"Audit {audit['audit_id']} approved for Library storage.", str(library_job["id"]))
            library_result = execute_job(db_path, str(library_job["id"]))
            return {"audit": audit, "next_job": library_result}
        return {"audit": audit}

    if job_type == JobType.LIBRARY_STORE.value:
        from project_exchange.os_services import add_knowledge_edge, send_worker_message
        from workers.px_a001_audit.audit_engine import list_audit_records
        from workers.px_l001_library.library_manager import store_approved_record
        from workers.px_r001_research.research_scanner import list_research_records

        audit_id = str(payload.get("audit_id") or "")
        research_id = str(payload.get("research_id") or "")
        audit_row = next((record for record in list_audit_records(db_path) if record["id"] == audit_id), None)
        research = next((record for record in list_research_records(db_path) if record["id"] == research_id), None)
        if not audit_row or not research:
            raise ValueError("Matching audit and research records are required for Library Store")
        audit_report = {
            "audit_id": audit_row["id"],
            "research_id": audit_row["research_id"],
            "decision": audit_row["decision"],
            "send_to_library": audit_row["decision"] == "approved",
        }
        library = store_approved_record(db_path, audit_report, research)
        add_knowledge_edge(db_path, "audit", audit_id, "stored_as", "library", str(library["library_id"]))
        send_worker_message(db_path, "PX-L001", "COMP-001", f"Library record {library['library_id']} stored; prompts may be evaluated against this evidence.")
        return {"library": library}

    if job_type == JobType.PROMPT_TEST.value:
        from components.comp_001_prompt_engine.prompt_engine import run_prompt_test

        return {
            "prompt_test": run_prompt_test(
                db_path,
                str(payload.get("prompt_id") or ""),
                str(payload.get("test_input") or ""),
                str(payload.get("expected_output") or "") or None,
            )
        }

    if job_type == JobType.PROMPT_APPROVAL.value:
        from components.comp_001_prompt_engine.prompt_engine import approve_prompt

        return {"prompt": approve_prompt(db_path, str(payload.get("prompt_id") or ""))}

    if job_type == JobType.SYSTEM_SCAN.value:
        return {"analytics": system_analytics(db_path), "queues": job_queue_counts(db_path)}

    return {"message": f"Job type {job_type} is queued for future implementation."}


def recovery_suggestion_for(job_type: str, error: str) -> str:
    if "not found" in error.lower():
        return "Confirm the referenced record still exists, then resume or retry the job."
    if job_type in {JobType.RESEARCH_SCAN.value, JobType.PROMPT_TEST.value}:
        return "Check required input fields, update the payload, then retry the job."
    return "Review the stack trace and retry once the underlying issue is fixed."


def duration_from_started(job: dict[str, object]) -> int:
    # SQLite stores ISO timestamps; for the local prototype, duration is approximate if loaded from DB.
    if not job.get("started_at"):
        return 0
    return max(0, int((time.perf_counter() - SYSTEM_STARTED_AT) * 1000))


def _loads(raw: object) -> dict[str, object]:
    if not raw:
        return {}
    try:
        value = json.loads(str(raw))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


@contextmanager
def worker_run(
    db_path: str | Path,
    worker_id: str,
    input_ref: str | None = None,
) -> Iterator[dict[str, object]]:
    started_at = utc_now()
    started = time.perf_counter()
    context: dict[str, object] = {"output_ref": None, "decision": None, "error": None}
    set_worker_status(db_path, worker_id, WorkerStatus.RUNNING)
    add_event(db_path, "WorkerStarted", worker_id, "Worker started", entity_id=input_ref)
    try:
        yield context
    except Exception as exc:
        context["error"] = str(exc)
        duration_ms = _duration_ms(started)
        _record_activity(db_path, worker_id, WorkerStatus.FAILED, input_ref, context, duration_ms, started_at)
        set_worker_status(db_path, worker_id, WorkerStatus.FAILED)
        add_event(
            db_path,
            "WorkerFailed",
            worker_id,
            "Worker failed",
            result=_compact(context.get("decision")),
            entity_id=input_ref,
            duration_ms=duration_ms,
            success=False,
            error=str(exc),
        )
        raise
    else:
        duration_ms = _duration_ms(started)
        _record_activity(db_path, worker_id, WorkerStatus.COMPLETED, input_ref, context, duration_ms, started_at)
        set_worker_status(db_path, worker_id, WorkerStatus.COMPLETED)
        add_event(
            db_path,
            "WorkerFinished",
            worker_id,
            "Worker finished",
            result=_compact(context.get("decision")),
            entity_id=_compact(context.get("output_ref")) or input_ref,
            duration_ms=duration_ms,
            success=True,
        )


def _record_activity(
    db_path: str | Path,
    worker_id: str,
    status: WorkerStatus,
    input_ref: str | None,
    context: dict[str, object],
    duration_ms: int,
    started_at: str,
) -> None:
    with connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO worker_activity
            (worker_id, status, input_ref, output_ref, decision, duration_ms, error, started_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                worker_id,
                status.value,
                input_ref,
                _compact(context.get("output_ref")),
                _compact(context.get("decision")),
                duration_ms,
                _compact(context.get("error")),
                started_at,
                utc_now(),
            ),
        )


def _duration_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def _compact(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)[:1000]
    return str(value)[:1000]


def list_notifications(db_path: str | Path, limit: int = 20) -> list[dict[str, object]]:
    with connect(db_path) as connection:
        rows = connection.execute(
            "SELECT * FROM notifications ORDER BY created_at DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [row_to_dict(row) for row in rows]


def list_activity(db_path: str | Path, limit: int = 50) -> list[dict[str, object]]:
    with connect(db_path) as connection:
        rows = connection.execute(
            "SELECT * FROM worker_activity ORDER BY started_at DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [row_to_dict(row) for row in rows]


def list_events(
    db_path: str | Path,
    event_type: str = "",
    worker_id: str = "",
    success: str = "",
    limit: int = 200,
) -> list[dict[str, object]]:
    clauses = []
    values: list[object] = []
    if event_type:
        clauses.append("event_type = ?")
        values.append(event_type)
    if worker_id:
        clauses.append("worker_id = ?")
        values.append(worker_id)
    if success:
        clauses.append("success = ?")
        values.append(1 if success == "Success" else 0)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    values.append(limit)
    with connect(db_path) as connection:
        rows = connection.execute(
            f"SELECT * FROM events {where} ORDER BY created_at DESC, id DESC LIMIT ?",
            values,
        ).fetchall()
    return [row_to_dict(row) for row in rows]


def list_system_logs(
    db_path: str | Path,
    severity: str = "",
    worker_id: str = "",
    job_id: str = "",
    limit: int = 300,
) -> list[dict[str, object]]:
    clauses = []
    values: list[object] = []
    if severity:
        clauses.append("severity = ?")
        values.append(severity)
    if worker_id:
        clauses.append("worker_id = ?")
        values.append(worker_id)
    if job_id:
        clauses.append("job_id = ?")
        values.append(job_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    values.append(limit)
    with connect(db_path) as connection:
        rows = connection.execute(
            f"SELECT * FROM system_logs {where} ORDER BY timestamp DESC, id DESC LIMIT ?",
            values,
        ).fetchall()
    return [row_to_dict(row) for row in rows]


def list_failure_history(db_path: str | Path, job_id: str = "", limit: int = 100) -> list[dict[str, object]]:
    values: list[object] = []
    where = ""
    if job_id:
        where = "WHERE job_id = ?"
        values.append(job_id)
    values.append(limit)
    with connect(db_path) as connection:
        rows = connection.execute(
            f"SELECT * FROM failure_history {where} ORDER BY created_at DESC, id DESC LIMIT ?",
            values,
        ).fetchall()
    return [row_to_dict(row) for row in rows]


def pending_audit_queue(db_path: str | Path) -> list[dict[str, object]]:
    with connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT research_records.*
            FROM research_records
            LEFT JOIN audit_records ON audit_records.research_id = research_records.id
            WHERE audit_records.id IS NULL
            ORDER BY research_records.created_at ASC
            """
        ).fetchall()
    return [row_to_dict(row) for row in rows]


def dashboard_metrics(db_path: str | Path) -> dict[str, object]:
    with connect(db_path) as connection:
        workers = connection.execute("SELECT * FROM workers ORDER BY id").fetchall()
        component_count = count_rows(connection, "components")
        prompt_count = count_rows(connection, "prompts")
        library_count = count_rows(connection, "library_records")
        worker_count = count_rows(connection, "workers")
        research_queue = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM research_records
            LEFT JOIN audit_records ON audit_records.research_id = research_records.id
            WHERE audit_records.id IS NULL
            """
        ).fetchone()["count"]
        audit_queue = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM audit_records
            LEFT JOIN library_records ON library_records.source_audit_id = audit_records.id
            WHERE audit_records.decision = 'approved'
              AND library_records.id IS NULL
            """
        ).fetchone()["count"]
        latest = connection.execute(
            "SELECT * FROM events ORDER BY created_at DESC, id DESC LIMIT 8"
        ).fetchall()
        current_milestone = connection.execute(
            "SELECT * FROM milestones ORDER BY id DESC LIMIT 1"
        ).fetchone()
        database_status = "Online"
        job_counts = job_queue_counts(db_path)
        analytics = system_analytics(db_path)

    failed_workers = [row["id"] for row in workers if row["status"] == WorkerStatus.FAILED.value]
    return {
        "workers_online": len(workers),
        "research_queue": research_queue,
        "audit_queue": audit_queue,
        "library_records": library_count,
        "prompt_count": prompt_count,
        "component_count": component_count,
        "worker_count": worker_count,
        "database_status": database_status,
        "system_health": "Needs Attention" if failed_workers else "Healthy",
        "current_sprint": current_milestone["sprint"] if current_milestone else "Sprint 8",
        "current_milestone": current_milestone["title"] if current_milestone else "Operational Base Workers",
        "uptime": format_uptime(),
        "workers": [row_to_dict(row) for row in workers],
        "latest_activity": [row_to_dict(row) for row in latest],
        "job_counts": job_counts,
        "analytics": analytics,
    }


def format_uptime() -> str:
    elapsed = int(time.perf_counter() - SYSTEM_STARTED_AT)
    minutes, seconds = divmod(elapsed, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def worker_registry(db_path: str | Path) -> list[dict[str, object]]:
    with connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT
                workers.*,
                COUNT(worker_activity.id) AS jobs_completed,
                ROUND(AVG(worker_activity.duration_ms), 0) AS average_runtime_ms,
                MAX(worker_activity.completed_at) AS last_run,
                ROUND(100.0 * SUM(CASE WHEN worker_activity.status = 'Completed' THEN 1 ELSE 0 END)
                      / NULLIF(COUNT(worker_activity.id), 0), 1) AS success_rate
            FROM workers
            LEFT JOIN worker_activity ON worker_activity.worker_id = workers.id
            GROUP BY workers.id
            ORDER BY workers.id
            """
        ).fetchall()
        active_jobs = connection.execute(
            "SELECT assigned_worker, id, job_type, created_at FROM jobs WHERE status IN ('Pending', 'Running', 'Waiting')"
        ).fetchall()
    active_by_worker = {row["assigned_worker"]: row_to_dict(row) for row in active_jobs}
    records = []
    for row in rows:
        record = row_to_dict(row)
        active = active_by_worker.get(record["id"])
        record["current_job"] = active["id"] if active else ""
        record["current_task"] = active["job_type"] if active else ""
        record["current_load"] = sum(1 for active_row in active_jobs if active_row["assigned_worker"] == record["id"])
        record["jobs_today"] = jobs_for_worker(db_path, str(record["id"]), "day")
        record["jobs_this_week"] = jobs_for_worker(db_path, str(record["id"]), "week")
        record["jobs_this_month"] = jobs_for_worker(db_path, str(record["id"]), "month")
        record["health_percent"] = health_percent(record)
        record["reliability_percent"] = record.get("success_rate") or 100
        record["cpu_time"] = "local"
        record["memory_usage"] = "local"
        records.append(record)
    return records


def jobs_for_worker(db_path: str | Path, worker_id: str, period: str) -> int:
    modifier = {"day": "-1 day", "week": "-7 day", "month": "-30 day"}[period]
    with connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM jobs
            WHERE assigned_worker = ?
              AND created_at >= datetime('now', ?)
            """,
            (worker_id, modifier),
        ).fetchone()
    return int(row["count"])


def health_percent(worker: dict[str, object]) -> int:
    if worker.get("status") in {WorkerStatus.FAILED.value, WorkerStatus.OFFLINE.value}:
        return 35
    success = worker.get("success_rate")
    if success is None:
        return 100
    return max(0, min(100, int(float(success))))


def component_registry(db_path: str | Path) -> list[dict[str, object]]:
    with connect(db_path) as connection:
        rows = connection.execute("SELECT * FROM components ORDER BY id").fetchall()
    return [row_to_dict(row) for row in rows]


def list_milestones(db_path: str | Path) -> list[dict[str, object]]:
    with connect(db_path) as connection:
        rows = connection.execute("SELECT * FROM milestones ORDER BY id DESC").fetchall()
    return [row_to_dict(row) for row in rows]


def add_milestone(
    db_path: str | Path,
    milestone_id: str,
    sprint: str,
    title: str,
    description: str,
    completed_by: str,
    files_changed: str,
    result: str,
) -> dict[str, object]:
    with connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO milestones
            (id, sprint, title, description, date, completed_by, files_changed, result)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (milestone_id, sprint, title, description, utc_now(), completed_by, files_changed, result),
        )
    add_event(db_path, "MilestoneLogged", None, "Milestone logged", result, milestone_id)
    return {"id": milestone_id, "sprint": sprint, "title": title, "result": result}


def complete_sprint_milestone(
    db_path: str | Path,
    sprint: str,
    title: str,
    description: str,
    files_changed: str,
    workers_added: str = "",
    components_added: str = "",
    notes: str = "",
    version: str = "v1.0",
) -> dict[str, object]:
    with connect(db_path) as connection:
        milestone_id = next_sequence_id("M", count_rows(connection, "milestones"), width=4, include_year=False)
        now = utc_now()
        connection.execute(
            """
            INSERT INTO milestones
            (id, sprint, version, title, description, date, completion_date, completed_by, files_changed,
             workers_added, components_added, notes, result)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                milestone_id,
                sprint,
                version,
                title,
                description,
                now,
                now,
                "PX-E002",
                files_changed,
                workers_added,
                components_added,
                notes,
                "Completed",
            ),
        )
    add_event(db_path, "Milestone", None, "Sprint milestone completed", title, milestone_id)
    add_journal_entry(
        db_path,
        f"Completed {sprint}: {title}",
        "Lesson Learned",
        f"{description}\n\nFiles changed: {files_changed}\n\nNotes: {notes}",
        milestone_id,
    )
    return {"id": milestone_id, "sprint": sprint, "title": title, "result": "Completed"}


def list_journal_entries(db_path: str | Path) -> list[dict[str, object]]:
    with connect(db_path) as connection:
        rows = connection.execute("SELECT * FROM engineering_journal ORDER BY created_at DESC, id DESC").fetchall()
    return [row_to_dict(row) for row in rows]


def add_journal_entry(
    db_path: str | Path,
    title: str,
    entry_type: str,
    body: str,
    related_entity: str = "",
    created_by: str = "PX-E002",
) -> dict[str, object]:
    if not title or not body:
        raise ValueError("title and body are required")
    now = utc_now()
    with connect(db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO engineering_journal
            (title, entry_type, body, related_entity, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (title, entry_type, body, related_entity, created_by, now),
        )
    add_event(db_path, "JournalEntryCreated", None, "Journal entry created", title, related_entity)
    return {"id": cursor.lastrowid, "title": title, "entry_type": entry_type, "created_at": now}


def pipeline_snapshot(db_path: str | Path) -> list[dict[str, object]]:
    metrics = dashboard_metrics(db_path)
    activity = list_activity(db_path, 20)
    failures = [record for record in activity if record.get("status") == WorkerStatus.FAILED.value]
    return [
        {"stage": "Research", "queue_size": metrics["research_queue"], "active_jobs": active_jobs(activity, "PX-R001"), "failures": failures_for(failures, "PX-R001")},
        {"stage": "Audit", "queue_size": metrics["audit_queue"], "active_jobs": active_jobs(activity, "PX-A001"), "failures": failures_for(failures, "PX-A001")},
        {"stage": "Library", "queue_size": metrics["library_records"], "active_jobs": active_jobs(activity, "PX-L001"), "failures": failures_for(failures, "PX-L001")},
        {"stage": "Components", "queue_size": metrics["component_count"], "active_jobs": 0, "failures": 0},
        {"stage": "Workers", "queue_size": metrics["worker_count"], "active_jobs": 0, "failures": 0},
        {"stage": "Deployment", "queue_size": 0, "active_jobs": 0, "failures": 0},
    ]


def system_analytics(db_path: str | Path) -> dict[str, object]:
    with connect(db_path) as connection:
        jobs_today = connection.execute("SELECT COUNT(*) AS count FROM jobs WHERE created_at >= datetime('now', '-1 day')").fetchone()["count"]
        jobs_completed = connection.execute("SELECT COUNT(*) AS count FROM jobs WHERE status = 'Completed'").fetchone()["count"]
        jobs_failed = connection.execute("SELECT COUNT(*) AS count FROM jobs WHERE status = 'Failed'").fetchone()["count"]
        avg_runtime = connection.execute("SELECT ROUND(AVG(duration_ms), 0) AS value FROM jobs WHERE duration_ms IS NOT NULL").fetchone()["value"]
        avg_audit = connection.execute("SELECT ROUND(AVG(confidence_score), 1) AS value FROM audit_records").fetchone()["value"]
        research_processed = count_rows(connection, "research_records")
        library_growth = count_rows(connection, "library_records")
        prompt_tests = connection.execute("SELECT COUNT(*) AS count FROM prompt_tests").fetchone()["count"]
        prompt_passes = connection.execute("SELECT COUNT(*) AS count FROM prompt_tests WHERE result = 'pass'").fetchone()["count"]
        running_jobs = connection.execute("SELECT COUNT(*) AS count FROM jobs WHERE status = 'Running'").fetchone()["count"]
        total_jobs = count_rows(connection, "jobs")
        storage_used = database_size_label(db_path)
    return {
        "jobs_today": jobs_today,
        "jobs_completed": jobs_completed,
        "jobs_failed": jobs_failed,
        "average_runtime_ms": avg_runtime or 0,
        "average_audit_score": avg_audit or 0,
        "research_processed": research_processed,
        "library_growth": library_growth,
        "prompt_success_percent": round((prompt_passes / prompt_tests) * 100, 1) if prompt_tests else 100,
        "worker_utilisation": round((running_jobs / max(total_jobs, 1)) * 100, 1),
        "system_load": running_jobs,
        "storage_used": storage_used,
    }


def database_size_label(db_path: str | Path) -> str:
    path = Path(db_path)
    if not path.exists():
        return "0 KB"
    size = path.stat().st_size
    if size < 1024 * 1024:
        return f"{round(size / 1024, 1)} KB"
    return f"{round(size / (1024 * 1024), 2)} MB"


def active_jobs(activity: list[dict[str, object]], worker_id: str) -> int:
    return sum(1 for record in activity if record.get("worker_id") == worker_id and record.get("status") == WorkerStatus.RUNNING.value)


def failures_for(failures: list[dict[str, object]], worker_id: str) -> int:
    return sum(1 for record in failures if record.get("worker_id") == worker_id)
