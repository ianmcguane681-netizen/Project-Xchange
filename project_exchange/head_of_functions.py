from __future__ import annotations

import json
from pathlib import Path

from project_exchange.database import connect, count_rows, row_to_dict, utc_now
from project_exchange.eos import (
    JobStatus,
    JobType,
    add_event,
    add_journal_entry,
    create_job,
    execute_job,
    list_jobs,
    retry_job,
    system_analytics,
    worker_registry,
)
from project_exchange.ids import next_sequence_id
from project_exchange.os_services import route_worker_message
from workers.px_l001_library.library_manager import search_library_records


HEAD_WORKER_ID = "PX-H001"


def submit_command(db_path: str | Path, command: str) -> dict[str, object]:
    text = command.strip()
    if not text:
        raise ValueError("Command is required")

    plan = create_execution_plan(db_path, text)
    intent = str(plan["intent"])
    if intent == "research":
        payload = parse_research_topic(text.removeprefix("Research").strip(" ."))
        job = create_job(
            db_path,
            JobType.INTERNET_RESEARCH.value,
            "PX-R001",
            payload,
            priority=1,
            parent_job_id=str(plan["id"]),
            created_by=HEAD_WORKER_ID,
        )
        attach_job_to_plan(db_path, str(plan["id"]), job)
        route_worker_message(
            db_path,
            HEAD_WORKER_ID,
            "PX-R001",
            f"Execute research plan {plan['id']}.",
            str(job["id"]),
            priority=1,
            payload=payload,
        )
        result = execute_job(db_path, str(job["id"]))
        complete_execution_plan(db_path, str(plan["id"]), [result])
        refresh_worker_memory(db_path)
        return {"command": text, "head_of_functions": plan, "job": result}

    if intent == "audit":
        pending = list_jobs(db_path, JobStatus.PENDING.value, "PX-A001")
        if not pending:
            complete_execution_plan(db_path, str(plan["id"]), [])
            return {"command": text, "head_of_functions": plan, "message": "No pending audit jobs found."}
        result = execute_job(db_path, str(pending[0]["id"]))
        attach_job_to_plan(db_path, str(plan["id"]), result)
        complete_execution_plan(db_path, str(plan["id"]), [result])
        refresh_worker_memory(db_path)
        return {"command": text, "head_of_functions": plan, "job": result}

    if intent == "failed_jobs":
        complete_execution_plan(db_path, str(plan["id"]), [])
        return {"command": text, "head_of_functions": plan, "failed_jobs": list_jobs(db_path, JobStatus.FAILED.value)}

    if intent == "library_summary":
        records = search_library_records(db_path)
        complete_execution_plan(db_path, str(plan["id"]), [])
        return {
            "command": text,
            "head_of_functions": plan,
            "summary": f"Library contains {len(records)} records.",
            "records": records[:10],
        }

    if intent == "library_search":
        query = text.split("library", 1)[-1].strip()
        complete_execution_plan(db_path, str(plan["id"]), [])
        return {"command": text, "head_of_functions": plan, "results": search_library_records(db_path, query)}

    if intent == "duplicate_scan":
        records = search_library_records(db_path)
        duplicates = detect_library_duplicates(records)
        complete_execution_plan(db_path, str(plan["id"]), [])
        return {"command": text, "head_of_functions": plan, "duplicates": duplicates}

    if intent == "brief":
        brief_type = "weekly" if "weekly" in text.lower() else "daily"
        brief = generate_operating_brief(db_path, brief_type)
        complete_execution_plan(db_path, str(plan["id"]), [])
        refresh_worker_memory(db_path)
        return {"command": text, "head_of_functions": plan, "brief": brief}

    job = create_job(
        db_path,
        JobType.SYSTEM_SCAN.value,
        HEAD_WORKER_ID,
        {"command": text},
        priority=5,
        parent_job_id=str(plan["id"]),
        created_by=HEAD_WORKER_ID,
    )
    attach_job_to_plan(db_path, str(plan["id"]), job)
    result = execute_job(db_path, str(job["id"]))
    recommendations = generate_system_recommendations(db_path)
    complete_execution_plan(db_path, str(plan["id"]), [result])
    refresh_worker_memory(db_path)
    return {"command": text, "head_of_functions": plan, "job": result, "recommendations": recommendations}


def create_execution_plan(db_path: str | Path, command: str, priority: int = 3) -> dict[str, object]:
    intent = classify_intent(command)
    with connect(db_path) as connection:
        plan_id = next_sequence_id("PLAN", count_rows(connection, "execution_plans"))
        now = utc_now()
        connection.execute(
            """
            INSERT INTO execution_plans (id, command, intent, status, priority, jobs, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (plan_id, command, intent, JobStatus.RUNNING.value, priority, "[]", HEAD_WORKER_ID, now),
        )
    add_event(db_path, "ExecutionPlanCreated", HEAD_WORKER_ID, "PX-H001 created execution plan", intent, plan_id)
    return get_execution_plan(db_path, plan_id)


def get_execution_plan(db_path: str | Path, plan_id: str) -> dict[str, object]:
    with connect(db_path) as connection:
        row = connection.execute("SELECT * FROM execution_plans WHERE id = ?", (plan_id,)).fetchone()
    if row is None:
        raise ValueError(f"Execution plan not found: {plan_id}")
    record = row_to_dict(row)
    record["jobs_list"] = safe_list(record.get("jobs"))
    return record


def attach_job_to_plan(db_path: str | Path, plan_id: str, job: dict[str, object]) -> None:
    plan = get_execution_plan(db_path, plan_id)
    jobs = safe_list(plan.get("jobs"))
    jobs.append({"id": job.get("id"), "type": job.get("job_type"), "worker": job.get("assigned_worker"), "status": job.get("status")})
    with connect(db_path) as connection:
        connection.execute("UPDATE execution_plans SET jobs = ? WHERE id = ?", (json.dumps(jobs, ensure_ascii=False), plan_id))


def complete_execution_plan(db_path: str | Path, plan_id: str, jobs: list[dict[str, object]]) -> None:
    status = JobStatus.FAILED.value if any(job.get("status") == JobStatus.FAILED.value for job in jobs) else JobStatus.COMPLETED.value
    with connect(db_path) as connection:
        connection.execute(
            "UPDATE execution_plans SET status = ?, completed_at = ? WHERE id = ?",
            (status, utc_now(), plan_id),
        )
    add_event(db_path, "ExecutionPlanCompleted", HEAD_WORKER_ID, "PX-H001 completed execution plan", status, plan_id)


def classify_intent(command: str) -> str:
    lower = command.lower()
    if lower.startswith("generate executive report") or "daily brief" in lower or "weekly brief" in lower:
        return "brief"
    if lower.startswith("research"):
        return "research"
    if lower.startswith("audit"):
        return "audit"
    if "failed audit" in lower or "failed job" in lower:
        return "failed_jobs"
    if lower.startswith("summarise library") or lower.startswith("summarize library"):
        return "library_summary"
    if lower.startswith("search library"):
        return "library_search"
    if "duplicate" in lower:
        return "duplicate_scan"
    return "system_scan"


def create_objective(
    db_path: str | Path,
    title: str,
    description: str = "",
    priority: int = 3,
    cadence: str = "manual",
    success_metric: str = "",
) -> dict[str, object]:
    if not title:
        raise ValueError("Objective title is required")
    with connect(db_path) as connection:
        objective_id = next_sequence_id("OBJ", count_rows(connection, "objectives"))
        now = utc_now()
        connection.execute(
            """
            INSERT INTO objectives
            (id, title, description, status, priority, owner, cadence, success_metric, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (objective_id, title, description, "active", priority, HEAD_WORKER_ID, cadence, success_metric, now, now),
        )
    add_event(db_path, "ObjectiveCreated", HEAD_WORKER_ID, "PX-H001 created objective", title, objective_id)
    return get_objective(db_path, objective_id)


def get_objective(db_path: str | Path, objective_id: str) -> dict[str, object]:
    with connect(db_path) as connection:
        row = connection.execute("SELECT * FROM objectives WHERE id = ?", (objective_id,)).fetchone()
    if row is None:
        raise ValueError(f"Objective not found: {objective_id}")
    return row_to_dict(row)


def list_objectives(db_path: str | Path, status: str = "") -> list[dict[str, object]]:
    values = []
    where = ""
    if status:
        where = "WHERE status = ?"
        values.append(status)
    with connect(db_path) as connection:
        rows = connection.execute(
            f"SELECT * FROM objectives {where} ORDER BY priority ASC, updated_at DESC",
            values,
        ).fetchall()
    return [row_to_dict(row) for row in rows]


def create_operating_schedule(
    db_path: str | Path,
    name: str,
    cadence: str,
    worker_id: str,
    job_type: str,
    payload: dict[str, object] | None = None,
    objective_id: str = "",
    priority: int = 3,
) -> dict[str, object]:
    if not name or not cadence or not worker_id or not job_type:
        raise ValueError("name, cadence, worker_id, and job_type are required")
    with connect(db_path) as connection:
        schedule_id = next_sequence_id("SCH", count_rows(connection, "operating_schedules"))
        connection.execute(
            """
            INSERT INTO operating_schedules
            (id, objective_id, name, cadence, worker_id, job_type, payload, priority, enabled, next_run_hint, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                schedule_id,
                objective_id,
                name,
                cadence,
                worker_id,
                job_type,
                json.dumps(payload or {}, ensure_ascii=False),
                priority,
                1,
                cadence,
                utc_now(),
            ),
        )
    add_event(db_path, "ScheduleCreated", HEAD_WORKER_ID, "PX-H001 created operating schedule", name, schedule_id)
    return get_operating_schedule(db_path, schedule_id)


def get_operating_schedule(db_path: str | Path, schedule_id: str) -> dict[str, object]:
    with connect(db_path) as connection:
        row = connection.execute("SELECT * FROM operating_schedules WHERE id = ?", (schedule_id,)).fetchone()
    if row is None:
        raise ValueError(f"Schedule not found: {schedule_id}")
    return row_to_dict(row)


def list_operating_schedules(db_path: str | Path) -> list[dict[str, object]]:
    with connect(db_path) as connection:
        rows = connection.execute("SELECT * FROM operating_schedules ORDER BY enabled DESC, priority ASC, created_at DESC").fetchall()
    return [row_to_dict(row) for row in rows]


def run_operating_schedule(db_path: str | Path, schedule_id: str) -> dict[str, object]:
    schedule = get_operating_schedule(db_path, schedule_id)
    payload = _safe_dict(schedule.get("payload"))
    payload["schedule_id"] = schedule_id
    payload["schedule"] = schedule.get("cadence") or ""
    job = create_job(
        db_path,
        str(schedule["job_type"]),
        str(schedule["worker_id"]),
        payload,
        int(schedule.get("priority") or 3),
        created_by=HEAD_WORKER_ID,
    )
    result = execute_job(db_path, str(job["id"]))
    with connect(db_path) as connection:
        connection.execute("UPDATE operating_schedules SET last_run_at = ? WHERE id = ?", (utc_now(), schedule_id))
    refresh_worker_memory(db_path)
    create_performance_snapshot(db_path, "schedule_run", str(schedule["worker_id"]))
    return {"schedule": schedule, "job": result}


def run_due_schedules(db_path: str | Path, cadence: str = "daily") -> dict[str, object]:
    results = []
    for schedule in list_operating_schedules(db_path):
        if int(schedule.get("enabled") or 0) and str(schedule.get("cadence") or "").lower() == cadence.lower():
            results.append(run_operating_schedule(db_path, str(schedule["id"])))
    add_event(db_path, "SchedulesRun", HEAD_WORKER_ID, "PX-H001 ran operating schedules", f"{len(results)} schedules")
    return {"cadence": cadence, "count": len(results), "results": results}


def create_performance_snapshot(db_path: str | Path, snapshot_type: str = "manual", worker_id: str = "") -> dict[str, object]:
    metrics = {
        "analytics": system_analytics(db_path),
        "worker_memory": refresh_worker_memory(db_path),
        "worker_load": worker_load_monitor(db_path),
        "priority_manager": priority_manager(db_path),
    }
    with connect(db_path) as connection:
        snapshot_id = next_sequence_id("PERF", count_rows(connection, "performance_snapshots"))
        connection.execute(
            """
            INSERT INTO performance_snapshots (id, worker_id, snapshot_type, metrics, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (snapshot_id, worker_id, snapshot_type, json.dumps(metrics, ensure_ascii=False), utc_now()),
        )
    return {"id": snapshot_id, "snapshot_type": snapshot_type, "worker_id": worker_id, "metrics": metrics}


def list_performance_snapshots(db_path: str | Path, limit: int = 50) -> list[dict[str, object]]:
    with connect(db_path) as connection:
        rows = connection.execute(
            "SELECT * FROM performance_snapshots ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [row_to_dict(row) for row in rows]


def worker_load_monitor(db_path: str | Path) -> list[dict[str, object]]:
    records = []
    for worker in worker_registry(db_path):
        current_load = int(worker.get("current_load") or 0)
        records.append(
            {
                "worker_id": worker["id"],
                "status": worker.get("status"),
                "current_load": current_load,
                "health_percent": worker.get("health_percent"),
                "recommendation": "Balance work away from this worker" if current_load >= 3 else "Capacity available",
            }
        )
    return records


def priority_manager(db_path: str | Path) -> dict[str, object]:
    objectives = list_objectives(db_path, "active")
    pending = list_jobs(db_path, JobStatus.PENDING.value)
    return {
        "top_objectives": objectives[:5],
        "urgent_jobs": [job for job in pending if int(job.get("priority") or 9) <= 2][:10],
        "recommendation": "Run high-priority schedules first, then clear pending audit/library jobs.",
    }


def generate_operating_brief(db_path: str | Path, brief_type: str = "daily") -> dict[str, object]:
    analytics = system_analytics(db_path)
    memory = refresh_worker_memory(db_path)
    recommendations = generate_system_recommendations(db_path)
    objectives = list_objectives(db_path, "active")
    schedules = list_operating_schedules(db_path)
    title = f"{brief_type.title()} Operating Brief"
    body = (
        f"PX-EOS processed {analytics['research_processed']} research records, "
        f"holds {analytics['library_growth']} library records, and has {analytics['jobs_failed']} failed jobs. "
        f"Active objectives: {len(objectives)}. Active schedules: {sum(1 for schedule in schedules if int(schedule.get('enabled') or 0))}. "
        "Recommended focus: clear high-priority jobs, strengthen weak evidence, and keep research schedules running."
    )
    with connect(db_path) as connection:
        brief_id = next_sequence_id("BRF", count_rows(connection, "operating_briefs"))
        connection.execute(
            """
            INSERT INTO operating_briefs (id, brief_type, title, body, metrics, recommendations, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                brief_id,
                brief_type,
                title,
                body,
                json.dumps({"analytics": analytics, "worker_memory": memory}, ensure_ascii=False),
                json.dumps(recommendations, ensure_ascii=False),
                HEAD_WORKER_ID,
                utc_now(),
            ),
        )
    add_event(db_path, "OperatingBriefCreated", HEAD_WORKER_ID, "PX-H001 created operating brief", brief_type, brief_id)
    return {"id": brief_id, "brief_type": brief_type, "title": title, "body": body, "recommendations": recommendations}


def list_operating_briefs(db_path: str | Path, limit: int = 50) -> list[dict[str, object]]:
    with connect(db_path) as connection:
        rows = connection.execute(
            "SELECT * FROM operating_briefs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [row_to_dict(row) for row in rows]


def operating_summary(db_path: str | Path) -> dict[str, object]:
    return {
        "objectives": list_objectives(db_path),
        "schedules": list_operating_schedules(db_path),
        "worker_load": worker_load_monitor(db_path),
        "priorities": priority_manager(db_path),
        "latest_briefs": list_operating_briefs(db_path, 5),
        "performance": list_performance_snapshots(db_path, 5),
    }


def _safe_dict(raw: object) -> dict[str, object]:
    if not raw:
        return {}
    try:
        parsed = json.loads(str(raw))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def parse_research_topic(topic: str) -> dict[str, object]:
    topic = topic or "market opportunity"
    return {
        "company": "",
        "industry": topic,
        "market": topic,
        "keyword": topic,
        "website": "",
        "source_text": topic,
        "source_type": "px_h001_command",
        "orchestrated_by": HEAD_WORKER_ID,
    }


def detect_library_duplicates(records: list[dict[str, object]]) -> list[dict[str, object]]:
    summaries = {}
    duplicates = []
    for record in records:
        key = str(record.get("summary") or "").lower()[:80]
        if key and key in summaries:
            duplicates.append({"first": summaries[key], "second": record})
        summaries[key] = record
    return duplicates


def refresh_worker_memory(db_path: str | Path) -> list[dict[str, object]]:
    registry = worker_registry(db_path)
    now = utc_now()
    with connect(db_path) as connection:
        for worker in registry:
            worker_id = str(worker["id"])
            jobs_completed = int(worker.get("jobs_completed") or 0)
            current_load = int(worker.get("current_load") or 0)
            jobs_failed = connection.execute(
                "SELECT COUNT(*) AS count FROM jobs WHERE assigned_worker = ? AND status = ?",
                (worker_id, JobStatus.FAILED.value),
            ).fetchone()["count"]
            confidence = confidence_for_worker(connection, worker_id)
            approval_rate = approval_rate_for_worker(connection, worker_id)
            companies = distinct_values(connection, "research_records", "company") if worker_id == "PX-R001" else []
            industries = distinct_values(connection, "research_records", "market") if worker_id == "PX-R001" else []
            success_rate = float(worker.get("success_rate") or 100)
            reliability = max(0.0, min(100.0, (success_rate * 0.75) + (confidence * 0.25 if confidence else 25)))
            health = "Needs Attention" if reliability < 70 or jobs_failed else "Healthy"
            experience = build_experience_summary(worker_id, jobs_completed, jobs_failed, confidence, approval_rate)
            connection.execute(
                """
                INSERT INTO worker_memory
                (worker_id, jobs_completed, jobs_failed, average_runtime_ms, average_confidence, most_used_components,
                 most_used_prompts, industries, companies, success_rate, approval_rate, reliability_score, health,
                 experience_summary, current_load, last_activity, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(worker_id) DO UPDATE SET
                    jobs_completed = excluded.jobs_completed,
                    jobs_failed = excluded.jobs_failed,
                    average_runtime_ms = excluded.average_runtime_ms,
                    average_confidence = excluded.average_confidence,
                    most_used_components = excluded.most_used_components,
                    most_used_prompts = excluded.most_used_prompts,
                    industries = excluded.industries,
                    companies = excluded.companies,
                    success_rate = excluded.success_rate,
                    approval_rate = excluded.approval_rate,
                    reliability_score = excluded.reliability_score,
                    health = excluded.health,
                    experience_summary = excluded.experience_summary,
                    current_load = excluded.current_load,
                    last_activity = excluded.last_activity,
                    updated_at = excluded.updated_at
                """,
                (
                    worker_id,
                    jobs_completed,
                    int(jobs_failed),
                    int(worker.get("average_runtime_ms") or 0),
                    confidence,
                    worker.get("components_used") or "",
                    worker.get("prompt_version") or "",
                    ", ".join(industries[:10]),
                    ", ".join(companies[:10]),
                    success_rate,
                    approval_rate,
                    reliability,
                    health,
                    experience,
                    current_load,
                    worker.get("last_run") or "",
                    now,
                ),
            )
    add_event(db_path, "WorkerMemoryUpdated", HEAD_WORKER_ID, "PX-H001 refreshed worker memory", "Updated")
    return list_worker_memory(db_path)


def confidence_for_worker(connection, worker_id: str) -> float:
    if worker_id != "PX-A001":
        return 0.0
    value = connection.execute("SELECT ROUND(AVG(confidence_score), 1) AS value FROM audit_records").fetchone()["value"]
    return float(value or 0)


def approval_rate_for_worker(connection, worker_id: str) -> float:
    if worker_id != "PX-A001":
        return 0.0
    total = connection.execute("SELECT COUNT(*) AS count FROM audit_records").fetchone()["count"]
    approved = connection.execute("SELECT COUNT(*) AS count FROM audit_records WHERE decision = 'approved'").fetchone()["count"]
    return round((approved / total) * 100, 1) if total else 0.0


def distinct_values(connection, table: str, column: str) -> list[str]:
    rows = connection.execute(f"SELECT DISTINCT {column} AS value FROM {table} WHERE {column} IS NOT NULL AND {column} != ''").fetchall()
    return [str(row["value"]) for row in rows]


def build_experience_summary(worker_id: str, completed: int, failed: int, confidence: float, approval_rate: float) -> str:
    if worker_id == "PX-H001":
        return "Routes commands into jobs, monitors queues, refreshes memory, and recommends operating improvements."
    if worker_id == "PX-A001":
        return f"Audited {completed} jobs with {confidence}% average confidence and {approval_rate}% approval rate."
    if worker_id == "PX-R001":
        return f"Completed {completed} research jobs and created structured research packages."
    if worker_id == "PX-L001":
        return f"Completed {completed} library jobs and maintains canonical knowledge records."
    return f"Completed {completed} jobs with {failed} failures."


def list_worker_memory(db_path: str | Path) -> list[dict[str, object]]:
    with connect(db_path) as connection:
        rows = connection.execute("SELECT * FROM worker_memory ORDER BY worker_id").fetchall()
    return [row_to_dict(row) for row in rows]


def list_execution_plans(db_path: str | Path, limit: int = 100) -> list[dict[str, object]]:
    with connect(db_path) as connection:
        rows = connection.execute(
            "SELECT * FROM execution_plans ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [row_to_dict(row) for row in rows]


def monitor_and_recover(db_path: str | Path) -> dict[str, object]:
    recovered = []
    for job in list_jobs(db_path, JobStatus.FAILED.value):
        if int(job.get("retries") or 0) < int(job.get("max_retries") or 0):
            recovered.append(retry_job(db_path, str(job["id"])))
    refresh_worker_memory(db_path)
    add_event(db_path, "RecoveryScanCompleted", HEAD_WORKER_ID, "PX-H001 scanned failed jobs", f"{len(recovered)} retried")
    return {"retried": recovered, "count": len(recovered)}


def generate_system_recommendations(db_path: str | Path) -> list[dict[str, object]]:
    analytics = system_analytics(db_path)
    memory = refresh_worker_memory(db_path)
    recommendations: list[tuple[str, str, str, str]] = []

    if int(analytics["jobs_failed"]) > 0:
        recommendations.append(("Reliability", "warning", "Review failed jobs and recovery suggestions.", f"{analytics['jobs_failed']} failed jobs recorded."))
    if int(analytics["average_runtime_ms"]) > 5000:
        recommendations.append(("Performance", "info", "Inspect slow worker paths and provider waits.", f"Average runtime is {analytics['average_runtime_ms']} ms."))
    for record in memory:
        if float(record.get("reliability_score") or 100) < 75:
            recommendations.append(("Worker Health", "warning", f"Investigate {record['worker_id']} reliability.", str(record.get("experience_summary") or "")))
    if float(analytics["prompt_success_percent"]) < 90:
        recommendations.append(("Prompt Quality", "warning", "Review weak prompt tests and retire failing variants.", f"Prompt success is {analytics['prompt_success_percent']}%."))
    if not recommendations:
        recommendations.append(("System", "info", "No urgent bottlenecks detected. Keep gathering operational history.", "PX-H001 found healthy baseline metrics."))

    saved = []
    with connect(db_path) as connection:
        base_count = count_rows(connection, "system_recommendations")
        for index, (category, severity, recommendation, evidence) in enumerate(recommendations, start=1):
            rec_id = next_sequence_id("REC", base_count + index - 1)
            connection.execute(
                """
                INSERT INTO system_recommendations (id, category, severity, recommendation, evidence, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (rec_id, category, severity, recommendation, evidence, "open", utc_now()),
            )
            saved.append({"id": rec_id, "category": category, "severity": severity, "recommendation": recommendation, "evidence": evidence})
    add_journal_entry(
        db_path,
        "PX-H001 system recommendations",
        "Future Improvement",
        "\n".join(f"- {item['recommendation']} ({item['evidence']})" for item in saved),
        HEAD_WORKER_ID,
        created_by=HEAD_WORKER_ID,
    )
    return saved


def list_system_recommendations(db_path: str | Path, limit: int = 100) -> list[dict[str, object]]:
    with connect(db_path) as connection:
        rows = connection.execute(
            "SELECT * FROM system_recommendations ORDER BY created_at DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [row_to_dict(row) for row in rows]


def safe_list(raw: object) -> list[dict[str, object]]:
    if not raw:
        return []
    try:
        parsed = json.loads(str(raw))
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []
