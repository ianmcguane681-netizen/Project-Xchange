import json

from project_exchange.database import connect, fetch_all, init_db, utc_now
from project_exchange.provider_base import ProviderResult
from project_exchange.golden_study import (
    DEFAULT_STUDY_ID,
    approve_audited_opportunities,
    approval_feedback,
    archive_all_demo_data,
    archive_current_production_run_and_start_fresh,
    archive_record,
    audit_batch_feedback,
    audit_finding,
    build_evidence_clusters,
    canonical_pain_category,
    calculate_oci,
    create_signal,
    create_study,
    discovery_learning_dashboard,
    discovery_memory_rows,
    evidence_class_for_source,
    evidence_quality_profile,
    evidence_tier_for_class,
    finding_evidence,
    generate_executive_brief,
    generate_findings,
    findings_feedback,
    finding_cluster_metadata,
    get_active_study_run,
    get_or_create_default_study,
    is_signal_in_gs001_scope,
    list_findings,
    list_signals,
    list_study_runs,
    list_opportunities,
    mark_engineering_ready,
    production_pipeline_statuses,
    prioritized_evidence_query_runs,
    prioritized_query_runs,
    pull_real_market_evidence,
    switch_study_run_mode,
    run_audit_batch,
    run_research_batch,
    signal_trace_card_view_model,
    study_progress,
    traceability_chain,
    validate_golden_study_integrity,
)


class StaticEvidenceProvider:
    name = "Tavily"

    def __init__(self, results):
        self.results = results
        self.used = False

    def search(self, command):
        if self.used:
            return []
        self.used = True
        return self.results


class OpenAIOnlyEvidenceProvider:
    name = "OpenAI"

    def search(self, command):
        return [
            ProviderResult(
                "OpenAI",
                "Generated maintenance communication claim",
                "",
                "OpenAI says tenants might complain about maintenance updates.",
                "llm",
            )
        ]


class BrokenEvidenceProvider:
    name = "NewsAPI"

    def search(self, command):
        raise RuntimeError("provider unavailable")


class QueryAwareEvidenceProvider:
    name = "Tavily"

    def __init__(self):
        self.commands = []

    def search(self, command):
        self.commands.append(command)
        keyword = str(command.get("keyword") or "")
        if "bbb.org" in keyword:
            return [
                ProviderResult(
                    "Tavily",
                    "BBB property management maintenance complaint",
                    "https://www.bbb.org/property-management-maintenance-complaint",
                    "Tenant complaint says maintenance request had no response and apartment repair was delayed.",
                    "search_result",
                )
            ]
        if "consumeraffairs.com" in keyword:
            return [
                ProviderResult(
                    "Tavily",
                    "Consumer Affairs maintenance complaint",
                    "https://www.consumeraffairs.com/property-management-maintenance",
                    "Property manager complaint says maintenance request updates are slow and tenants are not updated.",
                    "search_result",
                )
            ]
        if "reddit" in keyword:
            return [
                ProviderResult(
                    "Tavily",
                    "Reddit landlord repair complaint",
                    "https://www.reddit.com/r/tenant/comments/repair",
                    "Resident complaint says rental maintenance request is unresolved and repair communication is poor.",
                    "search_result",
                )
            ]
        return [
            ProviderResult(
                "Tavily",
                "Vendor maintenance response page",
                "https://vendor.example.com/industries/property-management/maintenance-response",
                "Our platform tracks maintenance response times and automates work orders.",
                "search_result",
            )
        ]


def start_production_run(db_path):
    return switch_study_run_mode(db_path, DEFAULT_STUDY_ID, "production", production_confirmed=True)


def test_default_study_creation(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    study = get_or_create_default_study(db_path)
    active_run = get_active_study_run(db_path)
    assert study["id"] == DEFAULT_STUDY_ID
    assert study["market"] == "Property Management"
    assert study["status"] == "Active"
    assert study["study_mode"] == "demo"
    assert active_run["study_mode"] == "demo"
    assert active_run["status"] == "active"


def test_signal_creation_and_finding_clustering(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)

    create_signal(
        db_path,
        "Property managers in Ireland repeatedly complain that maintenance updates are slow and tenants chase repairs.",
        country="Ireland",
        stakeholder_type="Property managers",
        source_name="Irish forum",
        data_origin="verified_import",
    )
    create_signal(
        db_path,
        "Tenants in the United Kingdom complain that maintenance communication is slow and repair updates need repeated chasing.",
        country="United Kingdom",
        stakeholder_type="Tenants",
        source_name="UK review",
        data_origin="verified_import",
    )
    create_signal(
        db_path,
        "Apartment residents in the United States complain that maintenance request updates are delayed and repairs are unresolved.",
        country="United States",
        stakeholder_type="Tenants",
        source_name="US review",
        data_origin="verified_import",
    )

    findings = generate_findings(db_path)
    assert findings
    assert findings[0]["signal_count"] == 3
    assert findings[0]["status"] == "pending_audit"
    assert findings[0]["is_demo"] == 0


def test_oci_calculation_inverts_build_complexity():
    low_complexity = {
        "evidence_score": 90,
        "frequency_score": 90,
        "market_size_score": 90,
        "pain_severity_score": 90,
        "competition_gap_score": 80,
        "build_complexity_score": 20,
        "commercial_potential_score": 90,
        "strategic_fit_score": 90,
    }
    high_complexity = {**low_complexity, "build_complexity_score": 90}

    assert calculate_oci(low_complexity) > calculate_oci(high_complexity)


def test_audit_approval_and_traceability_chain(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)

    batch = run_research_batch(
        db_path,
        [
            {
                "country": "Ireland",
                "stakeholder_type": "Property managers",
                "source_url": "https://www.consumeraffairs.com/property-management/irish",
                "source_name": "Consumer Affairs Irish complaint",
                "data_origin": "verified_import",
                "raw_text": "Property managers in Ireland repeatedly complain that maintenance updates are slow and tenants chase responses multiple times.",
            },
            {
                "country": "United Kingdom",
                "stakeholder_type": "Tenants",
                "source_url": "https://www.bbb.org/property-management/uk",
                "source_name": "BBB UK complaint",
                "data_origin": "verified_import",
                "raw_text": "Tenants in the United Kingdom repeatedly complain that repair communication is poor and maintenance updates are delayed.",
            },
            {
                "country": "United States",
                "stakeholder_type": "Property owners",
                "source_url": "https://www.gov.example/property-management/us",
                "source_name": "Government US complaint",
                "data_origin": "verified_import",
                "raw_text": "Property owners in the United States complain that maintenance coordination is manual, slow, and expensive.",
            },
        ],
    )
    assert batch["signals"]
    assert batch["findings"]

    audits = run_audit_batch(db_path)
    assert audits
    assert audits[0]["opportunity_confidence_index"] >= 85

    opportunities = approve_audited_opportunities(db_path)
    assert opportunities == []
    assert audits[0]["decision"] == "Needs More Evidence"
    assert "Minimum independent market events" in audits[0]["missing_evidence_warnings"]


def test_archive_instead_of_delete_and_executive_brief(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    signal = create_signal(
        db_path,
        "Property managers complain that reporting is manual and slow.",
        country="Ireland",
        stakeholder_type="Property managers",
        source_name="Manual source",
    )
    archived = archive_record(db_path, "study_signals", signal["id"])
    assert archived["status"] == "archived"
    assert fetch_all(db_path, "study_signals")[0]["status"] == "archived"

    brief = generate_executive_brief(db_path)
    assert brief["study_id"] == DEFAULT_STUDY_ID
    assert "signals" in brief["body"]

    progress = study_progress(db_path)
    assert progress["study_id"] == DEFAULT_STUDY_ID


def test_direct_audit_finding_path(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)

    create_signal(db_path, "Property managers repeatedly complain that maintenance request software is slow and repair updates are not updated.", source_name="A", data_origin="verified_import")
    create_signal(db_path, "Tenants complain that apartment maintenance request updates are delayed and repairs are unresolved.", source_name="B", data_origin="verified_import")
    create_signal(db_path, "Landlords complain that rental maintenance communication is poor and work order updates are ignored.", source_name="C", data_origin="verified_import")
    finding = generate_findings(db_path)[0]
    audit = audit_finding(db_path, finding["id"])

    assert audit["decision"] in {"Approve Opportunity", "Needs More Evidence", "Reject"}
    assert audit["reasoning_summary"]
    assert fetch_all(db_path, "finding_audits")
    assert list_opportunities(db_path) == []


def test_production_run_switch_requires_confirmation(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    try:
        switch_study_run_mode(db_path, DEFAULT_STUDY_ID, "production")
    except ValueError as exc:
        assert "explicit confirmation" in str(exc)
    else:
        raise AssertionError("Production run creation should require confirmation")

    run = start_production_run(db_path)
    assert run["study_mode"] == "production"
    assert run["verification_status"] == "pending_review"


def test_demo_records_block_production_evidence_until_archived(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    demo_signal = create_signal(db_path, "Demo evidence about maintenance communication.", source_name="Demo source")
    try:
        create_signal(
            db_path,
            "Real source says maintenance communication remains slow.",
            source_name="Real source",
            data_origin="manual",
        )
    except ValueError as exc:
        assert "Start a production run" in str(exc)
    else:
        raise AssertionError("Production evidence should be blocked while demo records exist")

    archive_record(db_path, "study_signals", demo_signal["id"])
    start_production_run(db_path)
    real_signal = create_signal(
        db_path,
        "Real source says maintenance communication remains slow.",
        source_name="Real source",
        data_origin="manual",
    )
    assert real_signal["verification_status"] == "pending_review"
    assert real_signal["is_demo"] == 0


def test_non_demo_signal_requires_source_reference(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    try:
        create_signal(db_path, "Real evidence without source.", data_origin="manual")
    except ValueError as exc:
        assert "Source URL or Source name" in str(exc)
    else:
        raise AssertionError("Non-demo evidence should require a source")


def test_demo_signal_cannot_be_added_after_production_evidence(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)

    create_signal(
        db_path,
        "Tenant complaint says a maintenance request had no response and apartment repair communication was poor.",
        source_name="Real source",
        data_origin="manual",
    )
    try:
        create_signal(db_path, "Demo evidence should not mix into the same run.")
    except ValueError as exc:
        assert "Production studies cannot contain demo records" in str(exc)
    else:
        raise AssertionError("Demo evidence should not be allowed after production evidence")


def test_integrity_failures_include_recommended_fix(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    create_signal(db_path, "Demo evidence about maintenance communication.", source_name="Demo source")
    validation = validate_golden_study_integrity(db_path)

    assert validation["checks"]
    assert all("recommended_fix" in check for check in validation["checks"])


def test_demo_data_is_labelled_and_blocked_from_approval(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    create_signal(db_path, "Property managers repeatedly complain that maintenance communication is slow.", source_name="Demo A")
    create_signal(db_path, "Tenants repeatedly complain that maintenance communication is slow.", source_name="Demo B")
    finding = generate_findings(db_path)[0]

    assert finding["is_demo"] == 1
    assert finding["data_origin"] == "demo"
    assert finding["verification_status"] == "unverified"
    assert finding["status"] == "Demo Finding"
    audit = audit_finding(db_path, finding["id"])
    opportunity = approve_audited_opportunities(db_path)[0]

    assert audit["status"] == "Demo Audited"
    assert audit["decision"] == "Demo Audited"
    assert opportunity["status"] == "Demo Opportunity"
    assert opportunity["is_demo"] == 1
    assert opportunity["data_origin"] == "demo"
    assert opportunity["verification_status"] == "unverified"


def test_archive_all_demo_data_preserves_records_and_archives_briefs(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    create_signal(db_path, "Property managers repeatedly complain that maintenance communication is slow.", source_name="Demo A")
    create_signal(db_path, "Tenants repeatedly complain that maintenance communication is slow.", source_name="Demo B")
    generate_findings(db_path)
    run_audit_batch(db_path)
    approve_audited_opportunities(db_path)
    generate_executive_brief(db_path)

    result = archive_all_demo_data(db_path)
    rows = {
        table_name: fetch_all(db_path, table_name)
        for table_name in ["study_signals", "study_findings", "finding_audits", "opportunity_records", "study_briefs"]
    }
    demo_runs = [run for run in list_study_runs(db_path) if run["study_mode"] == "demo"]

    assert result["records_archived"] >= 5
    assert all(row["status"] == "archived" for table_rows in rows.values() for row in table_rows)
    assert demo_runs[0]["status"] == "archived"
    assert rows["study_signals"]
    assert rows["study_briefs"]


def test_switching_to_production_creates_clean_active_run(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    demo_signal = create_signal(db_path, "Demo evidence about maintenance communication.", source_name="Demo A")
    demo_run = get_active_study_run(db_path)
    assert demo_signal["study_run_id"] == demo_run["id"]

    production_run = start_production_run(db_path)
    runs = list_study_runs(db_path)
    demo_run_after = [run for run in runs if run["id"] == demo_run["id"]][0]
    progress = study_progress(db_path)

    assert demo_run_after["status"] == "closed"
    assert production_run["status"] == "active"
    assert production_run["study_mode"] == "production"
    assert progress["active_run_id"] == production_run["id"]
    assert progress["signals_collected"] == 0
    assert progress["findings_created"] == 0
    assert progress["audits_completed"] == 0
    assert progress["engineering_ready"] == []
    assert progress["average_oci"] == 0
    assert fetch_all(db_path, "study_signals")[0]["status"] == "archived"


def test_demo_engineering_ready_and_oci_do_not_leak_into_production(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    demo_signal_a = create_signal(db_path, "Property managers repeatedly complain that maintenance communication is slow.", source_name="Demo A")
    create_signal(db_path, "Tenants repeatedly complain that maintenance communication is slow.", source_name="Demo B")
    demo_run = get_active_study_run(db_path)
    finding = generate_findings(db_path)[0]
    now = utc_now()
    with connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO finding_audits
            (id, study_id, study_run_id, finding_id, decision, opportunity_confidence_index, final_oci,
             status, created_at, data_origin, verification_status, is_demo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("FAD-DEMO", DEFAULT_STUDY_ID, demo_run["id"], finding["id"], "Approve Opportunity", 99, 99, "active", now, "demo", "unverified", 1),
        )
        connection.execute(
            """
            INSERT INTO opportunity_records
            (id, study_id, study_run_id, problem, opportunity_confidence_index, audit_id, finding_id, status,
             engineering_status, created_at, last_updated, data_origin, verification_status, is_demo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "OPP-DEMO",
                DEFAULT_STUDY_ID,
                demo_run["id"],
                "Demo opportunity",
                99,
                "FAD-DEMO",
                finding["id"],
                "Engineering Ready",
                "Engineering Ready",
                now,
                now,
                "demo",
                "unverified",
                1,
            ),
        )

    production_run = start_production_run(db_path)
    production_progress = study_progress(db_path)
    archived_chain = traceability_chain(db_path, "OPP-DEMO", include_archived=True)

    assert production_progress["active_run_id"] == production_run["id"]
    assert production_progress["engineering_ready"] == []
    assert production_progress["average_oci"] == 0
    assert production_progress["top_opportunities"] == []
    assert archived_chain["opportunity"]["id"] == "OPP-DEMO"
    assert archived_chain["opportunity"]["study_run_id"] == demo_run["id"]
    assert archived_chain["signals"][0]["study_run_id"] == demo_run["id"]
    assert len(fetch_all(db_path, "demo_archive")) >= 1


def test_production_evidence_increases_only_production_kpis(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    create_signal(db_path, "Demo evidence about maintenance communication.", source_name="Demo A")
    demo_run = get_active_study_run(db_path)
    production_run = start_production_run(db_path)
    run_research_batch(
        db_path,
        [
            {
                "country": "Ireland",
                "stakeholder_type": "Property managers",
                "source_url": "https://www.consumeraffairs.com/property-management/irish",
                "source_name": "Consumer Affairs Irish complaint",
                "data_origin": "verified_import",
                "raw_text": "Property managers in Ireland repeatedly complain that maintenance updates are slow and tenants chase responses multiple times.",
            },
            {
                "country": "United Kingdom",
                "stakeholder_type": "Tenants",
                "source_url": "https://www.bbb.org/property-management/uk",
                "source_name": "BBB UK complaint",
                "data_origin": "verified_import",
                "raw_text": "Tenants in the United Kingdom repeatedly complain that repair communication is poor and maintenance updates are delayed.",
            },
            {
                "country": "United States",
                "stakeholder_type": "Property owners",
                "source_url": "https://www.gov.example/property-management/us",
                "source_name": "Government US complaint",
                "data_origin": "verified_import",
                "raw_text": "Property owners in the United States complain that maintenance request communication is slow and work order updates are unresolved.",
            },
        ],
    )

    production_progress = study_progress(db_path)
    demo_history_progress = study_progress(db_path, study_run_id=demo_run["id"], include_archived=True, include_demo=True)

    assert production_progress["active_run_id"] == production_run["id"]
    assert production_progress["signals_collected"] == 3
    assert production_progress["findings_created"] == 1
    assert production_progress["demo_records_count"] == 0
    assert demo_history_progress["signals_collected"] == 1


def test_archived_demo_records_do_not_count_in_production_metrics(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    run_research_batch(
        db_path,
        [
            {"source_name": "Demo A", "data_origin": "demo", "raw_text": "Property managers repeatedly complain maintenance updates are slow."},
            {"source_name": "Demo B", "data_origin": "demo", "raw_text": "Tenants repeatedly complain maintenance updates are slow."},
        ],
    )
    run_audit_batch(db_path)
    opportunities = approve_audited_opportunities(db_path)
    mark_engineering_ready(
        db_path,
        opportunities[0]["id"],
        {
            "recommended_component": "Demo Component",
            "engineering_recommendation": "Demo recommendation",
            "problem_scope": "Demo scope",
            "target_users": "Demo users",
            "required_inputs": "Demo inputs",
            "expected_outputs": "Demo outputs",
            "system_boundaries": "Demo boundaries",
        },
    )
    demo_run = get_active_study_run(db_path)
    start_production_run(db_path)

    production_progress = study_progress(db_path)
    demo_history = study_progress(db_path, study_run_id=demo_run["id"], include_archived=True, include_demo=True)

    assert production_progress["signals_collected"] == 0
    assert production_progress["findings_created"] == 0
    assert production_progress["audits_completed"] == 0
    assert production_progress["opportunities_approved"] == 0
    assert production_progress["engineering_ready"] == []
    assert production_progress["average_oci"] == 0
    assert demo_history["signals_collected"] == 2
    assert demo_history["findings_created"] == 1
    assert demo_history["audits_completed"] == 1
    archived_demo_opportunities = list_opportunities(db_path, study_run_id=demo_run["id"], include_archived=True, include_demo=True)
    assert len(archived_demo_opportunities) == 1
    assert archived_demo_opportunities[0]["status"] == "archived"
    assert archived_demo_opportunities[0]["previous_status"] == "Demo Engineering Ready"


def test_list_functions_default_to_active_run_but_raw_access_keeps_history(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    demo_signal = create_signal(db_path, "Demo evidence about maintenance communication.", source_name="Demo A")
    demo_run = get_active_study_run(db_path)
    production_run = start_production_run(db_path)
    production_signal = create_signal(
        db_path,
        "Real source says maintenance communication remains slow.",
        source_name="Real source",
        data_origin="manual",
    )

    active_signals = list_signals(db_path)
    raw_signals = fetch_all(db_path, "study_signals")
    demo_history = study_progress(db_path, study_run_id=demo_run["id"], include_archived=True, include_demo=True)

    assert [signal["id"] for signal in active_signals] == [production_signal["id"]]
    assert active_signals[0]["study_run_id"] == production_run["id"]
    assert {signal["id"] for signal in raw_signals} == {demo_signal["id"], production_signal["id"]}
    assert demo_history["signals_collected"] == 1


def test_demo_batch_feedback_and_visible_signals(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    batch = run_research_batch(
        db_path,
        [
            {"source_name": "Demo A", "data_origin": "demo", "raw_text": "Property managers repeatedly complain maintenance updates are slow."},
            {"source_name": "Demo B", "data_origin": "demo", "raw_text": "Tenants repeatedly complain maintenance updates are slow."},
        ],
    )
    visible_signals = list_signals(db_path, include_demo=True)

    assert len(batch["signals"]) == 2
    assert len(visible_signals) == 2


def test_pull_real_market_evidence_blocked_outside_production(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    get_or_create_default_study(db_path)

    result = pull_real_market_evidence(
        db_path,
        providers=[
            StaticEvidenceProvider([
                ProviderResult("Tavily", "Real source", "https://example.com/source", "Tenants complain about maintenance request updates.", "search_result")
            ])
        ],
    )

    assert result["status"] == "blocked"
    assert result["message"] == "Real market evidence can only be pulled in Production Mode."
    assert list_signals(db_path, include_demo=True) == []


def test_pull_real_market_evidence_blocks_when_no_active_run_exists(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    result = pull_real_market_evidence(db_path)

    assert result["status"] == "blocked"
    assert result["signals_stored"] == 0
    assert result["active_run_id"] == ""


def test_pull_real_market_evidence_requires_configured_provider(monkeypatch, tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)
    monkeypatch.setattr(
        "project_exchange.golden_study.provider_ready_for_research",
        lambda: {
            "ready": False,
            "message": "No provider configured. Add API keys in Provider Settings or paste evidence manually.",
            "providers": [],
        },
    )

    result = pull_real_market_evidence(db_path)

    assert result["status"] == "blocked"
    assert result["message"] == "No provider configured. Add API keys in Provider Settings or paste evidence manually."
    assert list_signals(db_path) == []


def test_pull_real_market_evidence_provider_failure_creates_no_fake_records(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)

    result = pull_real_market_evidence(db_path, providers=[BrokenEvidenceProvider()])

    assert result["status"] == "empty"
    assert result["signals_stored"] == 0
    assert any(item["reason"] == "provider_failed" for item in result["skipped"])
    assert list_signals(db_path) == []


def test_pull_real_market_evidence_skips_missing_source_and_text(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)
    provider = StaticEvidenceProvider(
        [
            ProviderResult("Tavily", "", "", "Tenants complain about slow maintenance communication.", "search_result"),
            ProviderResult("Tavily", "Missing text source", "https://example.com/missing-text", "", "search_result"),
        ]
    )

    result = pull_real_market_evidence(db_path, providers=[provider])

    assert result["status"] == "empty"
    assert result["signals_stored"] == 0
    assert result["skipped_missing_source_or_text"] == 2
    assert len(result["skipped"]) == 2
    assert list_signals(db_path) == []


def test_pull_real_market_evidence_creates_provider_signal_in_active_production_run(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    production_run = start_production_run(db_path)
    provider = StaticEvidenceProvider(
        [
            ProviderResult(
                "Tavily",
                "Tenant maintenance complaints rise",
                "https://example.com/tenant-maintenance",
                "Tenants complain that apartment maintenance request updates are unclear and property managers do not communicate timelines.",
                "article",
            )
        ]
    )

    result = pull_real_market_evidence(db_path, providers=[provider])
    signals = list_signals(db_path)

    assert result["status"] == "completed"
    assert result["signals_stored"] == 1
    assert result["active_run_id"] == production_run["id"]
    assert result["stored_signal_ids"]
    assert result["queries"]
    assert result["sources_searched"] == len(result["queries"])
    assert result["candidate_results_found"] == 1
    assert result["skipped_duplicates"] == 0
    assert result["skipped_missing_source_or_text"] == 0
    assert result["providers_used"] == ["Tavily"]
    assert len(signals) == 1
    signal = signals[0]
    assert signal["study_run_id"] == production_run["id"]
    assert signal["is_demo"] == 0
    assert signal["data_origin"] == "provider"
    assert signal["verification_status"] == "pending_verification"
    assert signal["source_url"] == "https://example.com/tenant-maintenance"
    assert signal["source_type"] == "article"
    assert signal["country"] == "United States"
    metadata = json.loads(signal["source_name"])
    assert metadata["metadata_type"] == "provider_evidence"
    assert metadata["provider_name"] == "Tavily"
    assert metadata["original_query"] == result["queries"][0]
    assert metadata["retrieved_at"]
    assert metadata["original_title"] == "Tenant maintenance complaints rise"


def test_evidence_discovery_runs_focused_query_groups_and_prioritizes_trusted_sources(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)
    provider = QueryAwareEvidenceProvider()

    result = pull_real_market_evidence(db_path, providers=[provider], max_sources=2)
    signals = list_signals(db_path)

    assert len(provider.commands) >= 15
    assert {command["query_group"] for command in provider.commands} >= {"consumer_complaint", "bbb", "consumer_affairs", "government", "forums"}
    assert result["queries_executed"] == len(provider.commands)
    assert result["urls_retrieved"] >= len(provider.commands)
    assert result["vendor_urls"] > 0
    assert result["complaint_urls"] >= 2
    assert result["accepted_signals"] == 2
    assert result["signals_stored"] == 2
    assert result["technical_details"]["domain_learning"]["trusted_domains"]
    assert all("vendor.example.com" not in str(signal.get("source_url")) for signal in signals)


def test_gsp001_query_strategy_prioritises_authoritative_evidence_tiers(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    query_runs = prioritized_evidence_query_runs(db_path)
    tiers = [int(run["evidence_tier"]) for run in query_runs]

    assert tiers == sorted(tiers)
    assert query_runs[0]["evidence_class"] in {"Regulator", "Attorney General", "Housing Authority", "Court", "Ombudsman"}
    assert all(run.get("query_category") for run in query_runs)
    assert all("evidence_class" in run for run in query_runs)


def test_evidence_class_mapping_uses_source_authority_not_provider_volume():
    assert evidence_class_for_source("government", "https://www.hud.gov/maintenance-complaint", "Tenant repair complaint") == "Regulator"
    assert evidence_class_for_source("search_result", "https://www.bbb.org/property-management-maintenance", "Complaint") == "Consumer Complaints"
    assert evidence_class_for_source("vendor", "https://vendor.example.com/industries/property-management", "Book a demo") == "Vendor"
    assert evidence_tier_for_class("Regulator") == 1
    assert evidence_tier_for_class("Vendor") == 6


def test_pull_real_market_evidence_sends_acquisition_strategy_to_providers(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)
    provider = QueryAwareEvidenceProvider()

    result = pull_real_market_evidence(db_path, providers=[provider], max_sources=1)

    assert result["query_runs"]
    assert all(command.get("acquisition_strategy") == "GS-P001" for command in provider.commands)
    assert all(command.get("evidence_class") for command in provider.commands)
    assert all(command.get("evidence_tier") for command in provider.commands)
    assert all(command.get("query_category") for command in provider.commands)
    assert min(int(command["evidence_tier"]) for command in provider.commands[:5]) == 1


def test_discovery_learning_stores_successful_domains_as_trusted(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)

    result = pull_real_market_evidence(db_path, providers=[QueryAwareEvidenceProvider()], max_sources=2)
    memory = discovery_memory_rows(db_path)
    dashboard = discovery_learning_dashboard(db_path)

    trusted = [row for row in memory if row["memory_type"] == "trusted_domain"]
    assert result["signals_stored"] == 2
    assert any("bbb.org" in str(row["memory_key"]) for row in trusted)
    assert dashboard["runs_analysed"] == 1
    assert dashboard["acceptance_rate"] > 0


def test_provider_signals_store_evidence_class_and_tier_metadata(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)
    provider = StaticEvidenceProvider(
        [
            ProviderResult(
                "Tavily",
                "HUD tenant maintenance complaint",
                "https://www.hud.gov/tenant-maintenance-complaint",
                "Tenant complaint says apartment maintenance request had no response and repair communication was ignored.",
                "search_result",
            )
        ]
    )

    result = pull_real_market_evidence(db_path, providers=[provider], max_sources=1)
    signal = list_signals(db_path)[0]
    metadata = json.loads(signal["source_name"])

    assert result["signals_stored"] == 1
    assert metadata["evidence_class"] == "Regulator"
    assert metadata["evidence_tier"] == 1
    assert metadata["acquisition_strategy"] == "GS-P001"


def test_discovery_learning_tracks_evidence_class_performance(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)

    pull_real_market_evidence(db_path, providers=[QueryAwareEvidenceProvider()], max_sources=2)
    memory = discovery_memory_rows(db_path)
    dashboard = discovery_learning_dashboard(db_path)

    class_rows = [row for row in memory if row["memory_type"] == "evidence_class"]
    assert class_rows
    assert dashboard["evidence_classes"]
    assert any(int(row["accepted_count"] or 0) > 0 for row in class_rows)


def test_discovery_learning_stores_vendor_domains(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)

    pull_real_market_evidence(db_path, providers=[QueryAwareEvidenceProvider()], max_sources=2)
    memory = discovery_memory_rows(db_path)

    vendor_domains = [row for row in memory if row["memory_type"] == "vendor_domain"]
    assert any(row["memory_key"] == "vendor.example.com" for row in vendor_domains)


def test_discovery_learning_prioritises_high_yield_queries_and_deprioritises_low_yield(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)

    pull_real_market_evidence(db_path, providers=[QueryAwareEvidenceProvider()], max_sources=2)
    ordered_queries = [query for _, query in prioritized_query_runs(db_path)]
    memory = discovery_memory_rows(db_path)
    high_yield = [str(row["memory_key"]) for row in memory if row["memory_type"] == "high_yield_query"]
    low_yield = [str(row["memory_key"]) for row in memory if row["memory_type"] == "low_yield_query"]

    assert high_yield
    assert low_yield
    assert ordered_queries.index(high_yield[0]) < ordered_queries.index(low_yield[0])


def test_discovery_memory_does_not_override_evidence_quality_rules(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)
    pull_real_market_evidence(db_path, providers=[QueryAwareEvidenceProvider()], max_sources=2)
    before = len(list_signals(db_path))
    provider = StaticEvidenceProvider(
        [
            ProviderResult(
                "Tavily",
                "BBB property management background",
                "https://www.bbb.org/property-management-background",
                "Property management companies operate in many US rental markets with large apartment portfolios.",
                "search_result",
            )
        ]
    )

    result = pull_real_market_evidence(db_path, providers=[provider])

    assert result["signals_stored"] == 0
    assert len(list_signals(db_path)) == before
    assert result["skipped_market_size_generic_or_marketing"] + result["skipped_not_complaint_or_pain_evidence"] >= 1


def test_demo_runs_do_not_contaminate_production_discovery_memory(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    result = pull_real_market_evidence(db_path, providers=[QueryAwareEvidenceProvider()])

    assert result["status"] == "blocked"
    assert discovery_memory_rows(db_path) == []
    assert fetch_all(db_path, "discovery_runs") == []


def test_pull_real_market_evidence_skips_duplicate_url_and_raw_text(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)
    duplicate_text = "Property managers complain that maintenance communication tools do not show request status clearly."
    provider = StaticEvidenceProvider(
        [
            ProviderResult("Tavily", "Duplicate URL A", "https://example.com/duplicate", "Tenants complain that maintenance request updates are slow and unclear.", "search_result"),
            ProviderResult("Tavily", "Duplicate URL B", "https://example.com/duplicate", "Property managers complain that maintenance request updates are slow and tenants are not updated.", "search_result"),
            ProviderResult("Tavily", "Duplicate Text", "", duplicate_text, "search_result"),
            ProviderResult("Tavily", "Duplicate Text", "", duplicate_text, "search_result"),
        ]
    )

    result = pull_real_market_evidence(db_path, providers=[provider])

    assert result["signals_stored"] == 2
    assert result["skipped_duplicates"] == 2
    assert len([item for item in result["skipped"] if item["reason"] == "duplicate"]) == 2
    assert len(list_signals(db_path)) == 2


def test_openai_output_alone_cannot_create_production_evidence(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)

    result = pull_real_market_evidence(db_path, providers=[OpenAIOnlyEvidenceProvider()])

    assert result["status"] == "empty"
    assert result["signals_stored"] == 0
    assert result["skipped_openai_only"] >= 1
    assert any(item["reason"] == "openai_not_evidence" for item in result["skipped"])
    assert list_signals(db_path) == []


def test_market_size_article_is_skipped_as_production_signal(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)
    provider = StaticEvidenceProvider(
        [
            ProviderResult(
                "Tavily",
                "Property management market size forecast",
                "https://example.com/market-size",
                "The property management software market size is forecast to grow with a strong CAGR across multifamily portfolios.",
                "article",
            )
        ]
    )

    result = pull_real_market_evidence(db_path, providers=[provider])

    assert result["signals_stored"] == 0
    assert result["skipped_market_size_generic_or_marketing"] == 1
    assert list_signals(db_path) == []


def test_v2_vendor_blog_classifies_as_vendor_content():
    quality = evidence_quality_profile(
        "Our platform helps property managers streamline maintenance. Book a demo to learn about features.",
        url="https://vendor.example.com/blog/maintenance",
        title="Vendor maintenance blog",
    )

    assert quality["classification"] == "vendor_content"
    assert quality["evidence_classification"] == "vendor_content"
    assert quality["production_eligible"] is False
    assert quality["source_trust_score"] == 20


def test_oxmaint_page_classifies_as_vendor_content():
    quality = evidence_quality_profile(
        "Track and reduce property maintenance response times for tenants. Our platform automates work orders, tracks response times, and reduces legal risk.",
        url="https://oxmaint.com/industries/property-management/track-reduce-property-maintenance-response-times-2026",
        title="Track & Reduce Property Maintenance Response Times",
    )

    assert quality["classification"] == "vendor_content"
    assert quality["evidence_classification"] == "vendor_content"
    assert quality["evidence_relevance"] == "vendor_marketing"
    assert quality["source_type_detected"] == "vendor"
    assert quality["source_trust_score"] == 20
    assert quality["production_eligible"] is False
    assert quality["accepted_complaint_evidence"] is False
    assert quality["skip_reason"] == "market_size_generic_or_marketing"


def test_vendor_blog_with_tenant_complaints_is_not_production_eligible():
    quality = evidence_quality_profile(
        "Tenant complaints about delayed maintenance requests are common. Our software solution automates communication, includes features, and lets teams book a demo.",
        url="https://vendor.example.com/blog/tenant-maintenance-complaints",
        title="How our software solves tenant maintenance complaints",
    )

    assert quality["classification"] == "vendor_content"
    assert quality["production_eligible"] is False
    assert quality["accepted_complaint_evidence"] is False
    assert quality["source_type_detected"] == "vendor"


def test_v2_facebook_classifies_as_community_signal():
    quality = evidence_quality_profile(
        "Facebook group residents complain maintenance requests are ignored by the landlord.",
        url="https://facebook.com/groups/renters",
        title="Facebook tenant discussion",
    )

    assert quality["classification"] == "community_signal"
    assert quality["evidence_classification"] == "community_signal"
    assert quality["production_eligible"] is False
    assert quality["source_type_detected"] == "facebook_group"


def test_v2_market_statistics_classifies_as_market_context():
    quality = evidence_quality_profile(
        "The property management software market size forecast shows strong CAGR and industry investment.",
        url="https://example.com/market-report",
        title="Market size forecast",
    )

    assert quality["classification"] == "market_context"
    assert quality["evidence_classification"] == "market_context"
    assert quality["production_eligible"] is False


def test_v2_consumer_affairs_bbb_and_government_are_verified_complaints():
    examples = [
        ("https://www.consumeraffairs.com/property-management", "Consumer Affairs complaint", 95),
        ("https://www.bbb.org/us/example/property-management", "BBB complaint", 95),
        ("https://www.gov.example/tenant-complaints", "Government complaint portal", 100),
    ]

    for url, title, trust in examples:
        quality = evidence_quality_profile(
            "Tenant complaint says maintenance request had no response and apartment repair was delayed.",
            url=url,
            title=title,
        )
        assert quality["classification"] == "verified_complaint"
        assert quality["evidence_classification"] == "verified_complaint"
        assert quality["production_eligible"] is True
        assert quality["source_trust_score"] == trust


def test_px017_marketing_content_is_rejected_before_signal_creation(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)
    provider = StaticEvidenceProvider(
        [
            ProviderResult(
                "Tavily",
                "7 Essential Things To Know About Property Management",
                "https://example.com/property-management-guide",
                "This ultimate guide explains property management trends 2026, best companies, best software, and industry outlook.",
                "article",
            )
        ]
    )

    result = pull_real_market_evidence(db_path, providers=[provider])

    assert result["signals_stored"] == 0
    assert result["marketing_pages_rejected"] == 1
    assert result["skipped"][0]["candidate"]["classification"] == "marketing_content"
    assert result["skipped"][0]["candidate"]["classification_code"] == "MARKETING_CONTENT"
    assert result["skipped"][0]["candidate"]["rejection_reason"] == "Marketing / Promotional / Generic Industry Content."


def test_px017_government_investigation_gets_high_authority_and_structured_pain(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)
    provider = StaticEvidenceProvider(
        [
            ProviderResult(
                "Tavily",
                "Government investigation into landlord maintenance complaints",
                "https://housing.gov.example/investigation-maintenance-complaints",
                "Government investigation says tenants complain that apartment maintenance requests get no response, repairs remain unresolved, and residents are not updated.",
                "article",
            )
        ]
    )

    result = pull_real_market_evidence(db_path, providers=[provider])
    signal = list_signals(db_path)[0]
    metadata = json.loads(signal["source_name"])

    assert result["signals_stored"] == 1
    assert metadata["authority_score"] == 100
    assert metadata["operational_pain"]["what_pain"]
    assert metadata["operational_pain"]["business_impact"]
    assert metadata["operational_pain"]["root_cause"]


def test_px017_multiple_articles_about_same_event_do_not_approve_opportunity(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)
    provider = StaticEvidenceProvider(
        [
            ProviderResult("Tavily", "DOJ RealPage lawsuit maintenance complaint A", "https://news.example.com/a", "DOJ lawsuit against RealPage says tenants complain apartment maintenance requests had no response and repair communication was poor.", "article"),
            ProviderResult("Tavily", "DOJ RealPage lawsuit maintenance complaint B", "https://reuters.example.com/b", "DOJ lawsuit against RealPage says property managers complain maintenance request updates are delayed and tenants are not updated.", "article"),
            ProviderResult("Tavily", "DOJ RealPage lawsuit maintenance complaint C", "https://apnews.example.com/c", "DOJ lawsuit against RealPage says residents complain rental maintenance requests remain unresolved and repair updates are ignored.", "article"),
        ]
    )

    pull_real_market_evidence(db_path, providers=[provider])
    clusters = build_evidence_clusters(list_signals(db_path))

    assert clusters[0]["canonical_category"] == "Maintenance Communication Failure"
    assert clusters[0]["status"] == "Evidence Cluster - Needs More Evidence"
    assert generate_findings(db_path) == []
    assert approve_audited_opportunities(db_path) == []


def test_gs001_rejects_property_context_without_maintenance_pain():
    quality = evidence_quality_profile(
        "Government complaint alleges landlords shared rental pricing data and apartment market information.",
        url="https://www.federalregister.gov/documents/example-realpage",
        title="United States v RealPage proposed judgment",
    )

    assert quality["production_eligible"] is False
    assert quality["accepted_complaint_evidence"] is False
    assert quality["skip_reason"] == "not_complaint_or_pain_evidence"
    assert "maintenance" in quality["rejection_reason"].lower()


def test_needs_more_evidence_audit_does_not_create_opportunity(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)
    provider = StaticEvidenceProvider(
        [
            ProviderResult("Tavily", "Maintenance complaint A", "https://www.consumeraffairs.com/a", "Tenant complaint says maintenance request had no response and apartment repair was delayed.", "article"),
            ProviderResult("Tavily", "Maintenance complaint B", "https://www.bbb.org/b", "Property manager complaint says maintenance request updates are slow and tenants are not updated.", "article"),
            ProviderResult("Tavily", "Maintenance complaint C", "https://www.gov.example/c", "Resident complaint says rental maintenance request is unresolved and repair communication is poor.", "article"),
        ]
    )
    pull_real_market_evidence(db_path, providers=[provider])
    finding = generate_findings(db_path)[0]
    audit = audit_finding(db_path, finding["id"])

    assert audit["decision"] == "Needs More Evidence"
    assert approve_audited_opportunities(db_path) == []


def test_px018_housing_ombudsman_repair_communication_clusters_as_maintenance_communication(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)
    provider = StaticEvidenceProvider(
        [
            ProviderResult("Tavily", "Housing Ombudsman repair communication complaint", "https://www.housing-ombudsman.org.uk/case-a", "Resident complaint says the landlord failed to communicate during repairs and the tenant was not updated about maintenance work.", "article"),
            ProviderResult("Tavily", "Housing Ombudsman complaint handling failed", "https://www.bbb.org/case-b", "Tenant complaint says complaint handling failed after a maintenance repair took months and repair updates were unclear.", "article"),
            ProviderResult("Tavily", "Regulator emergency repair not explained", "https://www.gov.example/case-c", "Resident complaint says an emergency repair was not explained and the property manager failed to communicate maintenance status.", "article"),
        ]
    )
    pull_real_market_evidence(db_path, providers=[provider])
    clusters = build_evidence_clusters(list_signals(db_path))

    cluster = clusters[0]
    assert cluster["canonical_category"] == "Maintenance Communication Failure"
    assert cluster["status"] == "Draft finding ready"
    assert len(cluster["supporting_signal_ids"]) == 3


def test_px018_repair_months_not_updated_and_complaint_failed_cluster_together(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)
    provider = StaticEvidenceProvider(
        [
            ProviderResult("Tavily", "Repair took months", "https://www.consumeraffairs.com/repair-months", "Tenant complaint says the apartment maintenance repair took months and the resident had no repair updates.", "article"),
            ProviderResult("Tavily", "Resident not updated", "https://www.bbb.org/not-updated", "Resident complaint says the property manager failed to communicate and the tenant was not updated about maintenance work.", "article"),
            ProviderResult("Tavily", "Complaint handling failed", "https://www.gov.example/complaint-failed", "Government complaint says complaint handling failed after maintenance repairs and follow-up were ignored.", "article"),
        ]
    )
    pull_real_market_evidence(db_path, providers=[provider])
    clusters = build_evidence_clusters(list_signals(db_path))

    assert len([cluster for cluster in clusters if cluster["canonical_category"] == "Maintenance Communication Failure"]) == 1
    assert clusters[0]["canonical_category"] == "Maintenance Communication Failure"
    assert len(clusters[0]["supporting_signal_ids"]) == 3


def test_px018_accounting_payment_signals_are_out_of_scope_without_maintenance():
    signal = {
        "source_url": "https://www.bbb.org/payment-complaint",
        "source_name": "BBB payment complaint",
        "raw_text": "Tenant complaint says rent payment accounting and invoice arrears were handled poorly by the property manager.",
        "summary": "Payment accounting complaint",
        "stakeholder_type": "Tenants",
        "complaint_category": "Accounting / payment issues",
        "data_origin": "provider",
        "is_demo": 0,
    }

    category = canonical_pain_category(signal)

    assert is_signal_in_gs001_scope(signal) is False
    assert category["scope_status"] in {"context_only", "out_of_scope"}


def test_px018_market_trend_articles_do_not_become_findings(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)
    provider = StaticEvidenceProvider(
        [
            ProviderResult("Tavily", "Property Management Trends 2026", "https://example.com/trends", "Property management trends 2026 market outlook and best software guide for residential investors.", "article"),
        ]
    )
    pull_real_market_evidence(db_path, providers=[provider])

    assert build_evidence_clusters(list_signals(db_path)) == []
    assert generate_findings(db_path) == []


def test_px018_vendor_pages_do_not_create_eligible_clusters(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)
    provider = StaticEvidenceProvider(
        [
            ProviderResult("Tavily", "Our maintenance communication platform", "https://vendor.example.com/features", "Our platform automates maintenance repair updates. Book a demo for features and pricing.", "article"),
        ]
    )
    pull_real_market_evidence(db_path, providers=[provider])

    assert build_evidence_clusters(list_signals(db_path)) == []
    assert generate_findings(db_path) == []


def test_px018_three_signals_from_one_domain_need_more_evidence(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)
    provider = StaticEvidenceProvider(
        [
            ProviderResult("Tavily", "Maintenance complaint A", "https://www.housing-ombudsman.org.uk/a", "Resident complaint says landlord failed to communicate repair updates for maintenance work.", "article"),
            ProviderResult("Tavily", "Maintenance complaint B", "https://www.housing-ombudsman.org.uk/b", "Tenant complaint says no repair updates were provided and maintenance follow-up was poor.", "article"),
            ProviderResult("Tavily", "Maintenance complaint C", "https://www.housing-ombudsman.org.uk/c", "Resident complaint says complaint handling failed and repairs took months without updates.", "article"),
        ]
    )
    pull_real_market_evidence(db_path, providers=[provider])
    clusters = build_evidence_clusters(list_signals(db_path))

    assert clusters[0]["status"] == "Evidence Cluster - Needs More Evidence"
    assert "independent domains" in clusters[0]["why"]
    assert generate_findings(db_path) == []


def test_px018_independent_trusted_sources_create_semantic_finding(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)
    provider = StaticEvidenceProvider(
        [
            ProviderResult("Tavily", "Maintenance complaint A", "https://www.housing-ombudsman.org.uk/a", "Resident complaint says landlord failed to communicate repair updates for maintenance work.", "article"),
            ProviderResult("Tavily", "Maintenance complaint B", "https://www.bbb.org/b", "Tenant complaint says no repair updates were provided and maintenance follow-up was poor.", "article"),
            ProviderResult("Tavily", "Maintenance complaint C", "https://www.gov.example/c", "Resident complaint says complaint handling failed and repairs took months without updates.", "article"),
        ]
    )
    pull_real_market_evidence(db_path, providers=[provider])

    findings = generate_findings(db_path)
    cluster = finding_cluster_metadata(findings[0])

    assert len(findings) == 1
    assert findings[0]["theme"] == "Maintenance Communication Failure"
    assert cluster["canonical_category"] == "Maintenance Communication Failure"
    assert len(cluster["supporting_signal_ids"]) == 3


def test_px018_generate_findings_feedback_mentions_clusters_when_thresholds_fail(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)
    provider = StaticEvidenceProvider(
        [
            ProviderResult("Tavily", "Maintenance complaint A", "https://www.housing-ombudsman.org.uk/a", "Resident complaint says landlord failed to communicate repair updates for maintenance work.", "article"),
        ]
    )
    pull_real_market_evidence(db_path, providers=[provider])

    level, message = findings_feedback(generate_findings(db_path))

    assert level == "warning"
    assert message == "Evidence clusters reviewed. No production finding created because thresholds were not met."


def test_px018_finding_evidence_chain_includes_cluster(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)
    provider = StaticEvidenceProvider(
        [
            ProviderResult("Tavily", "Maintenance complaint A", "https://www.housing-ombudsman.org.uk/a", "Resident complaint says landlord failed to communicate repair updates for maintenance work.", "article"),
            ProviderResult("Tavily", "Maintenance complaint B", "https://www.bbb.org/b", "Tenant complaint says no repair updates were provided and maintenance follow-up was poor.", "article"),
            ProviderResult("Tavily", "Maintenance complaint C", "https://www.gov.example/c", "Resident complaint says complaint handling failed and repairs took months without updates.", "article"),
        ]
    )
    pull_real_market_evidence(db_path, providers=[provider])
    finding = generate_findings(db_path)[0]
    chain = finding_evidence(db_path, finding["id"])

    assert chain["evidence_cluster"]["canonical_category"] == "Maintenance Communication Failure"
    assert chain["evidence_cluster"]["supporting_signal_ids"]
    assert chain["signals"]


def test_vendor_marketing_page_is_skipped_as_production_signal(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)
    provider = StaticEvidenceProvider(
        [
            ProviderResult(
                "SerpAPI",
                "Our property management software features",
                "https://vendor.example.com/features",
                "Our platform helps property managers streamline maintenance workflows. Book a demo to learn about features.",
                "article",
            )
        ]
    )

    result = pull_real_market_evidence(db_path, providers=[provider])

    assert result["signals_stored"] == 0
    assert result["skipped_market_size_generic_or_marketing"] == 1


def test_generic_property_management_article_is_skipped_as_production_signal(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)
    provider = StaticEvidenceProvider(
        [
            ProviderResult(
                "NewsAPI",
                "Guide to property management maintenance",
                "https://example.com/property-guide",
                "This article is an overview of property management maintenance best practices for apartment teams.",
                "article",
            )
        ]
    )

    result = pull_real_market_evidence(db_path, providers=[provider])

    assert result["signals_stored"] == 0
    assert result["skipped_market_size_generic_or_marketing"] == 1


def test_tenant_maintenance_no_response_complaint_is_accepted(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)
    provider = StaticEvidenceProvider(
        [
            ProviderResult(
                "Tavily",
                "Tenant complaint about maintenance no response",
                "https://example.com/tenant-no-response",
                "Tenant complaint says a maintenance request had no response, the repair was delayed, and the apartment resident was not updated.",
                "article",
            )
        ]
    )

    result = pull_real_market_evidence(db_path, providers=[provider])
    signal = list_signals(db_path)[0]
    view = signal_trace_card_view_model(signal)

    assert result["signals_stored"] == 1
    assert view["evidence_relevance"] == "complaint"
    assert "complaint" in view["pain_keywords_matched"]
    assert "tenant" in view["context_keywords_matched"]


def test_production_finding_requires_three_accepted_signals(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)
    two_signal_provider = StaticEvidenceProvider(
        [
            ProviderResult("Tavily", "Tenant complaint A", "https://a.example.com/a", "Tenant complaint says maintenance request had no response and apartment repair was delayed.", "article"),
            ProviderResult("Tavily", "Tenant complaint B", "https://b.example.com/b", "Property manager complaint says maintenance request updates are slow and tenants are not updated.", "article"),
        ]
    )
    pull_real_market_evidence(db_path, providers=[two_signal_provider])

    assert generate_findings(db_path) == []

    third_signal_provider = StaticEvidenceProvider(
        [
            ProviderResult("Tavily", "Tenant complaint C", "https://c.example.com/c", "Resident complaint says rental maintenance request is unresolved and repair communication is poor.", "article"),
        ]
    )
    pull_real_market_evidence(db_path, providers=[third_signal_provider])

    findings = generate_findings(db_path)
    assert len(findings) == 1
    assert findings[0]["status"] == "pending_audit"
    assert findings[0]["signal_count"] == 3


def test_audit_cannot_approve_from_weak_generic_evidence(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)
    provider = StaticEvidenceProvider(
        [
            ProviderResult("Tavily", "Generic A", "https://a.example.com/a", "This article is an overview of property management maintenance for apartment teams.", "article"),
            ProviderResult("Tavily", "Generic B", "https://b.example.com/b", "This guide explains property management repair coordination best practices.", "article"),
            ProviderResult("Tavily", "Generic C", "https://c.example.com/c", "This property management article covers general maintenance planning.", "article"),
        ]
    )
    pull_real_market_evidence(db_path, providers=[provider])

    assert list_signals(db_path) == []
    assert generate_findings(db_path) == []


def test_audit_requires_full_opportunity_qualification_threshold(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)
    provider = StaticEvidenceProvider(
        [
            ProviderResult("Tavily", "Tenant complaint A", "https://www.consumeraffairs.com/a", "Tenant complaint says maintenance request had no response and apartment repair was delayed.", "article"),
            ProviderResult("Tavily", "Tenant complaint B", "https://www.bbb.org/b", "Property manager complaint says maintenance request updates are slow and tenants are not updated.", "article"),
            ProviderResult("Tavily", "Resident complaint C", "https://www.gov.example/c", "Resident complaint says rental maintenance request is unresolved and repair communication is poor.", "article"),
        ]
    )
    pull_real_market_evidence(db_path, providers=[provider])
    finding = generate_findings(db_path)[0]

    audit = audit_finding(db_path, finding["id"])

    assert audit["decision"] == "Needs More Evidence"
    assert "Minimum independent sources not met" in audit["missing_evidence_warnings"]
    assert "Minimum independent market events not met" in audit["missing_evidence_warnings"]


def test_opportunity_cannot_exist_without_minimum_trust_score(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)
    provider = StaticEvidenceProvider(
        [
            ProviderResult("Tavily", "Tenant complaint A", "https://forum-a.example.com/a", "Tenant complaint says maintenance request had no response and apartment repair was delayed.", "article"),
            ProviderResult("Tavily", "Tenant complaint B", "https://forum-b.example.com/b", "Property manager complaint says maintenance request updates are slow and tenants are not updated.", "article"),
            ProviderResult("Tavily", "Resident complaint C", "https://forum-c.example.com/c", "Resident complaint says rental maintenance request is unresolved and repair communication is poor.", "article"),
        ]
    )
    pull_real_market_evidence(db_path, providers=[provider])
    finding = generate_findings(db_path)[0]

    audit = audit_finding(db_path, finding["id"])

    assert audit["decision"] == "Needs More Evidence"
    assert "Evidence score below threshold" in audit["missing_evidence_warnings"]
    assert "Minimum independent sources not met" in audit["missing_evidence_warnings"]


def test_opportunity_cannot_exist_without_minimum_independent_domains(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)
    provider = StaticEvidenceProvider(
        [
            ProviderResult("Tavily", "Consumer complaint A", "https://www.consumeraffairs.com/a", "Tenant complaint says maintenance request had no response and apartment repair was delayed.", "article"),
            ProviderResult("Tavily", "Consumer complaint B", "https://www.consumeraffairs.com/b", "Property manager complaint says maintenance request updates are slow and tenants are not updated.", "article"),
            ProviderResult("Tavily", "Consumer complaint C", "https://www.consumeraffairs.com/c", "Resident complaint says rental maintenance request is unresolved and repair communication is poor.", "article"),
        ]
    )
    pull_real_market_evidence(db_path, providers=[provider])
    clusters = build_evidence_clusters(list_signals(db_path))

    assert clusters[0]["status"] == "Evidence Cluster - Needs More Evidence"
    assert "independent domains" in clusters[0]["why"]
    assert generate_findings(db_path) == []


def test_opportunity_cannot_exist_without_minimum_verified_complaint_threshold(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)
    provider = StaticEvidenceProvider(
        [
            ProviderResult("Tavily", "Consumer complaint A", "https://www.consumeraffairs.com/a", "Tenant complaint says maintenance request had no response and apartment repair was delayed.", "article"),
            ProviderResult("Tavily", "BBB complaint B", "https://www.bbb.org/b", "Property manager complaint says maintenance request updates are slow and tenants are not updated.", "article"),
        ]
    )
    pull_real_market_evidence(db_path, providers=[provider])

    assert generate_findings(db_path) == []


def test_archive_current_production_run_preserves_records_and_starts_empty_run(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    old_run = start_production_run(db_path)
    provider = StaticEvidenceProvider(
        [
            ProviderResult("Tavily", "Tenant complaint A", "https://www.consumeraffairs.com/a", "Tenant complaint says maintenance request had no response and apartment repair was delayed.", "article"),
            ProviderResult("Tavily", "Tenant complaint B", "https://www.bbb.org/b", "Property manager complaint says maintenance request updates are slow and tenants are not updated.", "article"),
            ProviderResult("Tavily", "Resident complaint C", "https://www.gov.example/c", "Resident complaint says rental maintenance request is unresolved and repair communication is poor.", "article"),
        ]
    )
    pull_real_market_evidence(db_path, providers=[provider])
    finding = generate_findings(db_path)[0]
    audit = audit_finding(db_path, finding["id"])
    run_before = study_progress(db_path)

    result = archive_current_production_run_and_start_fresh(db_path)
    run_after = study_progress(db_path)
    archived_signals = list_signals(db_path, study_run_id=old_run["id"], include_archived=True)

    assert result["message"] == "Current production run archived. New clean production run started."
    assert result["new_run_id"] != old_run["id"]
    assert run_before["signals_collected"] == 3
    assert run_after["signals_collected"] == 0
    assert run_after["findings_created"] == 0
    assert run_after["audits_completed"] == 0
    assert len(archived_signals) == 3
    assert all(signal["status"] == "archived" for signal in archived_signals)
    archived_evidence = finding_evidence(db_path, finding["id"], include_archived=True)
    assert audit["decision"] == "Needs More Evidence"
    assert archived_evidence["signals"]


def test_production_pull_needs_no_manual_form_and_updates_mission_control_counts(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    production_run = start_production_run(db_path)
    provider = StaticEvidenceProvider(
        [
            ProviderResult(
                "Tavily",
                "US renters report maintenance update gaps",
                "https://example.com/us-renters-maintenance",
                "US renters complain that apartment maintenance updates are unclear and property managers leave repair timelines unresolved.",
                "article",
            ),
            ProviderResult(
                "Tavily",
                "Property managers cite maintenance communication load",
                "https://example.com/property-manager-maintenance-load",
                "Property managers complain that maintenance communication is slow, fragmented across email, and tenant repair updates are delayed.",
                "article",
            ),
        ]
    )

    result = pull_real_market_evidence(db_path, providers=[provider])
    progress = study_progress(db_path)
    pipeline = production_pipeline_statuses(progress)

    assert result["status"] == "completed"
    assert result["signals_stored"] == 2
    assert result["active_run_id"] == production_run["id"]
    assert progress["signals_collected"] == 2
    assert progress["verification_pending_count"] == 2
    assert progress["countries_covered"] == ["United States"]
    assert pipeline["Evidence Collection"] == "Completed"
    assert pipeline["Signal Detection"] == "Completed"
    assert pipeline["Finding Generation"] == "Active"
    assert pipeline["Audit"] == "Locked"
    for signal in list_signals(db_path):
        assert signal["verification_status"] == "pending_verification"
        assert signal["is_demo"] == 0
        assert signal["data_origin"] == "provider"
        metadata = json.loads(signal["source_name"])
        assert metadata["provider_name"] == "Tavily"
        assert metadata["original_query"]
        assert metadata["retrieved_at"]
        assert metadata["original_title"]


def test_production_pipeline_unlocks_only_after_required_records(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)

    empty_pipeline = production_pipeline_statuses(study_progress(db_path))
    assert empty_pipeline["Evidence Collection"] == "Active"
    assert empty_pipeline["Signal Detection"] == "Locked"
    assert empty_pipeline["Finding Generation"] == "Locked"
    assert empty_pipeline["Audit"] == "Locked"
    assert empty_pipeline["Opportunity"] == "Locked"

    provider = StaticEvidenceProvider(
        [
            ProviderResult("Tavily", "Signal A", "https://example.com/a", "Tenants complain maintenance communication updates are unclear.", "article"),
            ProviderResult("Tavily", "Signal B", "https://example.com/b", "Property managers complain maintenance communication updates require repeated manual chasing.", "article"),
        ]
    )
    pull_real_market_evidence(db_path, providers=[provider])
    signal_pipeline = production_pipeline_statuses(study_progress(db_path))
    assert signal_pipeline["Signal Detection"] == "Completed"
    assert signal_pipeline["Finding Generation"] == "Active"
    assert signal_pipeline["Audit"] == "Locked"

    generate_findings(db_path)
    finding_pipeline = production_pipeline_statuses(study_progress(db_path))
    assert finding_pipeline["Finding Generation"] == "Active"
    assert finding_pipeline["Audit"] == "Locked"

    third_provider = StaticEvidenceProvider(
        [
            ProviderResult("Tavily", "Signal C", "https://example.com/c", "Residents complain rental maintenance request updates are delayed and repair communication is poor.", "article"),
        ]
    )
    pull_real_market_evidence(db_path, providers=[third_provider])
    generate_findings(db_path)
    finding_pipeline = production_pipeline_statuses(study_progress(db_path))
    assert finding_pipeline["Finding Generation"] == "Active"
    assert finding_pipeline["Audit"] == "Locked"
    assert finding_pipeline["Opportunity"] == "Locked"


def test_signal_trace_card_view_model_uses_source_url_when_source_name_missing():
    signal = {
        "source_url": "https://example.com/provider-signal",
        "provider_name": "Tavily",
        "query": "maintenance communication",
        "source_date": "2026-07-01T20:00:00Z",
        "raw_text": "Tenants complain that maintenance updates are unclear.",
        "verification_status": "pending_verification",
    }

    view = signal_trace_card_view_model(signal)

    assert view["source_name"] == "https://example.com/provider-signal"
    assert view["provider"] == "Tavily"
    assert view["query"] == "maintenance communication"
    assert view["retrieved"] == "2026-07-01T20:00:00Z"
    assert view["raw_text"].startswith("Tenants complain")


def test_signal_trace_card_view_model_handles_none_source_name():
    signal = {
        "source_name": None,
        "source_url": "",
        "raw_text": None,
        "summary": "Provider signal summary",
    }

    view = signal_trace_card_view_model(signal)

    assert view["source_name"] == "Unknown source"
    assert view["provider"] == "Unknown provider"
    assert view["query"] == "Not recorded"
    assert view["retrieved"] == "Not recorded"
    assert view["raw_text"] == "Provider signal summary"


def test_signals_page_card_model_handles_provider_signal_after_pull(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)
    provider = StaticEvidenceProvider(
        [
            ProviderResult(
                "Tavily",
                "Maintenance communication source",
                "https://example.com/maintenance-source",
                "Property managers complain that maintenance communication is too manual and hard to track.",
                "article",
            )
        ]
    )

    result = pull_real_market_evidence(db_path, providers=[provider])
    signal = list_signals(db_path)[0]
    view = signal_trace_card_view_model(signal)

    assert result["signals_stored"] == 1
    assert view["source_name"] == "Maintenance communication source"
    assert view["provider"] == "Tavily"
    assert view["source_url"] == "https://example.com/maintenance-source"
    assert view["verification_status"] == "pending_verification"
    assert view["retrieved"] != "Not recorded"


def test_provider_signal_view_model_hides_raw_source_name_json(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)
    provider = StaticEvidenceProvider(
        [
            ProviderResult(
                "Tavily",
                "Readable complaint title",
                "https://www.consumeraffairs.com/readable",
                "Tenant complaint says maintenance request had no response and apartment repair was delayed.",
                "article",
            )
        ]
    )

    pull_real_market_evidence(db_path, providers=[provider])
    signal = list_signals(db_path)[0]
    view = signal_trace_card_view_model(signal)

    assert str(signal["source_name"]).startswith("{")
    assert view["source_name"] == "Readable complaint title"


def test_demo_rehearsal_can_reach_demo_engineering_ready(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    run_research_batch(
        db_path,
        [
            {"source_name": "Demo A", "data_origin": "demo", "raw_text": "Property managers repeatedly complain maintenance updates are slow."},
            {"source_name": "Demo B", "data_origin": "demo", "raw_text": "Tenants repeatedly complain maintenance updates are slow."},
        ],
    )
    finding = list_findings(db_path, include_demo=True)[0]
    audits = run_audit_batch(db_path)
    opportunities = approve_audited_opportunities(db_path)
    ready = mark_engineering_ready(
        db_path,
        opportunities[0]["id"],
        {
            "recommended_component": "Demo Component",
            "engineering_recommendation": "Demo recommendation",
            "problem_scope": "Demo scope",
            "target_users": "Demo users",
            "required_inputs": "Demo inputs",
            "expected_outputs": "Demo outputs",
            "system_boundaries": "Demo boundaries",
        },
    )

    assert finding["status"] == "Demo Finding"
    assert audits[0]["decision"] == "Demo Audited"
    assert opportunities[0]["status"] == "Demo Opportunity"
    assert ready["status"] == "Demo Engineering Ready"
    assert ready["engineering_status"] == "Demo Engineering Ready"
    assert ready["is_demo"] == 1
    assert ready["data_origin"] == "demo"
    assert ready["verification_status"] == "unverified"

    start_production_run(db_path)
    production_progress = study_progress(db_path)
    assert production_progress["signals_collected"] == 0
    assert production_progress["engineering_ready"] == []
    assert production_progress["average_oci"] == 0


def test_demo_audit_batch_upgrades_legacy_insufficient_finding(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    run_research_batch(
        db_path,
        [
            {"source_name": "Demo A", "data_origin": "demo", "raw_text": "Property managers repeatedly complain maintenance updates are slow."},
            {"source_name": "Demo B", "data_origin": "demo", "raw_text": "Tenants repeatedly complain maintenance updates are slow."},
        ],
    )
    finding = list_findings(db_path, include_demo=True)[0]
    with connect(db_path) as connection:
        connection.execute("UPDATE study_findings SET status = 'Insufficient Evidence' WHERE id = ?", (finding["id"],))

    audits = run_audit_batch(db_path)
    refreshed = list_findings(db_path, include_demo=True)[0]

    assert audits
    assert audits[0]["status"] == "Demo Audited"
    assert refreshed["status"] == "Demo Audited"


def test_generate_findings_feedback_messages(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    level, message = findings_feedback(generate_findings(db_path))
    assert level == "warning"
    assert message == "Evidence clusters reviewed. No production finding created because thresholds were not met."

    run_research_batch(
        db_path,
        [
            {"source_name": "Demo A", "data_origin": "demo", "raw_text": "Property managers repeatedly complain maintenance updates are slow."},
            {"source_name": "Demo B", "data_origin": "demo", "raw_text": "Tenants repeatedly complain maintenance updates are slow."},
        ],
    )
    level, message = findings_feedback(generate_findings(db_path))
    assert level == "success"
    assert message.endswith("findings generated")


def test_audit_batch_demo_feedback_is_clear(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    run_research_batch(
        db_path,
        [
            {"source_name": "Demo A", "data_origin": "demo", "raw_text": "Property managers repeatedly complain maintenance updates are slow."},
            {"source_name": "Demo B", "data_origin": "demo", "raw_text": "Tenants repeatedly complain maintenance updates are slow."},
        ],
    )
    findings = list_findings(db_path, include_demo=True)
    audits = run_audit_batch(db_path)
    level, message = audit_batch_feedback(audits, findings)
    approval_level, approval_message = approval_feedback(approve_audited_opportunities(db_path), demo_present=True)

    assert audits
    assert audits[0]["status"] == "Demo Audited"
    assert level == "success"
    assert message.endswith("audits completed")
    assert approval_level == "success"
    assert approval_message.endswith("demo opportunities created")


def test_production_action_feedback_can_proceed_normally(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)
    start_production_run(db_path)

    batch = run_research_batch(
        db_path,
        [
            {
                "country": "Ireland",
                "stakeholder_type": "Property managers",
                "source_url": "https://www.consumeraffairs.com/property-management/irish",
                "source_name": "Consumer Affairs Irish complaint",
                "data_origin": "verified_import",
                "raw_text": "Property managers in Ireland repeatedly complain that maintenance updates are slow and tenants chase responses multiple times.",
            },
            {
                "country": "United Kingdom",
                "stakeholder_type": "Tenants",
                "source_url": "https://www.bbb.org/property-management/uk",
                "source_name": "BBB UK complaint",
                "data_origin": "verified_import",
                "raw_text": "Tenants in the United Kingdom repeatedly complain that repair communication is poor and maintenance updates are delayed.",
            },
            {
                "country": "United States",
                "stakeholder_type": "Property owners",
                "source_url": "https://www.gov.example/property-management/us",
                "source_name": "Government US complaint",
                "data_origin": "verified_import",
                "raw_text": "Property owners in the United States repeatedly complain that maintenance coordination is manual, slow, and expensive.",
            },
        ],
    )
    findings_level, findings_message = findings_feedback(batch["findings"])
    audits = run_audit_batch(db_path)
    audit_level, audit_message = audit_batch_feedback(audits, list_findings(db_path))
    opportunities = approve_audited_opportunities(db_path)
    approval_level, approval_message = approval_feedback(opportunities)

    assert findings_level == "success"
    assert findings_message.endswith("findings generated")
    assert audit_level == "success"
    assert audit_message.endswith("audits completed")
    assert approval_level == "warning"
    assert approval_message == "No approved opportunities available"
    assert opportunities == []
