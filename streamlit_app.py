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
    approval_feedback,
    archive_all_demo_data,
    archive_current_production_run_and_start_fresh,
    archive_record,
    audit_batch_feedback,
    audit_finding,
    create_signal,
    demo_warning_active,
    delete_archived_demo_data,
    discovery_learning_dashboard,
    findings_feedback,
    create_study,
    finding_evidence,
    generate_executive_brief,
    generate_findings,
    get_active_study_run,
    get_or_create_default_study,
    evidence_quality_dashboard,
    list_finding_audits,
    list_findings,
    list_opportunities,
    list_signals,
    list_studies,
    list_study_runs,
    list_study_briefs,
    mark_engineering_ready,
    production_pipeline_statuses,
    pull_real_market_evidence,
    run_audit_batch,
    run_research_batch,
    signal_trace_card_view_model,
    study_progress,
    switch_study_run_mode,
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
    study = get_or_create_default_study(DB_PATH)
    active_run = get_active_study_run(DB_PATH, DEFAULT_STUDY_ID)
    active_run_id = str((active_run or {}).get("id") or "")
    run_mode = str((active_run or {}).get("study_mode") or "none")
    run_status = str((active_run or {}).get("status") or "none")
    is_demo_run = run_mode == "demo"
    is_production_run = run_mode == "production"
    include_demo_view = is_demo_run
    progress = study_progress(DB_PATH, DEFAULT_STUDY_ID, active_run_id, include_demo=include_demo_view) if active_run_id else {
        "study_id": DEFAULT_STUDY_ID,
        "active_run_id": "",
        "run_status": "none",
        "study_mode": "none",
        "signals_collected": 0,
        "findings_created": 0,
        "audits_completed": 0,
        "opportunities_approved": 0,
        "engineering_ready": [],
        "demo_records_count": 0,
        "verification_pending_count": 0,
        "average_oci": 0,
        "countries_covered": [],
        "stakeholders_covered": [],
        "source_coverage": 0,
        "top_opportunities": [],
    }
    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border: 1px solid #E5EAF2;
            border-radius: 12px;
            box-shadow: 0 8px 22px rgba(31, 41, 55, 0.06);
            background: #FFFFFF;
        }
        div.stButton > button {
            border-radius: 10px;
            border: 1px solid #B7CCFF;
            color: #003399;
            background: #FFFFFF;
            font-weight: 650;
        }
        div.stButton > button[kind="primary"] {
            border-color: #003399;
            background: #003399;
            color: #FFFFFF;
        }
        div.stButton > button:hover {
            border-color: #0047CC;
            background: #F3F7FF;
            color: #003399;
        }
        .px-hero {
            border: 1px solid #D7E2F6;
            border-radius: 18px;
            padding: 22px 24px;
            background: linear-gradient(135deg, #FFFFFF 0%, #F7F9FC 100%);
            box-shadow: 0 12px 36px rgba(31, 41, 55, 0.08);
            margin-bottom: 18px;
        }
        .px-hero h2 {
            margin: 0 0 4px 0;
            color: #1F2937;
        }
        .golden-shell {
            border: 1px solid #C9D9FF;
            border-radius: 20px;
            background: #FFFFFF;
            box-shadow: 0 18px 45px rgba(31, 41, 55, 0.10);
            margin: 8px 0 18px 0;
            overflow: hidden;
        }
        .golden-shell-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            padding: 18px 22px;
            border-bottom: 1px solid #E5EAF2;
            background: linear-gradient(90deg, #003399 0%, #0047CC 52%, #F7F9FC 52%, #FFFFFF 100%);
        }
        .golden-shell-title {
            display: flex;
            align-items: center;
            gap: 14px;
            color: #FFFFFF;
        }
        .golden-brand-mark {
            width: 44px;
            height: 44px;
            border-radius: 14px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background: rgba(255,255,255,0.14);
            border: 1px solid rgba(255,255,255,0.30);
            font-weight: 850;
            letter-spacing: 0;
        }
        .golden-shell-title h2 {
            margin: 0;
            color: #FFFFFF;
            font-size: 1.35rem;
        }
        .golden-shell-title p {
            margin: 2px 0 0 0;
            color: rgba(255,255,255,0.82);
            font-size: 0.9rem;
        }
        .golden-shell-actions {
            display: flex;
            gap: 8px;
            align-items: center;
            flex-wrap: wrap;
            justify-content: flex-end;
        }
        .golden-shell-body {
            padding: 16px;
            background: #F7F9FC;
        }
        .golden-status-grid {
            display: grid;
            grid-template-columns: repeat(6, minmax(0, 1fr));
            gap: 10px;
        }
        .golden-status-card {
            border: 1px solid #E5EAF2;
            border-radius: 14px;
            padding: 14px;
            background: #FFFFFF;
            box-shadow: 0 8px 18px rgba(31, 41, 55, 0.05);
            border-top: 4px solid #003399;
            min-height: 112px;
        }
        .golden-status-card.is-green { border-top-color: #2DBE60; }
        .golden-status-card.is-orange { border-top-color: #F4B400; }
        .golden-status-card.is-blue { border-top-color: #2F6BFF; }
        .golden-status-card.is-red { border-top-color: #D93025; }
        .golden-status-label {
            color: #6B7280;
            font-size: 0.78rem;
            font-weight: 750;
            text-transform: uppercase;
        }
        .golden-status-value {
            color: #1F2937;
            font-size: 1.65rem;
            font-weight: 850;
            line-height: 1.05;
            margin-top: 8px;
        }
        .golden-status-note {
            color: #6B7280;
            font-size: 0.84rem;
            margin-top: 6px;
        }
        .golden-callout {
            margin-top: 12px;
            border: 1px solid #B7CCFF;
            background: #EEF4FF;
            color: #003399;
            border-radius: 14px;
            padding: 12px 14px;
            display: flex;
            justify-content: space-between;
            gap: 12px;
            align-items: center;
        }
        .golden-callout strong {
            color: #003399;
        }
        .px-muted {
            color: #6B7280;
            font-size: 0.92rem;
        }
        .px-card-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 12px;
            margin: 12px 0 16px 0;
        }
        .px-metric-card {
            border: 1px solid #E5EAF2;
            border-radius: 14px;
            padding: 16px;
            background: #FFFFFF;
            box-shadow: 0 8px 20px rgba(31, 41, 55, 0.05);
        }
        .px-metric-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
            margin-bottom: 10px;
        }
        .px-icon {
            width: 34px;
            height: 34px;
            border-radius: 10px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background: #EEF4FF;
            color: #003399;
            font-weight: 800;
            font-size: 0.78rem;
        }
        .px-metric-value {
            font-size: 2rem;
            font-weight: 800;
            color: #1F2937;
            line-height: 1;
        }
        .px-card-title {
            font-weight: 750;
            color: #1F2937;
            margin-bottom: 4px;
        }
        .px-badge {
            border-radius: 999px;
            padding: 4px 9px;
            font-size: 0.72rem;
            font-weight: 750;
            border: 1px solid #E5EAF2;
            color: #1F2937;
            background: #F7F9FC;
            white-space: nowrap;
        }
        .px-badge-blue { color: #003399; background: #EEF4FF; border-color: #B7CCFF; }
        .px-badge-green { color: #137333; background: #EAF7EF; border-color: #BFE8CD; }
        .px-badge-orange { color: #9A5B00; background: #FFF6DF; border-color: #FFE0A3; }
        .px-badge-yellow { color: #7A5A00; background: #FFFBEA; border-color: #F8E69A; }
        .px-badge-red { color: #A50E0E; background: #FCEDEA; border-color: #F5C2BD; }
        .px-badge-grey { color: #4B5563; background: #F3F4F6; border-color: #E5E7EB; }
        .px-workflow {
            display: grid;
            grid-template-columns: repeat(6, minmax(0, 1fr));
            gap: 10px;
            margin: 12px 0 18px 0;
        }
        .px-stage {
            border: 1px solid #E5EAF2;
            border-radius: 14px;
            padding: 14px;
            background: #FFFFFF;
        }
        .px-section-header {
            border: 1px solid #D7E2F6;
            border-left: 6px solid #003399;
            border-radius: 16px;
            padding: 16px 18px;
            background: linear-gradient(90deg, #FFFFFF 0%, #F7F9FC 100%);
            box-shadow: 0 8px 22px rgba(31, 41, 55, 0.06);
            margin: 10px 0 14px 0;
        }
        .px-section-header h3 {
            margin: 0;
            color: #003399;
            font-size: 1.15rem;
        }
        .px-section-header p {
            margin: 4px 0 0 0;
            color: #6B7280;
            font-size: 0.9rem;
        }
        .px-business-card {
            border: 1px solid #E5EAF2;
            border-top: 4px solid #003399;
            border-radius: 14px;
            padding: 16px;
            background: #FFFFFF;
            box-shadow: 0 8px 20px rgba(31, 41, 55, 0.055);
            margin-bottom: 12px;
        }
        .px-business-card h4 {
            margin: 0 0 8px 0;
            color: #1F2937;
            font-size: 1rem;
        }
        .px-card-meta {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            align-items: center;
            margin-bottom: 10px;
        }
        .px-card-summary {
            color: #1F2937;
            line-height: 1.45;
            margin: 0 0 12px 0;
        }
        .px-card-kpis {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 8px;
            margin-top: 10px;
        }
        .px-card-kpi {
            border: 1px solid #E5EAF2;
            border-radius: 10px;
            padding: 9px;
            background: #F7F9FC;
        }
        .px-card-kpi span {
            display: block;
            color: #6B7280;
            font-size: 0.72rem;
            font-weight: 700;
        }
        .px-card-kpi strong {
            display: block;
            color: #1F2937;
            font-size: 1rem;
            margin-top: 3px;
        }
        .px-brief-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
            margin-top: 10px;
        }
        .px-brief-item {
            border: 1px solid #E5EAF2;
            border-radius: 12px;
            padding: 12px;
            background: #F7F9FC;
        }
        .px-brief-item strong {
            display: block;
            color: #003399;
            margin-bottom: 4px;
        }
        @media (max-width: 1000px) {
            .px-card-grid, .px-workflow, .px-card-kpis, .px-brief-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
            .golden-shell-header {
                background: linear-gradient(180deg, #003399 0%, #0047CC 62%, #F7F9FC 62%, #FFFFFF 100%);
                align-items: flex-start;
                flex-direction: column;
            }
            .golden-status-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    def html_escape(value: object) -> str:
        return (
            str(value or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    def signal_provider_metadata(record: dict[str, object]) -> dict[str, object]:
        raw = str(record.get("source_name") or "").strip()
        if not raw.startswith("{"):
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed, dict) and parsed.get("metadata_type") == "provider_evidence":
            return parsed
        return {}

    def get_signal_source_display_name(record: dict[str, object]) -> str:
        metadata = signal_provider_metadata(record)
        source_name = record.get("source_name")
        if metadata.get("original_title"):
            return str(metadata["original_title"])
        if isinstance(source_name, str) and source_name.strip() and not source_name.strip().startswith("{"):
            return source_name
        source_url = str(record.get("source_url") or "").strip()
        if source_url:
            try:
                from urllib.parse import urlparse

                domain = urlparse(source_url).netloc.replace("www.", "")
                return domain or source_url
            except Exception:
                return source_url
        if metadata.get("provider_name"):
            return str(metadata["provider_name"])
        return "Unknown source"

    def clean_signal_source_title(signal: dict[str, object]) -> str:
        return get_signal_source_display_name(signal)

    def source_label(record: dict[str, object]) -> str:
        metadata = signal_provider_metadata(record)
        return str(
            record.get("source_url")
            or metadata.get("original_title")
            or metadata.get("provider_name")
            or record.get("source_name")
            or "No source"
        )

    def render_signal_trace_card(signal: dict[str, object]) -> None:
        try:
            view = signal_trace_card_view_model(signal)
            with st.container(border=True):
                render_business_card(
                    clean_signal_source_title(signal),
                    view["verification_status"],
                    view["raw_text"],
                    [
                        ("Provider", view["provider"]),
                        ("Source URL", view["source_url"]),
                        ("Country", view["country"]),
                        ("Stakeholder", view["stakeholder"]),
                        ("Retrieved", view["retrieved"]),
                        ("Evidence Classification", view["evidence_classification"]),
                        ("Source Type", view["source_type"]),
                        ("Trust", view["source_trust_score"]),
                        ("Production Eligible", view["production_eligible"]),
                    ],
                )
                st.caption(f"Original query: {view['query']}")
                st.caption(f"Reason: {view['why_accepted']}")
                st.caption(f"Pain keywords: {view['pain_keywords_matched']}")
                st.caption(f"Context keywords: {view['context_keywords_matched']}")
                if signal.get("source_url"):
                    st.markdown(f"[Open source]({signal['source_url']})")
                with st.expander("Technical Details"):
                    st.json(signal)
        except Exception as exc:
            st.warning("This signal could not be rendered as a card, but the record is preserved.")
            with st.expander("Technical Details"):
                st.json({"error": str(exc), "signal": signal})

    def render_rejected_signal_card(signal: dict[str, object]) -> None:
        try:
            view = signal_trace_card_view_model(signal)
            badge = view["evidence_classification"].replace("_", " ").title()
            if view["production_eligible"] != "YES":
                badge = f"{badge} / Not Production Eligible"
            with st.container(border=True):
                st.caption(badge)
                st.markdown(f"**{clean_signal_source_title(signal)}**")
                st.write(view["why_accepted"])
                cols = st.columns(4)
                cols[0].metric("Classification", view["evidence_classification"].replace("_", " ").title())
                cols[1].metric("Source Type", view["source_type"].replace("_", " ").title())
                cols[2].metric("Trust", view["source_trust_score"])
                cols[3].metric("Provider", view["provider"])
                if signal.get("source_url"):
                    st.markdown(f"[Open source]({signal['source_url']})")
                with st.expander("Technical Details"):
                    st.json(signal)
        except Exception as exc:
            st.warning("This context record could not be rendered as a card, but the record is preserved.")
            with st.expander("Technical Details"):
                st.json({"error": str(exc), "signal": signal})

    def render_research_run_result(result: dict[str, object]) -> None:
        if result.get("status") == "completed":
            st.success("Research Run Complete")
        elif result.get("status") == "blocked":
            st.warning(str(result.get("message") or "Research run blocked"))
        else:
            st.warning(str(result.get("message") or "Research run finished with no stored signals"))
        summary_cols = st.columns(4)
        summary_cols[0].metric("Queries Executed", result.get("queries_executed", result.get("sources_searched", 0)))
        summary_cols[1].metric("URLs Retrieved", result.get("urls_retrieved", result.get("candidate_results_found", 0)))
        summary_cols[2].metric("Accepted Signals", result.get("accepted_signals", result.get("signals_stored", 0)))
        summary_cols[3].metric("Rejected Signals", result.get("rejected_signals", 0))
        detail_cols = st.columns(4)
        detail_cols[0].metric("URLs Skipped", result.get("urls_skipped", 0))
        detail_cols[1].metric("Vendor URLs", result.get("vendor_urls", 0))
        detail_cols[2].metric("Government URLs", result.get("government_urls", 0))
        detail_cols[3].metric("Complaint URLs", result.get("complaint_urls", 0))
        skip_cols = st.columns(4)
        skip_cols[0].metric("Duplicates skipped", result.get("skipped_duplicates", 0))
        skip_cols[1].metric("Invalid sources skipped", result.get("skipped_missing_source_or_text", 0))
        skip_cols[2].metric("Skipped not pain evidence", result.get("skipped_not_complaint_or_pain_evidence", 0))
        skip_cols[3].metric("Skipped market/generic/marketing", result.get("skipped_market_size_generic_or_marketing", 0))
        run_cols = st.columns(2)
        run_cols[0].metric("Providers used", ", ".join(str(provider) for provider in result.get("providers_used", [])) or "None")
        run_cols[1].metric("Run ID", result.get("run_id") or result.get("active_run_id") or "No run")
        learning = result.get("discovery_learning_update")
        if isinstance(learning, dict):
            st.subheader("Discovery Learning Update")
            accepted_domains = learning.get("accepted_domains") or []
            vendor_domains = learning.get("rejected_vendor_domains") or []
            st.write("Accepted evidence came from: " + (", ".join(str(domain) for domain in accepted_domains) if accepted_domains else "No accepted domains this run."))
            st.write("Rejected vendor-heavy domains: " + (", ".join(str(domain) for domain in vendor_domains) if vendor_domains else "None recorded."))
            st.write(f"Best performing query: {learning.get('best_query') or 'Not enough accepted evidence yet.'}")
            provider_rows = learning.get("provider_performance") or []
            if provider_rows:
                for provider_row in provider_rows[:6]:
                    provider = provider_row.get("provider", "Provider")
                    returned = provider_row.get("urls_returned", 0)
                    accepted = provider_row.get("accepted_signals", 0)
                    st.caption(f"{provider} returned {returned} candidates, {accepted} accepted.")
        stored_signals = result.get("signals") or []
        if stored_signals:
            st.subheader("New Production Signals")
            for signal in stored_signals:
                if isinstance(signal, dict):
                    render_signal_trace_card(signal)
        with st.expander("Technical Details"):
            st.json(result)

    def render_discovery_learning_dashboard() -> None:
        dashboard = discovery_learning_dashboard(DB_PATH, DEFAULT_STUDY_ID)
        st.subheader("Discovery Learning")
        metric_cols = st.columns(4)
        metric_cols[0].metric("Runs Analysed", dashboard["runs_analysed"])
        metric_cols[1].metric("Acceptance Rate", f"{dashboard['acceptance_rate']}%")
        metric_cols[2].metric("Average Trust", dashboard["average_trust_score"])
        best_provider = dashboard.get("best_provider") or {}
        metric_cols[3].metric("Best Provider", best_provider.get("memory_key") or "None yet")

        card_cols = st.columns(2)
        with card_cols[0]:
            with st.container(border=True):
                st.markdown("**Best domains**")
                rows = dashboard.get("best_domains") or []
                if rows:
                    for row in rows:
                        st.write(f"{row.get('memory_key')} - {row.get('accepted_count')} accepted")
                else:
                    st.caption("No trusted domains learned yet.")
            with st.container(border=True):
                st.markdown("**Best queries**")
                rows = dashboard.get("best_queries") or []
                if rows:
                    for row in rows:
                        st.write(f"{row.get('memory_key')} - score {row.get('score')}")
                else:
                    st.caption("No high-yield queries learned yet.")
        with card_cols[1]:
            with st.container(border=True):
                st.markdown("**Worst domains**")
                rows = dashboard.get("worst_domains") or []
                if rows:
                    for row in rows:
                        label = "Vendor" if row.get("memory_type") == "vendor_domain" else "Rejected"
                        st.write(f"{row.get('memory_key')} - {label}")
                else:
                    st.caption("No rejected/vendor domains learned yet.")
            with st.container(border=True):
                st.markdown("**Worst queries**")
                rows = dashboard.get("worst_queries") or []
                if rows:
                    for row in rows:
                        st.write(f"{row.get('memory_key')} - {row.get('rejected_count')} rejected")
                else:
                    st.caption("No low-yield queries learned yet.")
        with st.expander("Technical Details"):
            st.json(dashboard)

    def as_list_text(raw: object) -> str:
        if not raw:
            return ""
        try:
            parsed = json.loads(str(raw))
        except json.JSONDecodeError:
            return str(raw)
        if isinstance(parsed, list):
            return ", ".join(str(item) for item in parsed)
        return str(parsed)

    def list_count(raw: object) -> int:
        if not raw:
            return 0
        try:
            parsed = json.loads(str(raw))
        except json.JSONDecodeError:
            return 0
        return len(parsed) if isinstance(parsed, list) else 0

    def compact_signals(records: list[dict[str, object]]) -> list[dict[str, object]]:
        return [
            {
                "Summary": row.get("summary"),
                "Country": row.get("country"),
                "Stakeholder": row.get("stakeholder_type"),
                "Source": source_label(row),
                "Data origin": row.get("data_origin"),
                "Verification": row.get("verification_status"),
                "Evidence strength": row.get("evidence_strength"),
                "Status": row.get("status"),
            }
            for row in records
        ]

    def compact_findings(records: list[dict[str, object]]) -> list[dict[str, object]]:
        return [
            {
                "Theme": row.get("theme"),
                "Problem statement": row.get("problem_statement"),
                "Signal count": row.get("signal_count"),
                "Independent sources": row.get("independent_source_count"),
                "Countries": as_list_text(row.get("countries")),
                "Confidence score": row.get("confidence_score"),
                "Status": row.get("status"),
            }
            for row in records
        ]

    def compact_audits(records: list[dict[str, object]]) -> list[dict[str, object]]:
        return [
            {
                "Decision": row.get("decision"),
                "OCI": row.get("opportunity_confidence_index"),
                "Evidence score": row.get("evidence_score"),
                "Frequency score": row.get("frequency_score"),
                "Market size score": row.get("market_size_score"),
                "Pain severity score": row.get("pain_severity_score"),
                "Traceability score": row.get("traceability_score"),
                "Missing evidence": row.get("missing_evidence"),
                "Recommendation": row.get("recommendation"),
            }
            for row in records
        ]

    def compact_opportunities(records: list[dict[str, object]]) -> list[dict[str, object]]:
        return [
            {
                "Problem": row.get("problem"),
                "OCI": row.get("opportunity_confidence_index"),
                "Commercial potential": row.get("commercial_potential"),
                "Engineering complexity": row.get("estimated_build_complexity"),
                "Recommended component": row.get("recommended_component"),
                "Engineering status": row.get("engineering_status"),
                "Status": row.get("status"),
            }
            for row in records
        ]

    def badge_text(value: object) -> str:
        return str(value or "Not started")

    def badge_class(value: object) -> str:
        text = str(value or "").lower()
        if "ready" in text or "complete" in text or "verified" in text or "active" in text:
            return "green"
        if "demo" in text:
            return "orange"
        if "pending" in text or "progress" in text or "waiting" in text:
            return "yellow"
        if "missing" in text or "blocked" in text or "failed" in text:
            return "red"
        if "archived" in text or "not started" in text:
            return "grey"
        return "blue"

    def badge_html(value: object) -> str:
        return f"Status: {badge_text(value)}"

    def metric_card(icon: str, title: str, value: object, description: str, status: object = "Active") -> str:
        return f"**{title}**\n\n{value}\n\n{description}\n\n{badge_html(status)}"

    def section_header(title: str, subtitle: str = "", status: object | None = None) -> None:
        with st.container(border=True):
            if status:
                st.caption(badge_html(status))
            st.subheader(title)
            if subtitle:
                st.caption(subtitle)

    def shell_status_card(label: str, value: object, note: str, tone: str = "blue") -> str:
        return f"**{label}**\n\n{value}\n\n{note}"

    def brief_item(label: str, value: object) -> str:
        return f"**{label}:** {value or 'Not specified'}"

    def workflow_stage_card(stage: str) -> str:
        state = workflow_stage_status(stage)
        return f"**{stage}**\n\n{badge_html(state)}"

    def render_status_card(label: str, value: object, note: str, status: object = "Active") -> None:
        with st.container(border=True):
            st.caption(badge_html(status))
            st.metric(label, value)
            st.caption(note)

    def render_business_card(title: object, status: object, summary: object, kpis: list[tuple[str, object]] | None = None) -> None:
        with st.container(border=True):
            st.caption(badge_html(status))
            st.markdown(f"**{title or 'Untitled'}**")
            st.write(str(summary or "No summary available."))
            if kpis:
                cols = st.columns(min(4, len(kpis)))
                for index, (label, value) in enumerate(kpis):
                    cols[index % len(cols)].metric(str(label), value)

    def empty_state(tab_name: str, production_text: str, demo_text: str | None = None) -> None:
        if is_production_run:
            message = production_text
        elif is_demo_run:
            message = demo_text or production_text.replace("production", "demo")
        else:
            message = f"No active run is available for {tab_name}."
        with st.container(border=True):
            st.caption("Empty state")
            st.info(message)

    def production_timeline_status(stage: str) -> str:
        return production_pipeline_statuses(progress).get(stage, "Locked")

    def render_workflow_timeline(stages: list[str]) -> None:
        cols = st.columns(5)
        for index, stage in enumerate(stages):
            with cols[index % 5]:
                with st.container(border=True):
                    state = production_timeline_status(stage)
                    st.caption(badge_html(state))
                    st.write(stage)

    def pipeline_progress_percent(stages: list[str]) -> int:
        if not stages:
            return 0
        completed = sum(1 for stage in stages if production_timeline_status(stage) == "Completed")
        return round((completed / len(stages)) * 100)

    def demo_oci(record: dict[str, object]) -> int:
        if not record:
            return 0
        raw = record.get("opportunity_confidence_index") or record.get("confidence_score") or record.get("research_confidence") or 0
        try:
            score = int(raw)
        except (TypeError, ValueError):
            score = 0
        if score:
            return score
        return min(100, int(record.get("evidence_strength") or 0) + 20)

    def displayed_oci(record: dict[str, object]) -> int:
        return demo_oci(record) if is_demo_run else int(record.get("opportunity_confidence_index") or 0)

    def recommended_action_text() -> str:
        if not active_run:
            return "Create a Golden Study run"
        if not progress["signals_collected"]:
            return "Add source-backed evidence"
        if not progress["findings_created"]:
            return "Generate findings"
        if not progress["audits_completed"]:
            return "Run audit batch"
        if not progress["opportunities_approved"]:
            return "Review opportunities"
        if not progress["engineering_ready"]:
            return "Create engineering specification"
        return "Prepare executive brief"

    def workflow_stage_status(stage: str) -> str:
        values = {
            "Signals": progress["signals_collected"],
            "Findings": progress["findings_created"],
            "Audits": progress["audits_completed"],
            "Opportunities": progress["opportunities_approved"],
            "Engineering Specs": len([row for row in opportunities if row.get("engineering_status") in {"Engineering Specification Required", "Demo Opportunity"}]),
            "Engineering Ready": len(progress["engineering_ready"]),
        }
        order = ["Signals", "Findings", "Audits", "Opportunities", "Engineering Specs", "Engineering Ready"]
        current = values.get(stage, 0)
        if current:
            return "Complete"
        index = order.index(stage)
        if index > 0 and values.get(order[index - 1], 0):
            return "In progress"
        return "Not started"

    def show_record_card(title: str, status: object, metric_label: str, metric_value: object, summary: object) -> None:
        cols = st.columns([3, 1, 1])
        cols[0].markdown(f"**{title or 'Untitled'}**")
        cols[1].caption(badge_text(status))
        cols[2].metric(metric_label, metric_value)
        if summary:
            st.write(str(summary))

    def set_golden_flash(level: str, message: str, details: object | None = None) -> None:
        st.session_state["golden_flash"] = {"level": level, "message": message, "details": details}

    def show_golden_flash() -> None:
        flash = st.session_state.pop("golden_flash", None)
        if not flash:
            return
        level = flash.get("level")
        message = str(flash.get("message") or "")
        if level == "success":
            st.success(message)
        elif level == "error":
            st.error(message)
        else:
            st.warning(message)
        if flash.get("details") is not None:
            with st.expander("Technical Details"):
                st.json(flash["details"])

    signals = list_signals(DB_PATH, DEFAULT_STUDY_ID, active_run_id, include_demo=include_demo_view) if active_run_id else []
    findings = list_findings(DB_PATH, DEFAULT_STUDY_ID, active_run_id, include_demo=include_demo_view) if active_run_id else []
    audits = list_finding_audits(DB_PATH, DEFAULT_STUDY_ID, active_run_id, include_demo=include_demo_view) if active_run_id else []
    opportunities = list_opportunities(DB_PATH, DEFAULT_STUDY_ID, active_run_id, include_demo=include_demo_view) if active_run_id else []

    show_golden_flash()

    mode_label = "Demo Mode" if is_demo_run else "Production Mode" if is_production_run else "No Active Run"
    production_empty = is_production_run and not any(
        [
            progress["signals_collected"],
            progress["findings_created"],
            progress["audits_completed"],
            progress["opportunities_approved"],
            len(progress["engineering_ready"]),
        ]
    )

    title_cols = st.columns([4, 1])
    with title_cols[0]:
        st.header("Golden Study 001")
        st.caption("Operational research and audit workflow for Global Property Management")
    with title_cols[1]:
        st.caption(badge_html(mode_label))
        st.caption(f"Run status: {str(run_status or 'Waiting').title()}")

    workflow_tabs = st.tabs([
        "Mission Control",
        "Collect Market Evidence",
        "Signals",
        "Findings",
        "Audits",
        "Opportunities",
        "Engineering Specs",
        "Evidence Chain",
        "Executive Brief",
        "Integrity Check",
        "Archive / Demo History",
        "Raw Database View",
        "Discovery Learning",
    ])

    with workflow_tabs[0]:
        top_opportunity = opportunities[0] if opportunities else {}
        workflow_stages = [
            "Evidence Collection",
            "Signal Detection",
            "Finding Generation",
            "Audit",
            "Opportunity",
            "Engineering Spec",
            "Prototype",
            "Internal Validation",
            "External Validation",
            "Commercial Ready",
        ]
        progress_percent = pipeline_progress_percent(workflow_stages)
        section_header("Mission Control", "GS-001 command centre for market evidence, audit, and opportunity readiness.", mode_label)
        control_cols = st.columns(3)
        with control_cols[0]:
            render_status_card("Current Study", "GS-001", "Global Property Management", "Active")
        with control_cols[1]:
            render_status_card("Current Run", str(run_status or "Waiting").title(), "Active run only; IDs are in Technical Details.", mode_label)
        with control_cols[2]:
            render_status_card("Mode", mode_label.replace(" Mode", ""), "Demo outputs never count as production evidence.", mode_label)

        st.subheader("Pipeline Progress")
        if production_empty:
            st.info("Production Mode Active. No production research has been started.")
            action_cols = st.columns(2)
            if action_cols[0].button("+ Add First Verified Evidence", key="gs001_overview_add_first_verified", type="primary"):
                st.session_state["gs001_focus_add_evidence"] = True
                st.info("Open Collect Market Evidence to enter the first verified source.")
            if action_cols[1].button("View Demo History", key="gs001_overview_view_demo_history"):
                st.info("Open Archive / Demo History to view preserved demo records.")
            st.caption("0% - Awaiting first verified evidence")
            render_workflow_timeline(workflow_stages)
            empty_cols = st.columns(3)
            with empty_cols[0]:
                render_status_card("Signals", "No evidence collected", "Add verified evidence to begin.", "Active")
            with empty_cols[1]:
                render_status_card("Findings", "Waiting for evidence", "Findings unlock after repeated signals.", "Locked")
            with empty_cols[2]:
                render_status_card("Audits", "Locked until findings exist", "Audit requires auditable findings.", "Locked")
            empty_cols = st.columns(3)
            with empty_cols[0]:
                render_status_card("Opportunities", "Locked until audit approval", "Production opportunities require approved audits.", "Locked")
            with empty_cols[1]:
                render_status_card("OCI", "Unavailable", "OCI appears after production opportunities exist.", "Locked")
            with empty_cols[2]:
                render_status_card("Engineering", "No approved opportunities", "Specs unlock after approval.", "Locked")
        else:
            st.caption(f"{progress_percent}% - {recommended_action_text()}")
            render_workflow_timeline(workflow_stages)

        st.subheader("Evidence Health")
        quality_dashboard = evidence_quality_dashboard(signals)
        health_cols = st.columns(3)
        with health_cols[0]:
            render_status_card("Sources", progress["source_coverage"] or "None", "Independent sources in the active run.", workflow_stage_status("Signals"))
        with health_cols[1]:
            render_status_card("Countries", len(progress["countries_covered"]) or "None", ", ".join(progress["countries_covered"]) or "No country coverage yet.", workflow_stage_status("Signals"))
        with health_cols[2]:
            render_status_card("Pending Verification", progress["verification_pending_count"], "Evidence still awaiting review.", "Waiting" if progress["verification_pending_count"] else "Completed")
        quality_cols = st.columns(4)
        with quality_cols[0]:
            render_status_card("Accepted Production Signals", quality_dashboard["accepted_production_signals"], "Eligible complaint/pain evidence.", quality_dashboard["production_readiness"])
        with quality_cols[1]:
            render_status_card("Average Trust Score", quality_dashboard["average_trust_score"], "Eligible evidence only.", "Complete" if float(quality_dashboard["average_trust_score"] or 0) >= 80 else "Waiting")
        with quality_cols[2]:
            render_status_card("Independent Domains", quality_dashboard["independent_domains"], "Eligible source domains.", "Complete" if int(quality_dashboard["independent_domains"] or 0) >= 2 else "Waiting")
        with quality_cols[3]:
            render_status_card("Production Readiness", quality_dashboard["production_readiness"], "Analyst gate before findings/opportunities.", quality_dashboard["production_readiness"])
        mix_cols = st.columns(4)
        with mix_cols[0]:
            render_status_card("Market Context", quality_dashboard["market_context"], "Background only.", "Waiting" if quality_dashboard["market_context"] else "Complete")
        with mix_cols[1]:
            render_status_card("Vendor Content", quality_dashboard["vendor_content"], "Never counted.", "Waiting" if quality_dashboard["vendor_content"] else "Complete")
        with mix_cols[2]:
            render_status_card("Community Signals", quality_dashboard["community_signals"], "Require verification.", "Waiting" if quality_dashboard["community_signals"] else "Complete")
        with mix_cols[3]:
            render_status_card("Rejected", quality_dashboard["rejected"], "Not eligible for production findings.", "Waiting" if quality_dashboard["rejected"] else "Complete")

        render_discovery_learning_dashboard()

        st.subheader("Current Top Opportunity")
        if top_opportunity:
            render_business_card(
                top_opportunity.get("recommended_component") or "Opportunity",
                top_opportunity.get("status"),
                top_opportunity.get("problem"),
                [
                    ("Demo OCI" if bool(top_opportunity.get("is_demo")) else "OCI", displayed_oci(top_opportunity)),
                    ("Commercial", top_opportunity.get("commercial_potential") or "Not set"),
                    ("Engineering", top_opportunity.get("engineering_status") or "Not started"),
                    ("Mode", "Demo" if bool(top_opportunity.get("is_demo")) else "Production"),
                ],
            )
        else:
            empty_state(
                "Current Top Opportunity",
                "No approved production opportunity exists yet. Complete audit approval to surface one.",
                "No demo opportunity exists yet. Run demo audit and approval to rehearse this stage.",
            )

        st.subheader("Recommended Next Action")
        if is_demo_run:
            st.info("Demo rehearsal mode active. Demo records prove the workflow but are excluded from production.")
            if progress["opportunities_approved"] == 0 and progress["audits_completed"]:
                st.write("Approve demo opportunities to continue rehearsal.")
            elif progress["audits_completed"] == 0 and progress["findings_created"]:
                st.write("Run demo audit batch to rehearse audit flow.")
            elif progress["findings_created"] == 0:
                st.write("Generate demo findings from sample signals.")
            else:
                st.write("Start a production run when you are ready to use real market evidence.")
            cleanup_cols = st.columns(2)
            with cleanup_cols[0]:
                archive_confirmed = st.checkbox(
                    "I understand this archives demo data and preserves it for history.",
                    key="gs001_archive_demo_confirmed",
                )
                if st.button(
                    "Clear / Archive All Demo Data",
                    disabled=not archive_confirmed,
                    key="gs001_archive_all_demo",
                ):
                    result = archive_all_demo_data(DB_PATH, DEFAULT_STUDY_ID)
                    count_text = ", ".join(
                        f"{table.replace('_', ' ')}: {count}"
                        for table, count in dict(result.get("counts") or {}).items()
                    )
                    set_golden_flash(
                        "success",
                        f"{result['records_archived']} demo records archived and preserved for history. {count_text}",
                        result,
                    )
                    st.rerun()
            with cleanup_cols[1]:
                production_confirmed = st.checkbox(
                    "I understand production mode requires real, source-backed evidence.",
                    key="gs001_overview_production_confirmed",
                )
                if st.button(
                    "Start Real / Production Run",
                    key="gs001_overview_start_production",
                    type="primary",
                    disabled=not production_confirmed,
                ):
                    try:
                        archive_result = archive_all_demo_data(DB_PATH, DEFAULT_STUDY_ID)
                        run_result = switch_study_run_mode(DB_PATH, DEFAULT_STUDY_ID, "production", production_confirmed)
                        set_golden_flash(
                            "success",
                            "Production run started. Production KPIs now use a clean active run. Demo records were archived by table before switching.",
                            {"archive": archive_result, "production_run": run_result},
                        )
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
        elif is_production_run:
            st.success("Production Mode Active. Add real, source-backed evidence to build production metrics.")
            if progress["signals_collected"] == 0:
                st.write("Add real source-backed evidence.")
            elif progress["findings_created"] == 0:
                st.write("Generate findings once repeated signals exist.")
            elif progress["audits_completed"] == 0:
                st.write("Run audit batch for auditable findings.")
            else:
                st.write("Approve evidence-backed opportunities and complete engineering specs.")
        else:
            st.write("Create a run before collecting Golden Study evidence.")

        validation = validate_golden_study_integrity(DB_PATH, DEFAULT_STUDY_ID)
        warnings = []
        if is_demo_run:
            warnings.append("Demo data active.")
        if progress["verification_pending_count"]:
            warnings.append("Evidence pending verification.")
        if progress["signals_collected"] < 2:
            warnings.append("Insufficient evidence for robust findings.")
        if is_production_run and progress["signals_collected"] == 0:
            warnings.append("Production run is empty.")
        if not validation["passed"]:
            warnings.append(f"{validation['failed_count']} integrity checks need attention.")
        if warnings:
            st.subheader("Warnings")
            for warning in warnings:
                st.warning(warning)

    with workflow_tabs[1]:
        section_header(
            "Collect Market Evidence",
            "Production collects verified market evidence. Demo mode loads rehearsal evidence.",
            "Production Mode Active" if is_production_run else "Demo Mode Active" if is_demo_run else "Waiting",
        )
        if is_production_run:
            with st.container(border=True):
                st.caption("Production provider pull")
                st.markdown("**Pull Real Market Evidence**")
                st.write("Run the configured research providers against the GS-001 query set. No manual form input is required.")
                scope_cols = st.columns(4)
                scope_cols[0].metric("Market", "United States")
                scope_cols[1].metric("Industry", "Residential Property Management")
                scope_cols[2].metric("Focus", "Maintenance Communication")
                scope_cols[3].metric("Max sources", 10)
                if st.button("Pull Real Market Evidence", key="gs001_pull_real_market_evidence", type="primary"):
                    with st.status("Starting research run", expanded=True) as status:
                        progress_bar = st.progress(0)
                        st.write("Checking providers")
                        progress_bar.progress(15)
                        st.write("Searching queries")
                        progress_bar.progress(35)
                        result = pull_real_market_evidence(DB_PATH, DEFAULT_STUDY_ID)
                        st.write("Normalising evidence")
                        progress_bar.progress(55)
                        st.write("Deduplicating")
                        progress_bar.progress(70)
                        st.write("Saving production signals")
                        progress_bar.progress(90)
                        progress_bar.progress(100)
                        status.update(label="Complete", state="complete", expanded=True)
                    st.session_state["gs001_last_research_run"] = result
                    if result["status"] == "blocked":
                        set_golden_flash("warning", str(result["message"]), result)
                    elif result["status"] == "empty":
                        set_golden_flash("warning", str(result["message"]), result)
                    else:
                        set_golden_flash("success", "Research Run Complete", result)
                    st.rerun()
            last_research_run = st.session_state.get("gs001_last_research_run")
            if isinstance(last_research_run, dict):
                with st.container(border=True):
                    render_research_run_result(last_research_run)
            st.subheader("Add Manual Verified Evidence")
            with st.form("golden_real_evidence_form"):
                source_cols = st.columns(3)
                signal_source = source_cols[0].text_input("Source URL", key="golden_real_source")
                manual_signal_source_name = source_cols[1].text_input("Source name", key="golden_real_source_name")
                signal_source_type = source_cols[2].selectbox("Source type", ["manual", "url", "pdf", "csv", "txt", "article", "provider"], key="golden_real_source_type")
                meta_cols = st.columns(4)
                signal_country = meta_cols[0].text_input("Country", value="Unknown", key="golden_real_country")
                signal_stakeholder = meta_cols[1].text_input("Stakeholder type", value="Unknown", key="golden_real_stakeholder")
                signal_product = meta_cols[2].text_input("Company / Product", key="golden_real_product")
                signal_source_date = meta_cols[3].date_input("Evidence date", key="golden_real_source_date")
                signal_origin = st.selectbox("Data origin", ["manual", "provider", "verified_import"], key="golden_real_origin")
                signal_text = st.text_area("Raw evidence text", key="golden_real_text")
                if st.form_submit_button("Collect Verified Evidence"):
                    try:
                        result = create_signal(
                            DB_PATH,
                            signal_text,
                            DEFAULT_STUDY_ID,
                            signal_source,
                            manual_signal_source_name,
                            signal_source_type,
                            signal_source_date.isoformat(),
                            signal_country,
                            signal_stakeholder,
                            signal_product,
                            signal_origin,
                        )
                        set_golden_flash("success", "Verified market evidence added to the active production run.", result)
                        st.rerun()
                    except ValueError as exc:
                        set_golden_flash("error", str(exc))
                        st.rerun()
        elif is_demo_run:
            st.info("Real market evidence can only be pulled in Production Mode.")
            st.warning("This loader creates demo/sample records only. Do not treat them as real or verified market evidence.")
            demo_sample_confirmed = st.checkbox("I understand this loads demo/sample data only.", key="gs001_demo_sample_confirmed")
            if st.button("Load DEMO Sample GS-001 Batch", disabled=not demo_sample_confirmed, key="gs001_load_demo_sample_batch"):
                sample = [
                    {"country": "Ireland", "stakeholder_type": "Property managers", "source_name": "Irish property forum", "data_origin": "demo", "raw_text": "Property managers in Ireland repeatedly complain that maintenance updates are slow and tenants chase responses multiple times."},
                    {"country": "United Kingdom", "stakeholder_type": "Tenants", "source_name": "UK tenant review", "data_origin": "demo", "raw_text": "Tenants in the United Kingdom complain that repair communication is poor, updates are delayed, and maintenance requests need repeated follow-up."},
                    {"country": "United States", "stakeholder_type": "Property owners", "source_name": "US owner review", "data_origin": "demo", "raw_text": "Property owners in the United States say maintenance coordination is manual, slow, and expensive across property management software."},
                ]
                result = run_research_batch(DB_PATH, sample, DEFAULT_STUDY_ID)
                set_golden_flash("success", f"{len(result['signals'])} demo signals created", result)
                st.rerun()
        else:
            st.info("Real market evidence can only be pulled in Production Mode.")
            st.info("No active run is available.")

    with workflow_tabs[2]:
        section_header("Signals", "Evidence cards for the current active run. Technical IDs stay inside each expander.", workflow_stage_status("Signals"))
        accepted_signals = []
        rejected_signals = []
        for signal in signals:
            view = signal_trace_card_view_model(signal)
            if view["production_eligible"] == "YES":
                accepted_signals.append(signal)
            else:
                rejected_signals.append(signal)

        st.subheader("Accepted Production Signals")
        if not accepted_signals:
            empty_state(
                "Signals",
                "No accepted production signals yet. Pull evidence or review rejected/context results.",
                "No demo signals yet. Load the demo sample batch to rehearse evidence collection.",
            )
        for signal in accepted_signals:
            render_signal_trace_card(signal)
            if st.button("Archive", key=f"archive_signal_{signal['id']}"):
                archive_record(DB_PATH, "study_signals", str(signal["id"]))
                st.rerun()

        st.subheader("Rejected / Context / Non-Eligible Evidence")
        if rejected_signals:
            st.info("Evidence was found, but did not meet production quality rules.")
            for signal in rejected_signals:
                render_rejected_signal_card(signal)
                if st.button("Archive", key=f"archive_rejected_signal_{signal['id']}"):
                    archive_record(DB_PATH, "study_signals", str(signal["id"]))
                    st.rerun()
        else:
            st.caption("No rejected or context evidence in the active run.")

        with st.expander("Technical Raw Data"):
            st.dataframe(signals, use_container_width=True)

    with workflow_tabs[3]:
        section_header("Findings", "Problems generated from repeated supporting signals in the active run.", workflow_stage_status("Findings"))
        if st.button("Generate Findings", key="gs001_generate_findings"):
            generated = generate_findings(DB_PATH, DEFAULT_STUDY_ID)
            level, message = findings_feedback(generated)
            set_golden_flash(level, message, generated)
            st.rerun()
        if not findings:
            empty_state(
                "Findings",
                "No findings yet. Findings are generated once repeated evidence exists.",
                "No demo findings yet. Generate findings after loading repeated demo evidence.",
            )
        for finding in findings:
            with st.container(border=True):
                render_business_card(
                    str(finding.get("theme") or "Market problem"),
                    finding.get("status"),
                    finding.get("problem_statement"),
                    [
                        ("Confidence", finding.get("confidence_score") or 0),
                        ("Signals", finding.get("signal_count") or 0),
                        ("Sources", finding.get("independent_source_count") or 0),
                        ("Countries", list_count(finding.get("countries"))),
                    ],
                )
                cols = st.columns(3)
                if cols[0].button("Audit Finding", key=f"audit_finding_{finding['id']}"):
                    try:
                        result = audit_finding(DB_PATH, str(finding["id"]))
                        set_golden_flash("success", "1 audit completed", result)
                        st.rerun()
                    except ValueError as exc:
                        message = str(exc)
                        set_golden_flash("warning", message)
                        st.rerun()
                if cols[1].button("View Evidence Chain", key=f"finding_chain_{finding['id']}"):
                    st.session_state["golden_chain_target_type"] = "Finding"
                    st.session_state["golden_chain_target_id"] = str(finding["id"])
                if cols[2].button("Archive", key=f"archive_finding_{finding['id']}"):
                    archive_record(DB_PATH, "study_findings", str(finding["id"]))
                    st.rerun()
                with st.expander("Technical Details"):
                    st.json(finding)

    with workflow_tabs[4]:
        section_header("Audits", "Audit decisions, evidence scoring, reasoning and opportunity approval controls.", workflow_stage_status("Audits"))
        audit_actions = st.columns(2)
        with audit_actions[0]:
            if st.button("Run Audit Batch", key="gs001_run_audit_batch"):
                try:
                    completed = run_audit_batch(DB_PATH, DEFAULT_STUDY_ID)
                    refreshed_findings = list_findings(DB_PATH, DEFAULT_STUDY_ID, active_run_id, include_demo=include_demo_view)
                    level, message = audit_batch_feedback(completed, refreshed_findings)
                    set_golden_flash(level, message, completed)
                    st.rerun()
                except ValueError as exc:
                    set_golden_flash("error", str(exc))
                    st.rerun()
        with audit_actions[1]:
            if st.button("Approve Opportunities", key="gs001_approve_opportunities"):
                try:
                    approved = approve_audited_opportunities(DB_PATH, DEFAULT_STUDY_ID)
                    level, message = approval_feedback(approved, demo_present=is_demo_run or progress["demo_records_count"] > 0)
                    set_golden_flash(level, message, approved)
                    st.rerun()
                except ValueError as exc:
                    set_golden_flash("error", str(exc))
                    st.rerun()
        if not audits:
            empty_state(
                "Audits",
                "No audits yet. Generate findings before running audit.",
                "No demo audits yet. Generate demo findings, then run the demo audit batch.",
            )
        for audit in audits:
            finding_label = next((str(finding.get("theme")) for finding in findings if finding.get("id") == audit.get("finding_id")), "Audited finding")
            with st.container(border=True):
                render_business_card(
                    finding_label,
                    audit.get("status") or audit.get("decision"),
                    audit.get("recommendation"),
                    [
                        ("Evidence", audit.get("evidence_score") or 0),
                        ("Pain", audit.get("pain_severity_score") or 0),
                        ("Traceability", audit.get("traceability_score") or 0),
                        ("Demo OCI" if bool(audit.get("is_demo")) else "OCI", demo_oci(audit) if bool(audit.get("is_demo")) else audit.get("opportunity_confidence_index") or 0),
                    ],
                )
                cols = st.columns(2)
                if cols[0].button("Approve Opportunity", key=f"approve_audit_{audit['id']}"):
                    try:
                        approved = approve_audited_opportunities(DB_PATH, DEFAULT_STUDY_ID)
                        level, message = approval_feedback(approved, demo_present=bool(audit.get("is_demo")) or is_demo_run)
                        set_golden_flash(level, message, approved)
                        st.rerun()
                    except ValueError as exc:
                        set_golden_flash("error", str(exc))
                        st.rerun()
                if cols[1].button("Archive", key=f"archive_audit_{audit['id']}"):
                    archive_record(DB_PATH, "finding_audits", str(audit["id"]))
                    st.rerun()
                with st.expander("Technical Details"):
                    st.json(audit)

    with workflow_tabs[5]:
        section_header("Opportunities", "Current-run opportunity cards with commercial and engineering readiness context.", workflow_stage_status("Opportunities"))
        if not opportunities:
            empty_state(
                "Opportunities",
                "No opportunities yet. Opportunities appear after audit approval.",
                "No demo opportunities yet. Approve demo audits to continue the rehearsal.",
            )
        for opportunity in opportunities:
            with st.container(border=True):
                render_business_card(
                    str(opportunity.get("recommended_component") or "Opportunity"),
                    opportunity.get("status"),
                    opportunity.get("problem"),
                    [
                        ("Demo OCI" if bool(opportunity.get("is_demo")) else "OCI", displayed_oci(opportunity)),
                        ("Commercial", opportunity.get("commercial_potential") or "Not set"),
                        ("Complexity", opportunity.get("estimated_build_complexity") or "Not set"),
                        ("Countries", list_count(opportunity.get("countries"))),
                    ],
                )
                st.caption(f"Engineering status: {opportunity.get('engineering_status') or 'Not started'}")
                cols = st.columns(3)
                if cols[0].button("View Evidence Chain", key=f"opp_chain_{opportunity['id']}"):
                    st.session_state["golden_chain_target_type"] = "Opportunity"
                    st.session_state["golden_chain_target_id"] = str(opportunity["id"])
                if cols[1].button("Create / Edit Engineering Spec", key=f"opp_spec_{opportunity['id']}"):
                    st.session_state["golden_spec_opportunity_id"] = str(opportunity["id"])
                if cols[2].button("Archive", key=f"archive_opp_{opportunity['id']}"):
                    archive_record(DB_PATH, "opportunity_records", str(opportunity["id"]))
                    st.rerun()
                with st.expander("Technical Details"):
                    st.json(opportunity)

    with workflow_tabs[6]:
        section_header("Engineering Specs", "Professional engineering briefs for opportunities that are ready for specification.", workflow_stage_status("Engineering Specs"))
        spec_opportunities = [row for row in opportunities if row.get("engineering_status") in {"Engineering Specification Required", "Engineering Ready", "Demo Opportunity", "Demo Engineering Ready"}]
        if not spec_opportunities:
            empty_state(
                "Engineering Specs",
                "No engineering specs yet. Approve an opportunity first.",
                "No demo engineering specs yet. Create a demo opportunity first.",
            )
        for row in spec_opportunities:
            demo_prefix = "Demo " if bool(row.get("is_demo")) else ""
            with st.container(border=True):
                st.caption(badge_html(row.get("engineering_status") or "Not started"))
                st.markdown(f"**{row.get('recommended_component') or 'Component'}**")
                brief_cols = st.columns(2)
                items = [
                    ("Purpose", row.get("problem_scope") or row.get("problem") or demo_prefix + "rehearsal scope based on the current problem statement."),
                    ("Primary Users", row.get("target_users") or demo_prefix + "property managers and operations teams"),
                    ("Secondary Users", demo_prefix + "tenants, owners, and support teams"),
                    ("Inputs", row.get("required_inputs") or demo_prefix + "maintenance requests, status updates, source evidence, user notes"),
                    ("Outputs", row.get("expected_outputs") or demo_prefix + "prioritised workflow, notifications, evidence summary, audit trail"),
                    ("Dependencies", demo_prefix + "PX-R001 research, PX-A001 audit, PX-L001 library"),
                    ("System Boundaries", row.get("system_boundaries") or demo_prefix + "no production automation until verified evidence exists"),
                    ("Architecture Recommendation", row.get("engineering_recommendation") or demo_prefix + "component-first workflow with traceable evidence chain"),
                    ("Implementation Complexity", row.get("estimated_build_complexity") or "Not specified"),
                    ("Engineering Status", row.get("engineering_status") or "Not started"),
                ]
                for index, (label, value) in enumerate(items):
                    with brief_cols[index % 2]:
                        st.markdown(brief_item(label, value))
                with st.expander("Technical Details"):
                    st.json(row)
        spec_options = {str(row.get("recommended_component") or row.get("problem") or row["id"]): row["id"] for row in spec_opportunities}
        selected_spec_label = st.selectbox("Opportunity", list(spec_options), key="golden_spec_select") if spec_options else None
        selected_spec = spec_options[selected_spec_label] if selected_spec_label else None
        if selected_spec:
            selected_row = next(row for row in spec_opportunities if row["id"] == selected_spec)
            st.caption(str(selected_row.get("recommended_component") or selected_row.get("problem") or selected_spec))
            with st.form("golden_engineering_spec_form"):
                spec = {
                    "recommended_component": st.text_input("Recommended component", value=str(selected_row.get("recommended_component") or "")),
                    "engineering_recommendation": st.text_area("Engineering recommendation", value=str(selected_row.get("engineering_recommendation") or "")),
                    "problem_scope": st.text_area("Problem scope", value=str(selected_row.get("problem_scope") or "")),
                    "target_users": st.text_area("Target users", value=str(selected_row.get("target_users") or "")),
                    "required_inputs": st.text_area("Required inputs", value=str(selected_row.get("required_inputs") or "")),
                    "expected_outputs": st.text_area("Expected outputs", value=str(selected_row.get("expected_outputs") or "")),
                    "system_boundaries": st.text_area("System boundaries", value=str(selected_row.get("system_boundaries") or "")),
                }
                if st.form_submit_button("Mark Engineering Ready"):
                    result = mark_engineering_ready(DB_PATH, str(selected_spec), spec)
                    if result.get("status") == "blocked":
                        set_golden_flash("error", "Engineering Ready blocked. Complete missing fields or traceability.", result)
                    else:
                        set_golden_flash("success", "Opportunity marked Engineering Ready.", result)
                    st.rerun()

    with workflow_tabs[7]:
        section_header("Evidence Chain", "Trace the business chain from evidence to finding, audit and opportunity.", "Traceability")
        include_history = st.toggle("Include archived/demo history", value=False, key="golden_chain_include_history")
        target_type = st.radio("Evidence target", ["Finding", "Opportunity"], horizontal=True, key="golden_chain_type")
        if target_type == "Finding":
            chain_findings = fetch_all(DB_PATH, "study_findings") if include_history else findings
            finding_options = {str(row.get("theme") or row.get("problem_statement") or row["id"]): row["id"] for row in chain_findings}
            selected_label = st.selectbox("Finding", list(finding_options), key="golden_chain_finding") if finding_options else None
            selected = finding_options[selected_label] if selected_label else None
            if not selected:
                empty_state(
                    "Evidence Chain",
                    "No finding evidence chain yet. Generate findings from verified evidence first.",
                    "No demo finding evidence chain yet. Generate demo findings first.",
                )
            if selected:
                try:
                    chain = finding_evidence(DB_PATH, str(selected), include_archived=include_history)
                    render_business_card(
                        chain["finding"].get("theme") or "Finding",
                        chain["finding"].get("status"),
                        chain["finding"].get("problem_statement"),
                        [
                            ("Signals", len(chain["signals"])),
                            ("Sources", len(chain.get("sources", []))),
                            ("Mode", "Demo" if bool(chain["finding"].get("is_demo")) else "Production"),
                            ("Confidence", chain["finding"].get("confidence_score") or 0),
                        ],
                    )
                    st.subheader("Supporting Signals")
                    for signal in chain["signals"]:
                        render_business_card(
                            f"{signal.get('country') or 'Unknown'} - {signal.get('stakeholder_type') or 'Unknown'}",
                            signal.get("verification_status"),
                            signal.get("summary") or signal.get("raw_text"),
                            [("Source", source_label(signal)), ("Strength", signal.get("evidence_strength") or 0)],
                        )
                    with st.expander("Technical Details"):
                        st.json(chain)
                except ValueError as exc:
                    st.error(str(exc))
        else:
            chain_opportunities = fetch_all(DB_PATH, "opportunity_records") if include_history else opportunities
            opportunity_options = {str(row.get("recommended_component") or row.get("problem") or row["id"]): row["id"] for row in chain_opportunities}
            selected_label = st.selectbox("Opportunity", list(opportunity_options), key="golden_chain_opportunity") if opportunity_options else None
            selected = opportunity_options[selected_label] if selected_label else None
            if not selected:
                empty_state(
                    "Evidence Chain",
                    "No opportunity evidence chain yet. Approve an audited production opportunity first.",
                    "No demo opportunity evidence chain yet. Approve a demo audit first.",
                )
            if selected:
                try:
                    chain = traceability_chain(DB_PATH, str(selected), include_archived=include_history)
                    render_business_card(
                        chain["opportunity"].get("recommended_component") or "Opportunity",
                        chain["opportunity"].get("status"),
                        chain["opportunity"].get("problem"),
                        [
                            ("Audit", chain["audit"].get("decision")),
                            ("Finding", chain["finding"].get("theme")),
                            ("Signals", len(chain["signals"])),
                            ("Sources", len(chain["sources"])),
                        ],
                    )
                    st.subheader("Supporting Signals")
                    for signal in chain["signals"]:
                        render_business_card(
                            f"{signal.get('country') or 'Unknown'} - {signal.get('stakeholder_type') or 'Unknown'}",
                            signal.get("verification_status"),
                            signal.get("summary") or signal.get("raw_text"),
                            [("Source", source_label(signal)), ("Strength", signal.get("evidence_strength") or 0)],
                        )
                    with st.expander("Technical Details"):
                        st.json(chain)
                except ValueError as exc:
                    st.error(str(exc))

    with workflow_tabs[8]:
        section_header("Executive Brief", "Founder-facing summary of the current run, risks, opportunities and next actions.", "Brief")
        if st.button("Generate Executive Brief", key="gs001_executive_brief"):
            brief = generate_executive_brief(DB_PATH, DEFAULT_STUDY_ID)
            render_business_card(brief.get("title"), brief.get("brief_type"), brief.get("body"))
            with st.expander("Technical Details"):
                st.json(brief)
        briefs = list_study_briefs(DB_PATH, DEFAULT_STUDY_ID, active_run_id, include_demo=include_demo_view) if active_run_id else []
        if briefs:
            latest = briefs[0]
            render_business_card(latest.get("title"), latest.get("brief_type"), latest.get("body"))
            with st.expander("Technical Details"):
                st.json(latest)
        else:
            empty_state(
                "Executive Brief",
                "No executive brief for this run yet. Generate one after evidence, findings, and audits exist.",
                "No demo executive brief yet. Generate one after the demo rehearsal creates outputs.",
            )

    with workflow_tabs[9]:
        section_header("Integrity Check", "Operational safety checks shown as cards. Full technical rows are hidden below.", "Protected")
        validation = validate_golden_study_integrity(DB_PATH, DEFAULT_STUDY_ID)
        if validation["passed"]:
            st.success("Passed")
        else:
            st.error(f"Failed: {validation['failed_count']} checks need attention.")
        checks = sorted(validation["checks"], key=lambda row: bool(row.get("passed")))
        integrity_groups = {
            "Traceability": ["run", "trace", "source", "links"],
            "Demo Isolation": ["demo"],
            "Production Safety": ["production", "approved"],
            "Engineering Readiness": ["Engineering Ready", "engineering"],
            "Evidence Completeness": ["signal", "evidence", "OCI"],
        }
        card_cols = st.columns(2)
        for index, (group_name, keywords) in enumerate(integrity_groups.items()):
            relevant = [
                row for row in checks
                if any(keyword.lower() in str(row.get("check", "")).lower() for keyword in keywords)
            ]
            failed = [row for row in relevant if not row.get("passed")]
            passed = not failed
            fix = failed[0].get("recommended_fix") if failed else "No action required."
            with card_cols[index % 2]:
                render_business_card(
                    group_name,
                    "Passed" if passed else "Failed",
                    "Checks passed." if passed else "Attention required.",
                    [("Checks", len(relevant)), ("Failed", len(failed)), ("Recommended fix", fix)],
                )
        with st.expander("Technical Details"):
            st.json(
                [
                    {
                        "Status": "Passed" if row.get("passed") else "Failed",
                        "Check": row.get("check"),
                        "Recommended fix": row.get("recommended_fix"),
                        "Related record": row.get("record_id", ""),
                        "Severity": "High" if not row.get("passed") else "OK",
                    }
                    for row in checks
                ]
            )

    with workflow_tabs[10]:
        section_header("Archive / Demo History", "Archived demo records remain visible for traceability but excluded from production metrics.", "History")
        st.warning("These records are preserved for traceability but excluded from production metrics.")
        if is_production_run:
            with st.container(border=True):
                st.subheader("Production Run Reset")
                st.write("Archive the current production run and start a clean empty production run after evidence-quality fixes.")
                reset_confirmed = st.checkbox(
                    "I understand this will archive the current production run and start a new empty production run.",
                    key="gs001_archive_current_production_confirmed",
                )
                if st.button(
                    "Archive Current Production Run & Start Fresh",
                    key="gs001_archive_current_production_run",
                    type="primary",
                    disabled=not reset_confirmed,
                ):
                    try:
                        result = archive_current_production_run_and_start_fresh(DB_PATH, DEFAULT_STUDY_ID)
                        set_golden_flash("success", "Current production run archived. New clean production run started.", result)
                        st.session_state.pop("gs001_last_research_run", None)
                        st.rerun()
                    except ValueError as exc:
                        set_golden_flash("error", str(exc))
                        st.rerun()
        else:
            st.info("Production archive-and-reset is only available while a production run is active.")
        archived_runs = [row for row in list_study_runs(DB_PATH, DEFAULT_STUDY_ID) if row.get("status") in {"closed", "archived"}]
        if not archived_runs:
            empty_state(
                "Archive / Demo History",
                "No archived history yet.",
                "No archived demo history yet. Archive demo data when you are ready to preserve rehearsal records.",
            )
        for run in archived_runs:
            render_business_card(
                f"Archived {run.get('study_mode')} run",
                run.get("status"),
                run.get("notes") or "Run preserved for history.",
                [("Mode", run.get("study_mode")), ("Origin", run.get("data_origin")), ("Verification", run.get("verification_status"))],
            )
            with st.expander("Technical Details"):
                st.json(run)
        for table_name in ["study_signals", "study_findings", "finding_audits", "opportunity_records", "study_briefs"]:
            rows = [row for row in fetch_all(DB_PATH, table_name) if row.get("study_id") == DEFAULT_STUDY_ID and row.get("is_demo") and row.get("status") == "archived"]
            st.subheader(table_name.replace("_", " ").title())
            render_business_card(
                table_name.replace("_", " ").title(),
                "Archived",
                f"{len(rows)} archived demo records preserved.",
                [("Records", len(rows))],
            )
            with st.expander("Technical Details"):
                st.json(rows)
        with st.expander("Technical/Admin"):
            st.warning("Danger zone: this deletes archived demo data only. Production records cannot be deleted here.")
            delete_confirmed = st.checkbox(
                "I understand this permanently deletes archived demo data only.",
                key="gs001_delete_archived_demo_confirmed",
            )
            if st.button(
                "Delete Archived Demo Data",
                key="gs001_delete_archived_demo_data",
                disabled=not delete_confirmed,
            ):
                result = delete_archived_demo_data(DB_PATH, DEFAULT_STUDY_ID)
                set_golden_flash("success", f"Archived demo data deleted: {result['records_deleted']} records.", result)
                st.rerun()

    with workflow_tabs[11]:
        section_header("Raw Database View - technical audit only", "Full ID-heavy tables are intentionally kept here for inspection.", "Technical")
        for table_name in ["studies", "study_runs", "study_signals", "study_findings", "finding_audits", "opportunity_records", "study_briefs", "discovery_runs", "discovery_memory"]:
            st.subheader(table_name)
            st.dataframe(fetch_all(DB_PATH, table_name), use_container_width=True)

    with workflow_tabs[12]:
        section_header("Discovery Learning", "GS-001 memory for evidence queries, source domains, and provider performance.", "Learning")
        render_discovery_learning_dashboard()
