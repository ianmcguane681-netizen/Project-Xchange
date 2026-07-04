from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


UTC = timezone.utc
DEFAULT_DB_PATH = Path("data/project_exchange.db")


SCHEMA = """
CREATE TABLE IF NOT EXISTS prompts (
    id TEXT PRIMARY KEY,
    worker_id TEXT NOT NULL,
    prompt_type TEXT NOT NULL,
    version TEXT NOT NULL,
    status TEXT NOT NULL,
    prompt_text TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prompt_tests (
    id TEXT PRIMARY KEY,
    prompt_id TEXT NOT NULL,
    test_input TEXT NOT NULL,
    expected_output TEXT,
    actual_output TEXT,
    result TEXT,
    tested_at TEXT,
    FOREIGN KEY(prompt_id) REFERENCES prompts(id)
);

CREATE TABLE IF NOT EXISTS research_records (
    id TEXT PRIMARY KEY,
    market TEXT,
    company TEXT,
    source_url TEXT,
    source_type TEXT,
    source_text TEXT,
    complaint_summary TEXT,
    workflow_cluster TEXT,
    evidence_score INTEGER,
    pipeline_status TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS audit_records (
    id TEXT PRIMARY KEY,
    research_id TEXT,
    decision TEXT NOT NULL,
    confidence_score INTEGER,
    duplicate_flag INTEGER,
    source_verified INTEGER,
    duplicate_risk TEXT,
    evidence_checklist TEXT,
    reasoning_summary TEXT,
    audit_notes TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS library_records (
    id TEXT PRIMARY KEY,
    source_audit_id TEXT,
    title TEXT,
    category TEXT,
    tags TEXT,
    summary TEXT,
    canonical_status TEXT,
    version TEXT,
    audit_history TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS workers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    function TEXT,
    stage TEXT,
    status TEXT,
    version TEXT,
    owner TEXT,
    purpose TEXT,
    health TEXT,
    dependencies TEXT,
    components_used TEXT,
    prompt_version TEXT,
    internal_value_score INTEGER,
    external_value_score INTEGER,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS components (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    purpose TEXT,
    version TEXT,
    tests TEXT,
    dependencies TEXT,
    stage TEXT,
    status TEXT,
    reused_by TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS changelog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS worker_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    worker_id TEXT NOT NULL,
    status TEXT NOT NULL,
    input_ref TEXT,
    output_ref TEXT,
    decision TEXT,
    duration_ms INTEGER,
    error TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    message TEXT NOT NULL,
    entity_id TEXT,
    severity TEXT NOT NULL,
    read_flag INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prompt_versions (
    id TEXT PRIMARY KEY,
    prompt_id TEXT NOT NULL,
    version TEXT NOT NULL,
    prompt_text TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(prompt_id) REFERENCES prompts(id)
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    worker_id TEXT,
    action TEXT NOT NULL,
    result TEXT,
    entity_id TEXT,
    duration_ms INTEGER,
    success INTEGER NOT NULL,
    error TEXT,
    payload TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS milestones (
    id TEXT PRIMARY KEY,
    sprint TEXT NOT NULL,
    version TEXT,
    title TEXT NOT NULL,
    description TEXT,
    date TEXT NOT NULL,
    completion_date TEXT,
    completed_by TEXT,
    files_changed TEXT,
    workers_added TEXT,
    components_added TEXT,
    notes TEXT,
    result TEXT
);

CREATE TABLE IF NOT EXISTS engineering_journal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    entry_type TEXT NOT NULL,
    body TEXT NOT NULL,
    related_entity TEXT,
    created_by TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    job_type TEXT NOT NULL,
    priority INTEGER NOT NULL,
    status TEXT NOT NULL,
    assigned_worker TEXT,
    payload TEXT,
    result TEXT,
    dependencies TEXT,
    history TEXT,
    parent_job_id TEXT,
    created_by TEXT,
    retries INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 2,
    failure_reason TEXT,
    recovery_suggestion TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    duration_ms INTEGER
);

CREATE TABLE IF NOT EXISTS system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    worker_id TEXT,
    job_id TEXT,
    severity TEXT NOT NULL,
    duration_ms INTEGER,
    details TEXT,
    status TEXT
);

CREATE TABLE IF NOT EXISTS failure_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    worker_id TEXT,
    error TEXT NOT NULL,
    stack_trace TEXT,
    recovery_suggestion TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS provider_runs (
    id TEXT PRIMARY KEY,
    provider_name TEXT NOT NULL,
    query TEXT NOT NULL,
    status TEXT NOT NULL,
    result_count INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS research_packages (
    id TEXT PRIMARY KEY,
    research_id TEXT,
    company TEXT,
    industry TEXT,
    website TEXT,
    keyword TEXT,
    market TEXT,
    country TEXT,
    providers TEXT,
    findings TEXT,
    complaints TEXT,
    opportunities TEXT,
    competitors TEXT,
    pricing TEXT,
    trends TEXT,
    evidence_score INTEGER,
    complaint_summary TEXT,
    opportunity_summary TEXT,
    trend_summary TEXT,
    competitor_summary TEXT,
    recommended_actions TEXT,
    confidence_score INTEGER,
    status TEXT,
    research_history TEXT,
    research_schedule TEXT,
    research_performance TEXT,
    sources TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    category TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS worker_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_worker TEXT NOT NULL,
    receiver_worker TEXT NOT NULL,
    job_id TEXT,
    message_type TEXT NOT NULL,
    body TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 3,
    payload TEXT,
    status TEXT NOT NULL DEFAULT 'sent',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge_edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    relationship TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    metadata TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prompt_benchmarks (
    id TEXT PRIMARY KEY,
    prompt_id TEXT NOT NULL,
    variant_label TEXT,
    test_input TEXT NOT NULL,
    expected_output TEXT,
    actual_output TEXT,
    result TEXT,
    score INTEGER,
    duration_ms INTEGER,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS worker_memory (
    worker_id TEXT PRIMARY KEY,
    jobs_completed INTEGER NOT NULL DEFAULT 0,
    jobs_failed INTEGER NOT NULL DEFAULT 0,
    average_runtime_ms INTEGER NOT NULL DEFAULT 0,
    average_confidence REAL NOT NULL DEFAULT 0,
    most_used_components TEXT,
    most_used_prompts TEXT,
    industries TEXT,
    companies TEXT,
    success_rate REAL NOT NULL DEFAULT 100,
    approval_rate REAL NOT NULL DEFAULT 0,
    reliability_score REAL NOT NULL DEFAULT 100,
    health TEXT NOT NULL DEFAULT 'Healthy',
    experience_summary TEXT,
    current_load INTEGER NOT NULL DEFAULT 0,
    last_activity TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS execution_plans (
    id TEXT PRIMARY KEY,
    command TEXT NOT NULL,
    intent TEXT NOT NULL,
    status TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 3,
    jobs TEXT,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS system_recommendations (
    id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    severity TEXT NOT NULL,
    recommendation TEXT NOT NULL,
    evidence TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_reasoning (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id TEXT NOT NULL,
    audit_score INTEGER,
    evidence_matrix TEXT,
    source_quality TEXT,
    evidence_summary TEXT,
    supporting_sources TEXT,
    contradictions TEXT,
    missing_evidence TEXT,
    duplicate_risk TEXT,
    bias_detection TEXT,
    confidence_explanation TEXT,
    recommendation TEXT,
    raw_reasoning TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS objectives (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 3,
    owner TEXT NOT NULL DEFAULT 'PX-H001',
    cadence TEXT,
    success_metric TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS operating_schedules (
    id TEXT PRIMARY KEY,
    objective_id TEXT,
    name TEXT NOT NULL,
    cadence TEXT NOT NULL,
    worker_id TEXT NOT NULL,
    job_type TEXT NOT NULL,
    payload TEXT,
    priority INTEGER NOT NULL DEFAULT 3,
    enabled INTEGER NOT NULL DEFAULT 1,
    last_run_at TEXT,
    next_run_hint TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS operating_briefs (
    id TEXT PRIMARY KEY,
    brief_type TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    metrics TEXT,
    recommendations TEXT,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS performance_snapshots (
    id TEXT PRIMARY KEY,
    worker_id TEXT,
    snapshot_type TEXT NOT NULL,
    metrics TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS research_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    research_id TEXT NOT NULL,
    action TEXT NOT NULL,
    details TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS research_performance (
    id TEXT PRIMARY KEY,
    market TEXT,
    company TEXT,
    package_count INTEGER NOT NULL DEFAULT 0,
    average_confidence REAL NOT NULL DEFAULT 0,
    average_evidence REAL NOT NULL DEFAULT 0,
    duplicate_count INTEGER NOT NULL DEFAULT 0,
    last_researched_at TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prompt_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_id TEXT NOT NULL,
    worker_id TEXT,
    job_id TEXT,
    token_usage INTEGER NOT NULL DEFAULT 0,
    response_quality INTEGER NOT NULL DEFAULT 0,
    success INTEGER NOT NULL DEFAULT 1,
    notes TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS studies (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    market TEXT NOT NULL,
    scope TEXT,
    countries TEXT,
    stakeholders TEXT,
    objective TEXT,
    status TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    lead_worker TEXT,
    research_worker TEXT,
    audit_worker TEXT,
    library_worker TEXT,
    notes TEXT,
    study_mode TEXT DEFAULT 'demo',
    data_origin TEXT DEFAULT 'demo',
    verification_status TEXT DEFAULT 'unverified',
    is_demo INTEGER NOT NULL DEFAULT 1,
    source_confidence REAL,
    created_by_worker TEXT DEFAULT 'PX-H001',
    last_updated TEXT,
    archive_reason TEXT,
    archived_at TEXT,
    archived_by TEXT,
    previous_status TEXT
);

CREATE TABLE IF NOT EXISTS study_runs (
    id TEXT PRIMARY KEY,
    study_id TEXT NOT NULL,
    study_mode TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    closed_at TEXT,
    data_origin TEXT DEFAULT 'demo',
    verification_status TEXT DEFAULT 'unverified',
    is_demo INTEGER NOT NULL DEFAULT 1,
    notes TEXT,
    created_by_worker TEXT DEFAULT 'PX-H001'
);

CREATE TABLE IF NOT EXISTS study_signals (
    id TEXT PRIMARY KEY,
    study_id TEXT NOT NULL,
    study_run_id TEXT,
    source_url TEXT,
    source_name TEXT,
    source_type TEXT,
    source_date TEXT,
    country TEXT,
    stakeholder_type TEXT,
    company_product TEXT,
    raw_text TEXT NOT NULL,
    complaint_category TEXT,
    summary TEXT,
    sentiment TEXT,
    evidence_strength INTEGER,
    duplicate_group TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    data_origin TEXT DEFAULT 'demo',
    verification_status TEXT DEFAULT 'unverified',
    is_demo INTEGER NOT NULL DEFAULT 1,
    source_confidence REAL,
    created_by_worker TEXT DEFAULT 'PX-R001',
    last_updated TEXT,
    archive_reason TEXT,
    archived_at TEXT,
    archived_by TEXT,
    previous_status TEXT
);

CREATE TABLE IF NOT EXISTS study_findings (
    id TEXT PRIMARY KEY,
    study_id TEXT NOT NULL,
    study_run_id TEXT,
    theme TEXT NOT NULL,
    problem_statement TEXT NOT NULL,
    complaint_category TEXT,
    signal_count INTEGER NOT NULL,
    independent_source_count INTEGER NOT NULL,
    countries TEXT,
    stakeholder_types TEXT,
    products_mentioned TEXT,
    representative_signals TEXT,
    evidence_summary TEXT,
    research_confidence INTEGER,
    confidence_score INTEGER,
    country_count INTEGER,
    stakeholder_count INTEGER,
    supporting_evidence_count INTEGER,
    contradictory_evidence_count INTEGER DEFAULT 0,
    confidence_reasoning TEXT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    data_origin TEXT DEFAULT 'demo',
    verification_status TEXT DEFAULT 'unverified',
    is_demo INTEGER NOT NULL DEFAULT 1,
    source_confidence REAL,
    created_by_worker TEXT DEFAULT 'PX-R001',
    last_updated TEXT,
    archive_reason TEXT,
    archived_at TEXT,
    archived_by TEXT,
    previous_status TEXT
);

CREATE TABLE IF NOT EXISTS finding_audits (
    id TEXT PRIMARY KEY,
    study_id TEXT NOT NULL,
    study_run_id TEXT,
    finding_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    evidence_score INTEGER,
    frequency_score INTEGER,
    market_size_score INTEGER,
    pain_severity_score INTEGER,
    competition_gap_score INTEGER,
    build_complexity_score INTEGER,
    commercial_potential_score INTEGER,
    strategic_fit_score INTEGER,
    traceability_score INTEGER,
    opportunity_confidence_index INTEGER,
    final_oci INTEGER,
    score_breakdown TEXT,
    oci_reasoning TEXT,
    missing_evidence_warnings TEXT,
    contradictions TEXT,
    missing_evidence TEXT,
    reasoning_summary TEXT,
    recommendation TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    data_origin TEXT DEFAULT 'demo',
    verification_status TEXT DEFAULT 'unverified',
    is_demo INTEGER NOT NULL DEFAULT 1,
    source_confidence REAL,
    created_by_worker TEXT DEFAULT 'PX-A001',
    last_updated TEXT,
    archive_reason TEXT,
    archived_at TEXT,
    archived_by TEXT,
    previous_status TEXT
);

CREATE TABLE IF NOT EXISTS opportunity_records (
    id TEXT PRIMARY KEY,
    study_id TEXT NOT NULL,
    study_run_id TEXT,
    industry TEXT,
    market TEXT,
    problem TEXT NOT NULL,
    evidence_summary TEXT,
    evidence_count INTEGER,
    independent_sources INTEGER,
    countries TEXT,
    products_mentioned TEXT,
    stakeholder_types TEXT,
    customer_segments TEXT,
    current_solutions TEXT,
    strengths_existing_solutions TEXT,
    weaknesses_existing_solutions TEXT,
    opportunity_confidence_index INTEGER,
    commercial_potential TEXT,
    estimated_market_size TEXT,
    estimated_build_complexity TEXT,
    recommended_component TEXT,
    recommended_pricing_model TEXT,
    recommended_market_entry TEXT,
    engineering_recommendation TEXT,
    problem_scope TEXT,
    target_users TEXT,
    required_inputs TEXT,
    expected_outputs TEXT,
    system_boundaries TEXT,
    traceability_chain_complete INTEGER NOT NULL DEFAULT 0,
    non_demo_evidence_only INTEGER NOT NULL DEFAULT 0,
    audit_id TEXT NOT NULL,
    finding_id TEXT NOT NULL,
    status TEXT NOT NULL,
    engineering_status TEXT,
    owner TEXT,
    version TEXT,
    created_at TEXT NOT NULL,
    last_updated TEXT NOT NULL,
    data_origin TEXT DEFAULT 'demo',
    verification_status TEXT DEFAULT 'unverified',
    is_demo INTEGER NOT NULL DEFAULT 1,
    source_confidence REAL,
    created_by_worker TEXT DEFAULT 'PX-L001',
    archive_reason TEXT,
    archived_at TEXT,
    archived_by TEXT,
    previous_status TEXT
);

CREATE TABLE IF NOT EXISTS study_briefs (
    id TEXT PRIMARY KEY,
    study_id TEXT NOT NULL,
    study_run_id TEXT,
    brief_type TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    metrics TEXT,
    top_opportunities TEXT,
    risks TEXT,
    missing_evidence TEXT,
    engineering_recommendation TEXT,
    created_at TEXT NOT NULL,
    data_origin TEXT DEFAULT 'demo',
    verification_status TEXT DEFAULT 'unverified',
    is_demo INTEGER NOT NULL DEFAULT 1,
    source_confidence REAL,
    created_by_worker TEXT DEFAULT 'PX-H001',
    last_updated TEXT,
    archive_reason TEXT,
    archived_at TEXT,
    archived_by TEXT,
    previous_status TEXT
);

CREATE TABLE IF NOT EXISTS demo_archive (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,
    record_id TEXT NOT NULL,
    record_json TEXT NOT NULL,
    archive_reason TEXT,
    archived_at TEXT NOT NULL,
    archived_by TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS discovery_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    study_id TEXT NOT NULL,
    study_run_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    query TEXT NOT NULL,
    query_group TEXT,
    urls_returned INTEGER NOT NULL DEFAULT 0,
    urls_skipped INTEGER NOT NULL DEFAULT 0,
    accepted_signals INTEGER NOT NULL DEFAULT 0,
    rejected_vendor INTEGER NOT NULL DEFAULT 0,
    rejected_market_context INTEGER NOT NULL DEFAULT 0,
    rejected_community INTEGER NOT NULL DEFAULT 0,
    rejected_unknown INTEGER NOT NULL DEFAULT 0,
    duplicates INTEGER NOT NULL DEFAULT 0,
    average_trust_score REAL NOT NULL DEFAULT 0,
    accepted_domains TEXT,
    rejected_domains TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS discovery_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    study_id TEXT NOT NULL,
    memory_type TEXT NOT NULL,
    memory_key TEXT NOT NULL,
    provider TEXT,
    query TEXT,
    score REAL NOT NULL DEFAULT 0,
    accepted_count INTEGER NOT NULL DEFAULT 0,
    rejected_count INTEGER NOT NULL DEFAULT 0,
    vendor_count INTEGER NOT NULL DEFAULT 0,
    market_context_count INTEGER NOT NULL DEFAULT 0,
    community_count INTEGER NOT NULL DEFAULT 0,
    duplicate_count INTEGER NOT NULL DEFAULT 0,
    average_trust_score REAL NOT NULL DEFAULT 0,
    last_seen_at TEXT NOT NULL,
    UNIQUE(study_id, memory_type, memory_key)
);

CREATE TABLE IF NOT EXISTS evidence_sources (
    id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    organisation TEXT NOT NULL,
    evidence_class TEXT NOT NULL,
    evidence_tier INTEGER NOT NULL DEFAULT 6,
    country TEXT NOT NULL DEFAULT 'United States',
    industry TEXT NOT NULL DEFAULT 'Residential Property Management',
    authority_level TEXT NOT NULL DEFAULT 'Unknown',
    trust_default INTEGER NOT NULL DEFAULT 0,
    collection_method TEXT NOT NULL DEFAULT 'Search Provider',
    authentication_required INTEGER NOT NULL DEFAULT 0,
    rate_limits TEXT,
    update_frequency TEXT,
    average_documents INTEGER NOT NULL DEFAULT 0,
    production_ready TEXT NOT NULL DEFAULT 'Unknown',
    legal_terms_notes TEXT,
    supported_golden_studies TEXT,
    current_status TEXT NOT NULL DEFAULT 'Not evaluated',
    accessible TEXT NOT NULL DEFAULT 'Unknown',
    structured TEXT NOT NULL DEFAULT 'Unknown',
    automatable TEXT NOT NULL DEFAULT 'Unknown',
    readiness_score INTEGER NOT NULL DEFAULT 0,
    readiness_label TEXT NOT NULL DEFAULT 'Not evaluated',
    created_at TEXT NOT NULL,
    last_evaluated_at TEXT
);

CREATE TABLE IF NOT EXISTS source_collection_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    study_id TEXT NOT NULL,
    run_id TEXT,
    provider TEXT,
    documents_collected INTEGER NOT NULL DEFAULT 0,
    accepted_evidence INTEGER NOT NULL DEFAULT 0,
    rejected_evidence INTEGER NOT NULL DEFAULT 0,
    duplicates INTEGER NOT NULL DEFAULT 0,
    marketing_rejected INTEGER NOT NULL DEFAULT 0,
    average_trust_score REAL NOT NULL DEFAULT 0,
    average_commercial_relevance REAL NOT NULL DEFAULT 0,
    average_operational_pain REAL NOT NULL DEFAULT 0,
    collection_error TEXT,
    created_at TEXT NOT NULL
);
"""


MIGRATIONS = {
    "research_records": {
        "source_type": "TEXT",
        "source_text": "TEXT",
        "pipeline_status": "TEXT",
    },
    "audit_records": {
        "duplicate_risk": "TEXT",
        "evidence_checklist": "TEXT",
        "reasoning_summary": "TEXT",
    },
    "library_records": {
        "tags": "TEXT",
        "audit_history": "TEXT",
        "origin_research_id": "TEXT",
        "researched_by": "TEXT",
        "audited_by": "TEXT",
        "prompt_id": "TEXT",
        "related_companies": "TEXT",
        "related_industries": "TEXT",
        "related_opportunities": "TEXT",
        "worker_history": "TEXT",
        "milestone_refs": "TEXT",
        "source_tracking": "TEXT",
    },
    "workers": {
        "version": "TEXT",
        "owner": "TEXT",
        "purpose": "TEXT",
        "health": "TEXT",
        "dependencies": "TEXT",
        "components_used": "TEXT",
        "prompt_version": "TEXT",
    },
    "components": {
        "purpose": "TEXT",
        "version": "TEXT",
        "tests": "TEXT",
        "dependencies": "TEXT",
        "updated_at": "TEXT",
    },
    "milestones": {
        "version": "TEXT",
        "completion_date": "TEXT",
        "workers_added": "TEXT",
        "components_added": "TEXT",
        "notes": "TEXT",
    },
    "jobs": {
        "dependencies": "TEXT",
        "history": "TEXT",
        "parent_job_id": "TEXT",
        "created_by": "TEXT",
    },
    "worker_messages": {
        "priority": "INTEGER NOT NULL DEFAULT 3",
        "payload": "TEXT",
        "status": "TEXT NOT NULL DEFAULT 'sent'",
    },
    "research_packages": {
        "country": "TEXT",
        "evidence_score": "INTEGER",
        "complaint_summary": "TEXT",
        "opportunity_summary": "TEXT",
        "trend_summary": "TEXT",
        "competitor_summary": "TEXT",
        "recommended_actions": "TEXT",
        "status": "TEXT",
        "research_history": "TEXT",
        "research_schedule": "TEXT",
        "research_performance": "TEXT",
    },
    "audit_reasoning": {
        "audit_score": "INTEGER",
        "evidence_matrix": "TEXT",
        "source_quality": "TEXT",
        "missing_evidence": "TEXT",
    },
    "prompt_benchmarks": {
        "token_usage": "INTEGER NOT NULL DEFAULT 0",
        "response_quality": "INTEGER NOT NULL DEFAULT 0",
        "success_rate": "REAL NOT NULL DEFAULT 0",
    },
    "studies": {
        "study_mode": "TEXT DEFAULT 'demo'",
        "data_origin": "TEXT DEFAULT 'demo'",
        "verification_status": "TEXT DEFAULT 'unverified'",
        "is_demo": "INTEGER NOT NULL DEFAULT 1",
        "source_confidence": "REAL",
        "created_by_worker": "TEXT DEFAULT 'PX-H001'",
        "last_updated": "TEXT",
        "archive_reason": "TEXT",
        "archived_at": "TEXT",
        "archived_by": "TEXT",
        "previous_status": "TEXT",
    },
    "study_signals": {
        "study_run_id": "TEXT",
        "data_origin": "TEXT DEFAULT 'demo'",
        "verification_status": "TEXT DEFAULT 'unverified'",
        "is_demo": "INTEGER NOT NULL DEFAULT 1",
        "source_confidence": "REAL",
        "created_by_worker": "TEXT DEFAULT 'PX-R001'",
        "last_updated": "TEXT",
        "archive_reason": "TEXT",
        "archived_at": "TEXT",
        "archived_by": "TEXT",
        "previous_status": "TEXT",
    },
    "study_findings": {
        "study_run_id": "TEXT",
        "confidence_score": "INTEGER",
        "country_count": "INTEGER",
        "stakeholder_count": "INTEGER",
        "supporting_evidence_count": "INTEGER",
        "contradictory_evidence_count": "INTEGER DEFAULT 0",
        "confidence_reasoning": "TEXT",
        "data_origin": "TEXT DEFAULT 'demo'",
        "verification_status": "TEXT DEFAULT 'unverified'",
        "is_demo": "INTEGER NOT NULL DEFAULT 1",
        "source_confidence": "REAL",
        "created_by_worker": "TEXT DEFAULT 'PX-R001'",
        "last_updated": "TEXT",
        "archive_reason": "TEXT",
        "archived_at": "TEXT",
        "archived_by": "TEXT",
        "previous_status": "TEXT",
    },
    "finding_audits": {
        "study_run_id": "TEXT",
        "traceability_score": "INTEGER",
        "final_oci": "INTEGER",
        "score_breakdown": "TEXT",
        "oci_reasoning": "TEXT",
        "missing_evidence_warnings": "TEXT",
        "data_origin": "TEXT DEFAULT 'demo'",
        "verification_status": "TEXT DEFAULT 'unverified'",
        "is_demo": "INTEGER NOT NULL DEFAULT 1",
        "source_confidence": "REAL",
        "created_by_worker": "TEXT DEFAULT 'PX-A001'",
        "last_updated": "TEXT",
        "archive_reason": "TEXT",
        "archived_at": "TEXT",
        "archived_by": "TEXT",
        "previous_status": "TEXT",
    },
    "opportunity_records": {
        "study_run_id": "TEXT",
        "engineering_recommendation": "TEXT",
        "problem_scope": "TEXT",
        "target_users": "TEXT",
        "required_inputs": "TEXT",
        "expected_outputs": "TEXT",
        "system_boundaries": "TEXT",
        "traceability_chain_complete": "INTEGER NOT NULL DEFAULT 0",
        "non_demo_evidence_only": "INTEGER NOT NULL DEFAULT 0",
        "data_origin": "TEXT DEFAULT 'demo'",
        "verification_status": "TEXT DEFAULT 'unverified'",
        "is_demo": "INTEGER NOT NULL DEFAULT 1",
        "source_confidence": "REAL",
        "created_by_worker": "TEXT DEFAULT 'PX-L001'",
        "archive_reason": "TEXT",
        "archived_at": "TEXT",
        "archived_by": "TEXT",
        "previous_status": "TEXT",
    },
    "study_briefs": {
        "study_run_id": "TEXT",
        "status": "TEXT NOT NULL DEFAULT 'active'",
        "data_origin": "TEXT DEFAULT 'demo'",
        "verification_status": "TEXT DEFAULT 'unverified'",
        "is_demo": "INTEGER NOT NULL DEFAULT 1",
        "source_confidence": "REAL",
        "created_by_worker": "TEXT DEFAULT 'PX-H001'",
        "last_updated": "TEXT",
        "archive_reason": "TEXT",
        "archived_at": "TEXT",
        "archived_by": "TEXT",
        "previous_status": "TEXT",
    },
    "evidence_sources": {
        "readiness_score": "INTEGER NOT NULL DEFAULT 0",
        "readiness_label": "TEXT NOT NULL DEFAULT 'Not evaluated'",
        "last_evaluated_at": "TEXT",
    },
    "source_collection_runs": {
        "average_commercial_relevance": "REAL NOT NULL DEFAULT 0",
        "average_operational_pain": "REAL NOT NULL DEFAULT 0",
        "collection_error": "TEXT",
    },
}


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def connect(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    with connect(db_path) as connection:
        connection.executescript(SCHEMA)
        migrate_db(connection)
        seed_registries(connection)
        seed_default_studies(connection)
        seed_default_study_runs(connection)
        mark_existing_golden_study_records_demo(connection)


def migrate_db(connection: sqlite3.Connection) -> None:
    for table_name, columns in MIGRATIONS.items():
        existing = {
            row["name"]
            for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        for column_name, column_type in columns.items():
            if column_name not in existing:
                connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")


def seed_registries(connection: sqlite3.Connection) -> None:
    now = utc_now()
    components = [
        ("COMP-001", "Prompt Engine", "Store, version, approve, test, and roll back prompts", "v3.0", "pytest prompt engine", "SQLite", "Prototype", "Active", "PX-A001,PX-L001,PX-R001,PX-H001", now, now),
    ]
    workers = [
        ("PX-H001", "Head of Functions", "Orchestrate commands, jobs, worker routing, memory, and recommendations", "Prototype", "Active", "v1.0", "PX-E002", "Coordinate PX-EOS execution without replacing specialist workers", "Healthy", "Job Engine,SQLite,Event Bus", "Job Engine,COMP-001", "v1.0.0", 95, 90, now),
        ("PX-A001", "Audit & Verification Worker", "Verify research before Library entry", "Prototype", "Active", "v2.0", "PX-E002", "Protect Library quality through evidence and duplicate checks", "Healthy", "COMP-001,SQLite", "COMP-001", "v1.0.0", 90, 80, now),
        ("PX-L001", "Library Manager", "Maintain canonical Library records", "Prototype", "Active", "v2.0", "PX-E002", "Maintain Library records, versions, tags, and changelog", "Healthy", "COMP-001,SQLite", "COMP-001", "v1.0.0", 85, 75, now),
        ("PX-R001", "Market Research Scanner", "Scan markets and create research packs", "Prototype", "Active", "v2.0", "PX-E002", "Extract structured research from local source material", "Healthy", "COMP-001,SQLite", "COMP-001", "v1.0.0", 80, 85, now),
    ]
    connection.executemany(
        """
        INSERT OR IGNORE INTO components
        (id, name, purpose, version, tests, dependencies, stage, status, reused_by, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        components,
    )
    connection.executemany(
        """
        INSERT OR IGNORE INTO workers
        (id, name, function, stage, status, version, owner, purpose, health, dependencies, components_used,
         prompt_version, internal_value_score, external_value_score, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        workers,
    )
    refresh_registry_metadata(connection, now)
    seed_milestones(connection, now)
    seed_engineering_journal(connection, now)


def refresh_registry_metadata(connection: sqlite3.Connection, now: str) -> None:
    connection.execute(
        """
        UPDATE components
        SET purpose = COALESCE(purpose, ?),
            version = COALESCE(version, ?),
            tests = COALESCE(tests, ?),
            dependencies = COALESCE(dependencies, ?),
            updated_at = COALESCE(updated_at, ?)
        WHERE id = 'COMP-001'
        """,
        ("Store, version, approve, test, and roll back prompts", "v3.0", "pytest prompt engine", "SQLite", now),
    )
    worker_defaults = [
        ("PX-H001", "v1.0", "PX-E002", "Coordinate PX-EOS execution without replacing specialist workers", "Healthy", "Job Engine,SQLite,Event Bus", "Job Engine,COMP-001", "v1.0.0"),
        ("PX-A001", "v2.0", "PX-E002", "Protect Library quality through evidence and duplicate checks", "Healthy", "COMP-001,SQLite", "COMP-001", "v1.0.0"),
        ("PX-L001", "v2.0", "PX-E002", "Maintain Library records, versions, tags, and changelog", "Healthy", "COMP-001,SQLite", "COMP-001", "v1.0.0"),
        ("PX-R001", "v2.0", "PX-E002", "Extract structured research from local source material", "Healthy", "COMP-001,SQLite", "COMP-001", "v1.0.0"),
    ]
    connection.executemany(
        """
        UPDATE workers
        SET version = COALESCE(version, ?),
            owner = COALESCE(owner, ?),
            purpose = COALESCE(purpose, ?),
            health = COALESCE(health, ?),
            dependencies = COALESCE(dependencies, ?),
            components_used = COALESCE(components_used, ?),
            prompt_version = COALESCE(prompt_version, ?)
        WHERE id = ?
        """,
        [
            (version, owner, purpose, health, dependencies, components_used, prompt_version, worker_id)
            for worker_id, version, owner, purpose, health, dependencies, components_used, prompt_version in worker_defaults
        ],
    )


def seed_milestones(connection: sqlite3.Connection, now: str) -> None:
    milestones = [
        ("M-0001", "First Prototype", "First Prototype Operational", "PX-R001, PX-A001, PX-L001, COMP-001, SQLite, Streamlit, JSON export, and tests became runnable locally.", now, "PX-E002", "Initial prototype files", "Completed"),
        ("M-0002", "Sprint 2", "PX-EOS Foundation", "Dashboard, automated queues, worker status, activity history, notifications, and Prompt Engine v2 established.", now, "PX-E002", "project_exchange/eos.py, streamlit_app.py", "Completed"),
        ("M-0003", "Sprint 3", "PX-EOS Operating System Layer", "Event bus, timeline, registries, milestones, engineering journal, and pipeline operating view added.", now, "PX-E002", "project_exchange/eos.py, project_exchange/database.py, streamlit_app.py", "Completed"),
        ("M-0004", "Sprint 4", "Autonomous Execution Layer", "Job engine, queues, logs, error recovery, analytics, and autonomous execution controls added.", now, "PX-E002", "project_exchange/eos.py, project_exchange/database.py, streamlit_app.py, tests", "Completed"),
        ("M-0005", "Sprint 5", "Real World Integration", "Environment loading, provider modules, Provider Settings, live research providers, worker messages, knowledge graph, and prompt benchmarks added.", now, "PX-E002", "project_exchange/config.py, project_exchange/research_engine.py, project_exchange/provider_modules, streamlit_app.py, tests", "Completed"),
        ("M-0006", "Sprint 6", "Intelligence & Orchestration", "PX-H001 Head of Functions, execution plans, worker memory, routed worker communication, audit reasoning, and system recommendations added.", now, "PX-E002", "project_exchange/head_of_functions.py, project_exchange/database.py, project_exchange/eos.py, streamlit_app.py, tests", "Completed"),
        ("M-0007", "Sprint 7", "Operational Readiness", "Stabilised PX-EOS around the base workers before expanding into long-running operations.", now, "PX-E002", "project_exchange, streamlit_app.py, tests", "Completed"),
        ("M-0008", "Sprint 8", "Operational Base Workers", "Base workers gained objectives, schedules, operating briefs, worker load monitoring, performance snapshots, richer research packages, audit reasoning, library lineage, and prompt usage intelligence.", now, "PX-E002", "project_exchange/head_of_functions.py, project_exchange/database.py, project_exchange/research_engine.py, streamlit_app.py, components, workers, tests", "Completed"),
    ]
    connection.executemany(
        """
        INSERT OR IGNORE INTO milestones
        (id, sprint, title, description, date, completed_by, files_changed, result)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        milestones,
    )


def seed_engineering_journal(connection: sqlite3.Connection, now: str) -> None:
    connection.execute(
        """
        INSERT OR IGNORE INTO engineering_journal
        (id, title, entry_type, body, related_entity, created_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            1,
            "PX-EOS architecture direction",
            "Architecture Decision",
            "PX-EOS owns shared operating concerns: eventing, status, history, registries, milestones, and journal records. Workers remain focused applications that plug into the operating system.",
            "PX-EOS",
            "PX-E002",
            now,
        ),
    )


def seed_default_studies(connection: sqlite3.Connection) -> None:
    now = utc_now()
    connection.execute(
        """
        INSERT OR IGNORE INTO studies
        (id, name, market, scope, countries, stakeholders, objective, status, started_at, lead_worker,
         research_worker, audit_worker, library_worker, notes, study_mode, data_origin, verification_status, is_demo,
         created_by_worker, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "GS-001",
            "Global Property Management Golden Study",
            "Property Management",
            "Global",
            "Global",
            "Property managers, Tenants, Housing associations, Facilities managers, Estate management companies, Condo / HOA managers, Commercial property managers, Letting agents, Property owners, Maintenance contractors",
            "Find verified, traceable market opportunities backed by repeated complaints and evidence.",
            "Active",
            now,
            "PX-H001",
            "PX-R001",
            "PX-A001",
            "PX-L001",
            "Default Golden Study for the global Property Management market.",
            "demo",
            "demo",
            "unverified",
            1,
            "PX-H001",
            now,
        ),
    )


def seed_default_study_runs(connection: sqlite3.Connection) -> None:
    now = utc_now()
    connection.execute(
        """
        INSERT OR IGNORE INTO study_runs
        (id, study_id, study_mode, status, created_at, data_origin, verification_status, is_demo, notes, created_by_worker)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "GSR-2026-000001",
            "GS-001",
            "demo",
            "active",
            now,
            "demo",
            "unverified",
            1,
            "Default demo run for GS-001.",
            "PX-H001",
        ),
    )


def mark_existing_golden_study_records_demo(connection: sqlite3.Connection) -> None:
    now = utc_now()
    for table_name in ["studies", "study_signals", "study_findings", "finding_audits", "opportunity_records", "study_briefs"]:
        columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()}
        if {"data_origin", "verification_status", "is_demo", "last_updated"} <= columns:
            where = "study_id = 'GS-001'" if "study_id" in columns else "id = 'GS-001'"
            study_mode_sql = "study_mode = COALESCE(study_mode, 'demo')," if table_name == "studies" and "study_mode" in columns else ""
            connection.execute(
                f"""
                UPDATE {table_name}
                SET {study_mode_sql}
                    data_origin = COALESCE(data_origin, 'demo'),
                    verification_status = CASE
                        WHEN COALESCE(is_demo, 1) = 1 THEN 'unverified'
                        ELSE COALESCE(verification_status, 'pending_review')
                    END,
                    is_demo = COALESCE(is_demo, 1),
                    last_updated = COALESCE(last_updated, ?)
                WHERE {where}
                """,
                (now,),
            )


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def fetch_all(db_path: str | Path, table_name: str) -> list[dict[str, Any]]:
    if table_name not in {
        "prompts",
        "prompt_tests",
        "research_records",
        "audit_records",
        "library_records",
        "workers",
        "components",
        "changelog",
        "worker_activity",
        "notifications",
        "prompt_versions",
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
        "study_runs",
        "study_signals",
        "study_findings",
        "finding_audits",
        "opportunity_records",
        "study_briefs",
        "demo_archive",
        "discovery_runs",
        "discovery_memory",
        "evidence_sources",
        "source_collection_runs",
    }:
        raise ValueError(f"Unsupported table: {table_name}")
    with connect(db_path) as connection:
        rows = connection.execute(f"SELECT * FROM {table_name}").fetchall()
    return [row_to_dict(row) for row in rows]


def count_rows(connection: sqlite3.Connection, table_name: str) -> int:
    row = connection.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()
    return int(row["count"])


def add_changelog(connection: sqlite3.Connection, entity_id: str, entity_type: str, message: str) -> None:
    connection.execute(
        "INSERT INTO changelog (entity_id, entity_type, message, created_at) VALUES (?, ?, ?, ?)",
        (entity_id, entity_type, message, utc_now()),
    )
