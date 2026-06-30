from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import streamlit as st

from components.comp_001_prompt_engine.prompt_engine import (
    PromptStatus,
    approve_prompt,
    benchmark_prompt,
    create_prompt,
    create_prompt_version,
    list_prompt_benchmarks,
    list_prompt_versions,
    rollback_prompt,
    run_prompt_test,
    search_prompts,
    retire_prompt,
)
from project_exchange.command_console import run_command
from project_exchange.database import DEFAULT_DB_PATH, fetch_all, init_db
from project_exchange.eos import (
    add_journal_entry,
    add_milestone,
    cancel_job,
    component_registry,
    complete_sprint_milestone,
    create_job,
    dashboard_metrics,
    execute_job,
    JobStatus,
    JobType,
    list_activity,
    list_events,
    list_failure_history,
    list_journal_entries,
    list_jobs,
    list_milestones,
    list_notifications,
    list_system_logs,
    pending_audit_queue,
    pipeline_snapshot,
    restart_worker,
    retry_job,
    resume_job,
    worker_registry,
)
from project_exchange.json_io import read_json, write_json
from project_exchange.golden_study import (
    DEFAULT_STUDY_ID,
    approve_audited_opportunities,
    archive_record,
    audit_finding,
    create_signal,
    demo_warning_active,
    create_study,
    finding_evidence,
    generate_executive_brief,
    generate_findings,
    get_or_create_default_study,
    list_finding_audits,
    list_findings,
    list_opportunities,
    list_signals,
    list_studies,
    list_study_briefs,
    run_audit_batch,
    run_research_batch,
    study_progress,
    traceability_chain,
    validate_golden_study_integrity,
)
from project_exchange.head_of_functions import (
    create_objective,
    create_operating_schedule,
    create_performance_snapshot,
    generate_system_recommendations,
    generate_operating_brief,
    list_execution_plans,
    list_objectives,
    list_operating_briefs,
    list_operating_schedules,
    list_performance_snapshots,
    list_system_recommendations,
    list_worker_memory,
    monitor_and_recover,
    operating_summary,
    refresh_worker_memory,
    run_due_schedules,
    run_operating_schedule,
    worker_load_monitor,
)
from project_exchange.os_services import (
    list_knowledge_edges,
    list_settings,
    list_worker_messages,
    route_worker_message,
    send_worker_message,
    set_setting,
)
from project_exchange.provider_status import provider_connection_rows
from workers.px_a001_audit.audit_engine import AuditDecision, list_audit_records, run_audit, update_audit_decision
from workers.px_l001_library.library_manager import approved_audit_queue, list_library_records, search_library_records, store_approved_record
from workers.px_r001_research.research_scanner import list_research_records, run_market_scan, text_from_csv


DB_PATH = DEFAULT_DB_PATH
EXPORT_DIR = Path("data/exports")

st.set_page_config(page_title="PX-EOS", layout="wide")
init_db(DB_PATH)


def get_research_record(research_id: str) -> dict[str, object] | None:
    for record in list_research_records(DB_PATH):
        if record["id"] == research_id:
            return record
    return None


def get_audit_report(audit_id: str) -> dict[str, object] | None:
    for record in list_audit_records(DB_PATH):
        if record["id"] == audit_id:
            return {
                "audit_id": record["id"],
                "research_id": record["research_id"],
                "decision": record["decision"],
                "confidence_score": record["confidence_score"],
                "source_verified": bool(record["source_verified"]),
                "duplicate_risk": record.get("duplicate_risk") or ("high" if record["duplicate_flag"] else "low"),
                "evidence_checklist": safe_json(record.get("evidence_checklist")),
                "reasoning_summary": record.get("reasoning_summary") or record["audit_notes"],
                "send_to_library": record["decision"] == "approved",
                "created_at": record["created_at"],
            }
    return None


def safe_json(raw: object) -> object:
    if not raw:
        return {}
    try:
        return json.loads(str(raw))
    except json.JSONDecodeError:
        return raw


def uploaded_text(uploaded_file) -> tuple[str, str]:
    if uploaded_file is None:
        return "", "pasted_text"
    name = uploaded_file.name.lower()
    data = uploaded_file.read()
    if name.endswith(".txt"):
        return data.decode("utf-8", errors="ignore"), "txt_upload"
    if name.endswith(".csv"):
        decoded = data.decode("utf-8", errors="ignore")
        rows = csv.reader(io.StringIO(decoded))
        flattened = [" ".join(cell.strip() for cell in row if cell.strip()) for row in rows]
        return text_from_csv("\n".join(flattened)), "csv_upload"
    if name.endswith(".pdf"):
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            return text.strip(), "pdf_upload"
        except Exception:
            return "PDF uploaded but text extraction failed. Paste the article text for this source.", "pdf_upload"
    return data.decode("utf-8", errors="ignore"), "file_upload"


def store_selected_audit(audit_id: str) -> dict[str, object]:
    audit = get_audit_report(audit_id)
    research = get_research_record(str(audit["research_id"])) if audit else None
    if not audit or not research:
        raise ValueError("Could not find matching audit and research records.")
    return store_approved_record(DB_PATH, audit, research)


st.title("PROJECT EXCHANGE OS")
st.caption("Build Within. Use Within. Verify Within. Monetise Outside.")

tabs = st.tabs(
    [
        "Home",
        "Timeline",
        "PX Command Console",
        "Research Integration",
        "Pipeline",
        "Jobs",
        "Logs",
        "Errors",
        "Worker Registry",
        "Component Registry",
        "Milestones",
        "Engineering Journal",
        "Research",
        "Audit",
        "Library",
        "Prompts",
        "Knowledge Graph",
        "Worker Chat",
        "Settings",
        "Provider Settings",
        "History",
        "Data",
        "PX-H001",
        "Golden Study 001",
    ]
)

with tabs[0]:
    st.header("Home Dashboard")
    metrics = dashboard_metrics(DB_PATH)
    top = st.columns(4)
    top[0].metric("System Health", metrics["system_health"])
    top[1].metric("Current Sprint", metrics["current_sprint"])
    top[2].metric("Current Milestone", metrics["current_milestone"])
    top[3].metric("Uptime", metrics["uptime"])

    cols = st.columns(8)
    cols[0].metric("Workers Online", metrics["workers_online"])
    cols[1].metric("Research Queue", metrics["research_queue"])
    cols[2].metric("Audit Queue", metrics["audit_queue"])
    cols[3].metric("Library Records", metrics["library_records"])
    cols[4].metric("Prompt Count", metrics["prompt_count"])
    cols[5].metric("Component Count", metrics["component_count"])
    cols[6].metric("Worker Count", metrics["worker_count"])
    cols[7].metric("Database Status", metrics["database_status"])

    analytics = metrics["analytics"]
    st.subheader("System Analytics")
    analytics_cols = st.columns(6)
    analytics_cols[0].metric("Jobs Today", analytics["jobs_today"])
    analytics_cols[1].metric("Jobs Completed", analytics["jobs_completed"])
    analytics_cols[2].metric("Jobs Failed", analytics["jobs_failed"])
    analytics_cols[3].metric("Average Runtime", f"{analytics['average_runtime_ms']} ms")
    analytics_cols[4].metric("Average Audit Score", analytics["average_audit_score"])
    analytics_cols[5].metric("Storage Used", analytics["storage_used"])
    analytics_cols_2 = st.columns(5)
    analytics_cols_2[0].metric("Research Processed", analytics["research_processed"])
    analytics_cols_2[1].metric("Library Growth", analytics["library_growth"])
    analytics_cols_2[2].metric("Prompt Success %", analytics["prompt_success_percent"])
    analytics_cols_2[3].metric("Worker Utilisation", f"{analytics['worker_utilisation']}%")
    analytics_cols_2[4].metric("System Load", analytics["system_load"])

    st.subheader("Job Queues")
    queue_cols = st.columns(6)
    for column, status in zip(queue_cols, ["Pending", "Running", "Waiting", "Completed", "Failed", "Cancelled"]):
        column.metric(status, metrics["job_counts"].get(status, 0))

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Worker Status")
        st.dataframe(worker_registry(DB_PATH), use_container_width=True)
    with col_b:
        st.subheader("Recent Notifications")
        st.dataframe(list_notifications(DB_PATH), use_container_width=True)
    st.subheader("Latest Activity")
    st.dataframe(metrics["latest_activity"], use_container_width=True)
    st.subheader("PX-H001 Recommendations")
    recommendations = list_system_recommendations(DB_PATH, 5)
    if recommendations:
        st.dataframe(recommendations, use_container_width=True)
    else:
        st.info("PX-H001 has not generated recommendations yet.")
    st.subheader("Live Activity Feed")
    for event in list_events(DB_PATH, limit=12):
        st.write(f"{str(event['created_at'])[11:16]}  {event['event_type']}  {event.get('result') or ''}")

with tabs[1]:
    st.header("Event Timeline")
    event_type = st.text_input("Event type filter", key="timeline_event_type")
    worker_filter = st.selectbox("Worker filter", ["", "PX-H001", "PX-R001", "PX-A001", "PX-L001"], key="timeline_worker_filter")
    success_filter = st.selectbox("Success filter", ["", "Success", "Failed"], key="timeline_success_filter")
    st.dataframe(list_events(DB_PATH, event_type, worker_filter, success_filter), use_container_width=True)

with tabs[2]:
    st.header("PX-H001 Command Console")
    command = st.text_input("Command", value="Research Property Management software.", key="console_command")
    if st.button("Run Command", type="primary"):
        try:
            st.json(run_command(DB_PATH, command))
        except Exception as exc:
            st.error(str(exc))
    st.caption("PX-H001 turns commands into execution plans, jobs, worker messages, memory updates, and recommendations.")
    st.subheader("Recent Execution Plans")
    st.dataframe(list_execution_plans(DB_PATH, 20), use_container_width=True)

with tabs[3]:
    st.header("Internet Research Engine")
    col_a, col_b = st.columns(2)
    with col_a:
        ri_company = st.text_input("Company", key="research_integration_company")
        ri_industry = st.text_input("Industry", key="research_integration_industry")
        ri_website = st.text_input("Website", key="research_integration_website")
    with col_b:
        ri_keyword = st.text_input("Keyword", key="research_integration_keyword")
        ri_market = st.text_input("Market", key="research_integration_market")
        ri_rss = st.text_input("RSS feed URL", key="research_integration_rss")
    if st.button("Run Multi-Provider Research", type="primary"):
        payload = {
            "company": ri_company,
            "industry": ri_industry,
            "website": ri_website,
            "keyword": ri_keyword,
            "market": ri_market,
            "rss_url": ri_rss,
        }
        job = create_job(DB_PATH, JobType.INTERNET_RESEARCH.value, "PX-R001", payload, priority=1)
        st.json(execute_job(DB_PATH, str(job["id"])))
    st.subheader("Provider Runs")
    st.dataframe(fetch_all(DB_PATH, "provider_runs"), use_container_width=True)
    st.subheader("Research Packages")
    st.dataframe(fetch_all(DB_PATH, "research_packages"), use_container_width=True)

with tabs[4]:
    st.header("Pipeline View")
    st.caption("Research -> Audit -> Library -> Components -> Workers -> Deployment")
    st.dataframe(pipeline_snapshot(DB_PATH), use_container_width=True)

    queue_col, approved_col, library_col = st.columns(3)
    with queue_col:
        st.subheader("Pending Audit Queue")
        pending = pending_audit_queue(DB_PATH)
        st.dataframe(pending, use_container_width=True)
        pending_ids = [record["id"] for record in pending]
        selected_pending = st.selectbox("Audit next", pending_ids) if pending_ids else None
        if st.button("Run PX-A001", disabled=not selected_pending, type="primary"):
            job = create_job(DB_PATH, JobType.AUDIT_SCAN.value, "PX-A001", {"research_id": str(selected_pending)}, priority=2)
            result = execute_job(DB_PATH, str(job["id"]))
            st.success(f"Job finished: {result['id']}")
            st.json(result)

    with approved_col:
        st.subheader("Approved Queue")
        approved = approved_audit_queue(DB_PATH)
        st.dataframe(approved, use_container_width=True)
        approved_ids = [record["id"] for record in approved]
        selected_approved = st.selectbox("Store next", approved_ids) if approved_ids else None
        if st.button("Run PX-L001", disabled=not selected_approved, type="primary"):
            try:
                audit = get_audit_report(str(selected_approved))
                job = create_job(
                    DB_PATH,
                    JobType.LIBRARY_STORE.value,
                    "PX-L001",
                    {"audit_id": str(selected_approved), "research_id": str(audit["research_id"]) if audit else ""},
                    priority=2,
                )
                result = execute_job(DB_PATH, str(job["id"]))
                st.success(f"Job finished: {result['id']}")
                st.json(result)
            except ValueError as exc:
                st.error(str(exc))

    with library_col:
        st.subheader("Library")
        st.dataframe(list_library_records(DB_PATH), use_container_width=True)

with tabs[5]:
    st.header("PX Job Engine")
    status_filter = st.selectbox("Job status filter", ["", "Pending", "Running", "Waiting", "Completed", "Failed", "Cancelled"])
    worker_job_filter = st.selectbox("Assigned worker filter", ["", "PX-H001", "PX-R001", "PX-A001", "PX-L001"])
    jobs = list_jobs(DB_PATH, status_filter, worker_job_filter)
    st.dataframe(jobs, use_container_width=True)
    job_ids = [job["id"] for job in jobs]
    selected_job = st.selectbox("Selected job", job_ids) if job_ids else None
    action_cols = st.columns(4)
    with action_cols[0]:
        if st.button("Run Job", disabled=not selected_job):
            st.json(execute_job(DB_PATH, str(selected_job)))
    with action_cols[1]:
        if st.button("Retry Job", disabled=not selected_job):
            try:
                st.json(retry_job(DB_PATH, str(selected_job)))
            except ValueError as exc:
                st.error(str(exc))
    with action_cols[2]:
        if st.button("Resume Job", disabled=not selected_job):
            st.json(resume_job(DB_PATH, str(selected_job)))
    with action_cols[3]:
        if st.button("Cancel Job", disabled=not selected_job):
            st.json(cancel_job(DB_PATH, str(selected_job)))

    with st.form("manual_job_form"):
        job_type = st.selectbox("Job type", [item.value for item in JobType])
        assigned_worker = st.selectbox("Assigned worker", ["", "PX-H001", "PX-R001", "PX-A001", "PX-L001"])
        priority = st.number_input("Priority", min_value=1, max_value=9, value=3, key="manual_job_priority")
        payload_json = st.text_area("Payload JSON", value='{"market": "Property Management", "source_text": "Tenants repeatedly complain about maintenance updates.", "company": "PropertyMe"}', key="manual_job_payload")
        if st.form_submit_button("Create Job"):
            try:
                payload = json.loads(payload_json) if payload_json else {}
                st.json(create_job(DB_PATH, job_type, assigned_worker or None, payload, int(priority)))
            except Exception as exc:
                st.error(str(exc))

with tabs[6]:
    st.header("Structured Logs")
    severity = st.selectbox("Severity", ["", "info", "warning", "error"])
    log_worker = st.selectbox("Log worker", ["", "PX-H001", "PX-R001", "PX-A001", "PX-L001"])
    log_job = st.text_input("Log job ID")
    logs = list_system_logs(DB_PATH, severity, log_worker, log_job)
    st.dataframe(logs, use_container_width=True)
    if st.button("Export Logs JSON"):
        write_json(EXPORT_DIR / "system_logs.json", logs)
        st.success("Exported logs to data/exports/system_logs.json")

with tabs[7]:
    st.header("Error Management")
    failed_jobs = list_jobs(DB_PATH, JobStatus.FAILED.value)
    st.dataframe(failed_jobs, use_container_width=True)
    failed_ids = [job["id"] for job in failed_jobs]
    selected_failed = st.selectbox("Failed job", failed_ids) if failed_ids else None
    error_cols = st.columns(3)
    with error_cols[0]:
        if st.button("Retry Failed Job", disabled=not selected_failed):
            try:
                st.json(retry_job(DB_PATH, str(selected_failed)))
            except ValueError as exc:
                st.error(str(exc))
    with error_cols[1]:
        worker_restart = st.selectbox("Restart worker", ["PX-H001", "PX-R001", "PX-A001", "PX-L001"])
        if st.button("Restart Worker"):
            restart_worker(DB_PATH, worker_restart)
            st.success(f"Restarted {worker_restart}")
    with error_cols[2]:
        if st.button("View Stack Trace", disabled=not selected_failed):
            st.dataframe(list_failure_history(DB_PATH, str(selected_failed)), use_container_width=True)
    st.subheader("Failure History")
    st.dataframe(list_failure_history(DB_PATH), use_container_width=True)

with tabs[8]:
    st.header("Worker Registry")
    st.dataframe(worker_registry(DB_PATH), use_container_width=True)

with tabs[9]:
    st.header("Component Registry")
    st.dataframe(component_registry(DB_PATH), use_container_width=True)

with tabs[10]:
    st.header("Milestone System")
    with st.form("milestone_form"):
        milestone_id = st.text_input("Milestone ID", value="M-0004")
        sprint = st.text_input("Sprint", value="Sprint 8")
        title = st.text_input("Title", key="milestone_title")
        description = st.text_area("Description", key="milestone_description")
        completed_by = st.text_input("Completed by", value="PX-E002")
        files_changed = st.text_area("Files changed")
        result = st.text_input("Result", value="Completed")
        if st.form_submit_button("Log Milestone"):
            try:
                st.json(add_milestone(DB_PATH, milestone_id, sprint, title, description, completed_by, files_changed, result))
            except Exception as exc:
                st.error(str(exc))
    if st.button("Complete Sprint 4 Milestone"):
        st.json(
            complete_sprint_milestone(
                DB_PATH,
                "Sprint 4",
                "Autonomous Execution Layer",
                "Added PX Job Engine, queues, orchestration, logging, error recovery, analytics, and provider interfaces.",
                "project_exchange/eos.py, project_exchange/database.py, streamlit_app.py, project_exchange/providers.py, tests",
                components_added="Job Engine, Logging System, Error Management",
                notes="Every action can now become a job; every job emits events and logs.",
                version="v4.0",
            )
        )
    st.dataframe(list_milestones(DB_PATH), use_container_width=True)

with tabs[11]:
    st.header("Engineering Journal")
    with st.form("journal_form"):
        journal_title = st.text_input("Title")
        entry_type = st.selectbox("Entry type", ["Architecture Decision", "Refactor", "Future Improvement", "Technical Debt", "Lesson Learned"])
        related_entity = st.text_input("Related entity")
        body = st.text_area("Entry")
        if st.form_submit_button("Add Journal Entry"):
            try:
                st.json(add_journal_entry(DB_PATH, journal_title, entry_type, body, related_entity))
            except ValueError as exc:
                st.error(str(exc))
    st.dataframe(list_journal_entries(DB_PATH), use_container_width=True)

with tabs[12]:
    st.header("PX-R001 Market Research Scanner")
    market = st.text_input("Market", value="Property Management", key="manual_research_market")
    company = st.text_input("Company", value="PropertyMe", key="manual_research_company")
    source_url = st.text_input("Source URL", key="manual_research_source_url")
    pasted_text = st.text_area("Paste article or source text", height=150)
    uploaded = st.file_uploader("Upload PDF, CSV, or TXT", type=["pdf", "csv", "txt"])
    file_text, source_type = uploaded_text(uploaded)
    source_text = file_text or pasted_text
    if source_url and not source_text:
        source_text = f"URL submitted for market scan: {source_url}"
        source_type = "url"
    if st.button("Create Research Pack", type="primary"):
        try:
            job = create_job(
                DB_PATH,
                JobType.RESEARCH_SCAN.value,
                "PX-R001",
                {"market": market, "company": company, "source_url": source_url, "source_text": source_text, "source_type": source_type},
                priority=1,
            )
            result = execute_job(DB_PATH, str(job["id"]))
            st.success(f"Research job finished: {result['id']}")
            st.json(result)
        except ValueError as exc:
            st.error(str(exc))
    st.subheader("Research Records")
    st.dataframe(list_research_records(DB_PATH), use_container_width=True)

with tabs[13]:
    st.header("PX-A001 Audit & Verification")
    records = list_research_records(DB_PATH)
    record_ids = [record["id"] for record in records]
    selected_research_id = st.selectbox("Research record", record_ids) if record_ids else None
    if st.button("Run Audit", disabled=not selected_research_id, type="primary"):
        job = create_job(DB_PATH, JobType.AUDIT_SCAN.value, "PX-A001", {"research_id": str(selected_research_id)}, priority=2)
        st.json(execute_job(DB_PATH, str(job["id"])))

    audits = list_audit_records(DB_PATH)
    audit_ids = [record["id"] for record in audits]
    selected_audit = st.selectbox("Audit decision", audit_ids) if audit_ids else None
    for column, (label, decision) in zip(
        st.columns(4),
        [
            ("Approve", AuditDecision.APPROVED),
            ("Reject", AuditDecision.REJECTED),
            ("Needs Evidence", AuditDecision.NEEDS_EVIDENCE),
            ("Archive", AuditDecision.ARCHIVE),
        ],
    ):
        with column:
            if st.button(label, disabled=not selected_audit):
                st.json(update_audit_decision(DB_PATH, str(selected_audit), decision, f"Manual decision: {label}."))
    if selected_audit:
        st.subheader("Reasoning Panel")
        st.json(get_audit_report(str(selected_audit)))
    st.subheader("Audit Records")
    st.dataframe(audits, use_container_width=True)

with tabs[14]:
    st.header("PX-L001 Library Manager")
    query = st.text_input("Search Library", key="library_search_query")
    category = st.text_input("Category filter", key="library_category_filter")
    tag = st.text_input("Tag filter", key="library_tag_filter")
    filter_cols = st.columns(5)
    worker_filter = filter_cols[0].text_input("Worker", key="library_worker_filter")
    company_filter = filter_cols[1].text_input("Company", key="library_company_filter")
    market_filter = filter_cols[2].text_input("Market", key="library_market_filter")
    source_filter = filter_cols[3].text_input("Source", key="library_source_filter")
    confidence_filter = filter_cols[4].number_input("Min confidence", min_value=0, max_value=100, value=0, key="library_confidence_filter")
    st.dataframe(
        search_library_records(
            DB_PATH,
            query,
            category,
            tag,
            worker_filter,
            company_filter,
            market_filter,
            source_filter,
            int(confidence_filter),
        ),
        use_container_width=True,
    )
    st.subheader("Changelog")
    st.dataframe(fetch_all(DB_PATH, "changelog"), use_container_width=True)

with tabs[15]:
    st.header("COMP-001 Prompt Engine v3")
    with st.form("prompt_form"):
        worker_id = st.selectbox("Worker assignment", ["PX-H001", "PX-A001", "PX-L001", "PX-R001"], key="prompt_worker_assignment")
        prompt_type = st.selectbox("Prompt type", ["System prompt", "Task prompt", "Validation prompt", "Scoring prompt", "Fallback prompt", "Report prompt"], key="prompt_type")
        prompt_text = st.text_area("Prompt text", height=140, key="prompt_text")
        if st.form_submit_button("Create Prompt"):
            try:
                st.json(create_prompt(DB_PATH, worker_id, prompt_type, prompt_text))
            except ValueError as exc:
                st.error(str(exc))

    prompt_query = st.text_input("Prompt search")
    prompt_worker = st.selectbox("Prompt worker filter", ["", "PX-H001", "PX-A001", "PX-L001", "PX-R001"])
    prompt_status = st.selectbox("Status filter", ["", "Draft", "Approved", "Retired"], key="prompt_status_filter")
    prompts = search_prompts(DB_PATH, prompt_query, prompt_worker, prompt_status)
    st.dataframe(prompts, use_container_width=True)

    prompt_ids = [prompt["id"] for prompt in prompts]
    selected_prompt = st.selectbox("Selected prompt", prompt_ids) if prompt_ids else None
    if selected_prompt:
        col_1, col_2, col_3 = st.columns(3)
        with col_1:
            if st.button("Approve Prompt"):
                job = create_job(DB_PATH, JobType.PROMPT_APPROVAL.value, None, {"prompt_id": selected_prompt}, priority=3)
                st.json(execute_job(DB_PATH, str(job["id"])))
        with col_2:
            if st.button("Retire Prompt"):
                st.json(retire_prompt(DB_PATH, selected_prompt))
        with col_3:
            expected = st.text_input("Expected output contains", value="response", key="prompt_expected_output")
            if st.button("Run Prompt Test"):
                job = create_job(
                    DB_PATH,
                    JobType.PROMPT_TEST.value,
                    None,
                    {"prompt_id": selected_prompt, "test_input": "Sample local test input", "expected_output": expected},
                    priority=3,
                )
                st.json(execute_job(DB_PATH, str(job["id"])))
        benchmark_label = st.text_input("Benchmark variant", value="A")
        if st.button("Run Benchmark"):
            st.json(benchmark_prompt(DB_PATH, selected_prompt, "Benchmark local test input", "response", benchmark_label))

        with st.form("version_form"):
            new_version = st.text_input("New version", value="v1.0.1")
            new_text = st.text_area("Version text", height=120)
            if st.form_submit_button("Create Version"):
                try:
                    st.json(create_prompt_version(DB_PATH, selected_prompt, new_text, new_version, PromptStatus.DRAFT))
                except ValueError as exc:
                    st.error(str(exc))

        versions = list_prompt_versions(DB_PATH, selected_prompt)
        st.subheader("Version History")
        st.dataframe(versions, use_container_width=True)
        version_ids = [record["version"] for record in versions]
        rollback_version = st.selectbox("Rollback version", version_ids) if version_ids else None
        if st.button("Rollback", disabled=not rollback_version):
            st.json(rollback_prompt(DB_PATH, selected_prompt, str(rollback_version)))
    st.subheader("Test History")
    st.dataframe(fetch_all(DB_PATH, "prompt_tests"), use_container_width=True)
    st.subheader("Benchmarks")
    st.dataframe(list_prompt_benchmarks(DB_PATH, selected_prompt or ""), use_container_width=True)

with tabs[16]:
    st.header("Knowledge Graph")
    entity_id = st.text_input("Entity ID filter")
    st.dataframe(list_knowledge_edges(DB_PATH, entity_id), use_container_width=True)

with tabs[17]:
    st.header("Worker Chat")
    msg_cols = st.columns(2)
    sender = msg_cols[0].selectbox("Sender", ["PX-H001", "PX-R001", "PX-A001", "PX-L001", "COMP-001", "Notification"])
    receiver = msg_cols[1].selectbox("Receiver", ["PX-H001", "PX-R001", "PX-A001", "PX-L001", "COMP-001", "Notification"])
    message_priority = st.number_input("Priority", min_value=1, max_value=9, value=3, key="worker_message_priority")
    message = st.text_area("Message")
    if st.button("Send Worker Message"):
        if sender != "PX-H001" and receiver != "PX-H001":
            st.json(route_worker_message(DB_PATH, sender, receiver, message, priority=int(message_priority)))
        else:
            st.json(send_worker_message(DB_PATH, sender, receiver, message, priority=int(message_priority)))
    st.dataframe(list_worker_messages(DB_PATH), use_container_width=True)

with tabs[18]:
    st.header("Settings")
    st.caption("Store provider selections and local configuration. API key values are accepted but should stay local.")
    with st.form("settings_form"):
        category = st.selectbox("Category", ["API Keys", "Providers", "LLM", "Database", "Workers", "Notifications", "Debug"])
        key = st.text_input("Key")
        value = st.text_input("Value", type="password" if category == "API Keys" else "default")
        if st.form_submit_button("Save Setting"):
            st.json(set_setting(DB_PATH, key, value, category))
    st.dataframe(list_settings(DB_PATH), use_container_width=True)

with tabs[19]:
    st.header("Provider Settings")
    st.caption("Connection status is loaded from the project root .env file. API keys are never displayed.")
    provider_rows = provider_connection_rows()
    st.dataframe(provider_rows, use_container_width=True)
    connected = sum(1 for row in provider_rows if row["status"] == "connected")
    invalid = sum(1 for row in provider_rows if row["status"] == "invalid")
    disconnected = sum(1 for row in provider_rows if row["status"] == "disconnected")
    cols = st.columns(3)
    cols[0].metric("Connected", connected)
    cols[1].metric("Disconnected", disconnected)
    cols[2].metric("Invalid", invalid)
    st.info("Expected .env names: OPENAI_API_KEY, TAVILY_API_KEY, SERPAPI_API_KEY, NEWSAPI_API_KEY")

with tabs[20]:
    st.header("Activity History")
    st.dataframe(list_activity(DB_PATH, 200), use_container_width=True)
    st.subheader("Notifications")
    st.dataframe(list_notifications(DB_PATH, 200), use_container_width=True)

with tabs[21]:
    st.header("Local Data")
    export_table = st.selectbox(
        "Export table",
        [
            "research_records",
            "audit_records",
            "library_records",
            "prompts",
            "prompt_versions",
            "prompt_tests",
            "workers",
            "components",
            "worker_activity",
            "notifications",
            "changelog",
            "events",
            "milestones",
            "engineering_journal",
            "jobs",
            "system_logs",
            "failure_history",
            "provider_runs",
            "research_packages",
            "settings",
            "worker_messages",
            "knowledge_edges",
            "prompt_benchmarks",
            "worker_memory",
            "execution_plans",
            "system_recommendations",
            "audit_reasoning",
            "objectives",
            "operating_schedules",
            "operating_briefs",
            "performance_snapshots",
            "research_history",
            "research_performance",
            "prompt_usage",
            "studies",
            "study_signals",
            "study_findings",
            "finding_audits",
            "opportunity_records",
            "study_briefs",
            "demo_archive",
        ],
    )
    if st.button("Export Table JSON"):
        records = fetch_all(DB_PATH, export_table)
        output_path = EXPORT_DIR / f"{export_table}.json"
        write_json(output_path, records)
        st.success(f"Exported {len(records)} records to {output_path}")
        st.json(records)
    uploaded_json = st.file_uploader("Preview JSON file", type=["json"])
    if uploaded_json:
        st.json(json.load(uploaded_json))
    if st.button("Load Sample Research Preview"):
        st.json(read_json("data/sample_research.json"))

with tabs[22]:
    st.header("PX-H001 Head of Functions")
    st.caption("Operating executive for objectives, schedules, worker load, performance, briefs, recovery, and recommendations.")
    action_cols = st.columns(5)
    with action_cols[0]:
        if st.button("Refresh Worker Memory", type="primary"):
            st.json(refresh_worker_memory(DB_PATH))
    with action_cols[1]:
        if st.button("Monitor and Recover"):
            st.json(monitor_and_recover(DB_PATH))
    with action_cols[2]:
        if st.button("Generate Recommendations"):
            st.json(generate_system_recommendations(DB_PATH))
    with action_cols[3]:
        if st.button("Daily Brief"):
            st.json(generate_operating_brief(DB_PATH, "daily"))
    with action_cols[4]:
        if st.button("Performance Snapshot"):
            st.json(create_performance_snapshot(DB_PATH, "manual"))

    st.subheader("Objective Tracker")
    with st.form("objective_form"):
        objective_title = st.text_input("Objective title", value="Research the Irish property management market")
        objective_description = st.text_area("Objective description")
        objective_cols = st.columns(3)
        objective_priority = objective_cols[0].number_input("Objective priority", min_value=1, max_value=9, value=2)
        objective_cadence = objective_cols[1].selectbox("Cadence", ["manual", "daily", "weekly"])
        objective_metric = objective_cols[2].text_input("Success metric", value="Verified library records")
        if st.form_submit_button("Create Objective"):
            try:
                st.json(create_objective(DB_PATH, objective_title, objective_description, int(objective_priority), objective_cadence, objective_metric))
            except ValueError as exc:
                st.error(str(exc))
    st.dataframe(list_objectives(DB_PATH), use_container_width=True)

    st.subheader("Research Scheduling")
    objectives = list_objectives(DB_PATH)
    objective_ids = [""] + [record["id"] for record in objectives]
    with st.form("schedule_form"):
        schedule_name = st.text_input("Schedule name", value="Daily market research")
        schedule_cadence = st.selectbox("Schedule cadence", ["daily", "weekly", "manual"])
        schedule_worker = st.selectbox("Schedule worker", ["PX-R001", "PX-A001", "PX-L001", "PX-H001"])
        schedule_job_type = st.selectbox("Schedule job type", [item.value for item in JobType])
        schedule_objective = st.selectbox("Linked objective", objective_ids)
        schedule_priority = st.number_input("Schedule priority", min_value=1, max_value=9, value=2)
        schedule_payload = st.text_area("Schedule payload JSON", value='{"market": "Irish property management", "industry": "Property Management", "keyword": "complaints software"}')
        if st.form_submit_button("Create Schedule"):
            try:
                st.json(
                    create_operating_schedule(
                        DB_PATH,
                        schedule_name,
                        schedule_cadence,
                        schedule_worker,
                        schedule_job_type,
                        json.loads(schedule_payload) if schedule_payload else {},
                        schedule_objective,
                        int(schedule_priority),
                    )
                )
            except Exception as exc:
                st.error(str(exc))
    schedules = list_operating_schedules(DB_PATH)
    st.dataframe(schedules, use_container_width=True)
    schedule_ids = [record["id"] for record in schedules]
    selected_schedule = st.selectbox("Run schedule", schedule_ids) if schedule_ids else None
    schedule_run_cols = st.columns(2)
    with schedule_run_cols[0]:
        if st.button("Run Selected Schedule", disabled=not selected_schedule):
            st.json(run_operating_schedule(DB_PATH, str(selected_schedule)))
    with schedule_run_cols[1]:
        if st.button("Run Daily Schedules"):
            st.json(run_due_schedules(DB_PATH, "daily"))

    st.subheader("Execution Plans")
    st.dataframe(list_execution_plans(DB_PATH), use_container_width=True)
    st.subheader("Worker Load Monitor")
    st.dataframe(worker_load_monitor(DB_PATH), use_container_width=True)
    st.subheader("Priority Manager")
    st.json(operating_summary(DB_PATH)["priorities"])
    st.subheader("Worker Memory")
    memory = list_worker_memory(DB_PATH)
    if memory:
        st.dataframe(memory, use_container_width=True)
    else:
        st.info("No worker memory yet. Run Refresh Worker Memory.")
    st.subheader("Operating Briefs")
    st.dataframe(list_operating_briefs(DB_PATH), use_container_width=True)
    st.subheader("Performance Snapshots")
    st.dataframe(list_performance_snapshots(DB_PATH), use_container_width=True)
    st.subheader("System Recommendations")
    st.dataframe(list_system_recommendations(DB_PATH), use_container_width=True)

with tabs[23]:
    st.header("Golden Study 001")
    st.caption("Traceable opportunity creation for the global Property Management market.")
    study = get_or_create_default_study(DB_PATH)
    progress = study_progress(DB_PATH, DEFAULT_STUDY_ID)
    if demo_warning_active(DB_PATH, DEFAULT_STUDY_ID):
        st.warning("GS-001 is currently using demo/sample data. Do not treat this as verified market evidence.")
    else:
        st.success(f"GS-001 mode: {progress['study_mode'].title()} | Verification pending: {progress['verification_pending_count']} | Engineering Ready: {len(progress['engineering_ready'])}")

    metric_cols = st.columns(8)
    metric_cols[0].metric("Study", study["id"])
    metric_cols[1].metric("Signals", progress["signals_collected"])
    metric_cols[2].metric("Findings", progress["findings_created"])
    metric_cols[3].metric("Audits", progress["audits_completed"])
    metric_cols[4].metric("Approved Opportunities", progress["opportunities_approved"])
    metric_cols[5].metric("Engineering Ready", len(progress["engineering_ready"]))
    metric_cols[6].metric("Demo Records", progress["demo_records_count"])
    metric_cols[7].metric("Average OCI", progress["average_oci"])
    quality_cols = st.columns(4)
    quality_cols[0].metric("Database Status", "Connected")
    quality_cols[1].metric("Pending Verification", progress["verification_pending_count"])
    quality_cols[2].metric("Countries", len(progress["countries_covered"]))
    quality_cols[3].metric("Evidence Sources", progress["source_coverage"])

    control_cols = st.columns(5)
    with control_cols[0]:
        study_mode = st.selectbox("Study mode", ["demo", "production"], index=0 if progress["study_mode"] == "demo" else 1, key="gs001_mode")
        production_confirmed = st.checkbox("Confirm production GS-001", key="gs001_production_confirmed")
        if st.button("Create / Refresh GS-001", key="gs001_create_refresh"):
            try:
                result = create_study(
                    DB_PATH,
                    DEFAULT_STUDY_ID,
                    "Global Property Management Golden Study",
                    "Property Management",
                    "Global",
                    "Global",
                    "Property managers, Tenants, Housing associations, Facilities managers, Estate management companies, Condo / HOA managers, Commercial property managers, Letting agents, Property owners, Maintenance contractors",
                    "Find verified, traceable market opportunities backed by repeated complaints and evidence.",
                    "Active",
                    "Golden Study 001 default study.",
                    study_mode=study_mode,
                    production_confirmed=production_confirmed,
                )
                with st.expander("Study JSON"):
                    st.json(result)
            except ValueError as exc:
                st.error(str(exc))
    with control_cols[1]:
        if st.button("Generate Findings", key="gs001_generate_findings"):
            with st.expander("Generated Findings JSON", expanded=True):
                st.json(generate_findings(DB_PATH, DEFAULT_STUDY_ID))
    with control_cols[2]:
        if st.button("Run Audit Batch", key="gs001_run_audit_batch"):
            try:
                with st.expander("Audit Batch JSON", expanded=True):
                    st.json(run_audit_batch(DB_PATH, DEFAULT_STUDY_ID))
            except ValueError as exc:
                st.error(str(exc))
    with control_cols[3]:
        if st.button("Approve Opportunities", key="gs001_approve_opportunities"):
            try:
                with st.expander("Approved Opportunities JSON", expanded=True):
                    st.json(approve_audited_opportunities(DB_PATH, DEFAULT_STUDY_ID))
            except ValueError as exc:
                st.error(str(exc))
    with control_cols[4]:
        if st.button("Executive Brief", key="gs001_executive_brief"):
            brief = generate_executive_brief(DB_PATH, DEFAULT_STUDY_ID)
            st.text(brief["body"])
            with st.expander("Raw Data"):
                st.json(brief)

    validation_cols = st.columns(2)
    with validation_cols[0]:
        if st.button("Validate Golden Study Integrity", key="gs001_validate_integrity"):
            validation = validate_golden_study_integrity(DB_PATH, DEFAULT_STUDY_ID)
            if validation["passed"]:
                st.success("Golden Study integrity checks passed.")
            else:
                st.error(f"{validation['failed_count']} integrity checks failed.")
            st.dataframe(validation["checks"], use_container_width=True)
    with validation_cols[1]:
        if st.button("Archive Demo Data", key="gs001_archive_demo_data"):
            archived = []
            for table_name, rows in {
                "study_signals": list_signals(DB_PATH, DEFAULT_STUDY_ID),
                "study_findings": list_findings(DB_PATH, DEFAULT_STUDY_ID),
                "finding_audits": list_finding_audits(DB_PATH, DEFAULT_STUDY_ID),
                "opportunity_records": list_opportunities(DB_PATH, DEFAULT_STUDY_ID),
            }.items():
                for row in rows:
                    if row.get("is_demo") and row.get("status") != "archived":
                        archived.append(archive_record(DB_PATH, table_name, str(row["id"])))
            with st.expander("Archive Result JSON", expanded=True):
                st.json({"archived_demo_records": archived})

    st.subheader("Signals")
    with st.form("golden_signal_form"):
        sig_cols = st.columns(3)
        signal_study_id = sig_cols[0].text_input("Study ID", value=DEFAULT_STUDY_ID, key="golden_signal_study_id")
        signal_country = sig_cols[1].text_input("Country", value="Unknown", key="golden_signal_country")
        signal_product = sig_cols[2].text_input("Company / Product", key="golden_signal_product")
        source_cols = st.columns(3)
        signal_source = source_cols[0].text_input("Source URL", key="golden_signal_source")
        signal_source_name = source_cols[1].text_input("Source name", key="golden_signal_source_name")
        signal_source_type = source_cols[2].selectbox("Source type", ["manual", "url", "pdf", "csv", "txt", "article", "provider"], key="golden_signal_source_type")
        meta_cols = st.columns(3)
        signal_stakeholder = meta_cols[0].text_input("Stakeholder type", value="Unknown", key="golden_signal_stakeholder")
        signal_source_date = meta_cols[1].date_input("Evidence date", key="golden_signal_source_date")
        signal_origin = meta_cols[2].selectbox("Data origin", ["manual", "provider", "verified_import", "demo"], key="golden_signal_origin")
        signal_text = st.text_area(
            "Raw evidence text",
            value="",
            key="golden_signal_text",
        )
        if st.form_submit_button("Create Signal"):
            try:
                result = create_signal(
                    DB_PATH,
                    signal_text,
                    signal_study_id,
                    signal_source,
                    signal_source_name,
                    signal_source_type,
                    signal_source_date.isoformat(),
                    signal_country,
                    signal_stakeholder,
                    signal_product,
                    signal_origin,
                )
                with st.expander("Signal JSON", expanded=True):
                    st.json(result)
            except ValueError as exc:
                st.error(str(exc))

    with st.expander("Run Sample Research Batch"):
        if st.button("Load Sample GS-001 Batch"):
            sample = [
                {
                    "country": "Ireland",
                    "stakeholder_type": "Property managers",
                    "source_name": "Irish property forum",
                    "data_origin": "demo",
                    "raw_text": "Property managers in Ireland repeatedly complain that maintenance updates are slow and tenants chase responses multiple times.",
                },
                {
                    "country": "United Kingdom",
                    "stakeholder_type": "Tenants",
                    "source_name": "UK tenant review",
                    "data_origin": "demo",
                    "raw_text": "Tenants in the United Kingdom complain that repair communication is poor, updates are delayed, and maintenance requests need repeated follow-up.",
                },
                {
                    "country": "United States",
                    "stakeholder_type": "Property owners",
                    "source_name": "US owner review",
                    "data_origin": "demo",
                    "raw_text": "Property owners in the United States say maintenance coordination is manual, slow, and expensive across property management software.",
                },
            ]
            st.json(run_research_batch(DB_PATH, sample, DEFAULT_STUDY_ID))

    st.subheader("Study Records")
    st.dataframe(list_studies(DB_PATH), use_container_width=True)
    st.subheader("Signals")
    signals = list_signals(DB_PATH, DEFAULT_STUDY_ID)
    st.dataframe(signals, use_container_width=True)
    st.subheader("Findings")
    findings = list_findings(DB_PATH, DEFAULT_STUDY_ID)
    st.dataframe(findings, use_container_width=True)
    finding_ids = [record["id"] for record in findings]
    selected_finding = st.selectbox("Finding detail", finding_ids, key="golden_selected_finding") if finding_ids else None
    if selected_finding:
        finding_cols = st.columns(3)
        with finding_cols[0]:
            if st.button("Audit Finding"):
                try:
                    with st.expander("Audit Finding JSON", expanded=True):
                        st.json(audit_finding(DB_PATH, str(selected_finding)))
                except ValueError as exc:
                    st.error(str(exc))
        with finding_cols[1]:
            if st.button("View Evidence Chain"):
                with st.expander("Finding Evidence Chain JSON", expanded=True):
                    st.json(finding_evidence(DB_PATH, str(selected_finding)))
        with finding_cols[2]:
            if st.button("Archive Finding"):
                with st.expander("Archive Finding JSON", expanded=True):
                    st.json(archive_record(DB_PATH, "study_findings", str(selected_finding)))

    st.subheader("Audits")
    st.dataframe(list_finding_audits(DB_PATH, DEFAULT_STUDY_ID), use_container_width=True)
    st.subheader("Approved Opportunities")
    opportunities = list_opportunities(DB_PATH, DEFAULT_STUDY_ID)
    st.dataframe(opportunities, use_container_width=True)
    opportunity_ids = [record["id"] for record in opportunities]
    selected_opportunity = st.selectbox("Opportunity detail", opportunity_ids, key="golden_selected_opportunity") if opportunity_ids else None
    if selected_opportunity:
        opportunity_cols = st.columns(2)
        with opportunity_cols[0]:
            if st.button("View Traceability Chain"):
                with st.expander("Opportunity Evidence Chain JSON", expanded=True):
                    st.json(traceability_chain(DB_PATH, str(selected_opportunity)))
        with opportunity_cols[1]:
            if st.button("Archive Opportunity"):
                with st.expander("Archive Opportunity JSON", expanded=True):
                    st.json(archive_record(DB_PATH, "opportunity_records", str(selected_opportunity)))

    st.subheader("Engineering Specs")
    st.dataframe([row for row in opportunities if row.get("engineering_status")], use_container_width=True)
    st.subheader("Executive Briefs")
    st.dataframe(list_study_briefs(DB_PATH, DEFAULT_STUDY_ID), use_container_width=True)
    st.subheader("Coverage")
    coverage_cols = st.columns(3)
    coverage_cols[0].write(", ".join(progress["countries_covered"]) or "No countries yet")
    coverage_cols[1].write(", ".join(progress["stakeholders_covered"]) or "No stakeholders yet")
    coverage_cols[2].metric("Source Coverage", progress["source_coverage"])
