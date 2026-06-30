from project_exchange.database import connect, fetch_all, init_db, utc_now
from project_exchange.golden_study import (
    DEFAULT_STUDY_ID,
    approve_audited_opportunities,
    archive_record,
    audit_finding,
    calculate_oci,
    create_signal,
    create_study,
    generate_executive_brief,
    generate_findings,
    get_active_study_run,
    get_or_create_default_study,
    list_signals,
    list_study_runs,
    list_opportunities,
    switch_study_run_mode,
    run_audit_batch,
    run_research_batch,
    study_progress,
    traceability_chain,
    validate_golden_study_integrity,
)


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

    findings = generate_findings(db_path)
    assert findings
    assert findings[0]["signal_count"] == 2
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
                "source_name": "Irish source",
                "data_origin": "verified_import",
                "raw_text": "Property managers in Ireland repeatedly complain that maintenance updates are slow and tenants chase responses multiple times.",
            },
            {
                "country": "United Kingdom",
                "stakeholder_type": "Tenants",
                "source_name": "UK source",
                "data_origin": "verified_import",
                "raw_text": "Tenants in the United Kingdom repeatedly complain that repair communication is poor and maintenance updates are delayed.",
            },
            {
                "country": "United States",
                "stakeholder_type": "Property owners",
                "source_name": "US source",
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
    assert opportunities
    opportunity = opportunities[0]
    assert opportunity["engineering_status"] == "Engineering Specification Required"
    assert opportunity["status"] == "Approved Opportunity"

    chain = traceability_chain(db_path, opportunity["id"])
    assert chain["opportunity"]["id"] == opportunity["id"]
    assert chain["audit"]["id"] == opportunity["audit_id"]
    assert chain["finding"]["id"] == opportunity["finding_id"]
    assert len(chain["signals"]) >= 2
    assert chain["sources"]


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

    create_signal(db_path, "Property managers repeatedly complain about expensive software pricing and missing integrations.", source_name="A", data_origin="verified_import")
    create_signal(db_path, "Letting agents complain about expensive software pricing and missing integrations in property tools.", source_name="B", data_origin="verified_import")
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

    create_signal(db_path, "Real evidence starts the production run.", source_name="Real source", data_origin="manual")
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
    assert finding["status"] == "Insufficient Evidence"

    try:
        audit_finding(db_path, finding["id"])
    except ValueError as exc:
        assert "not auditable" in str(exc)
    else:
        raise AssertionError("Demo finding should not be auditable")


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
                "source_name": "Irish source",
                "data_origin": "verified_import",
                "raw_text": "Property managers in Ireland repeatedly complain that maintenance updates are slow and tenants chase responses multiple times.",
            },
            {
                "country": "United Kingdom",
                "stakeholder_type": "Tenants",
                "source_name": "UK source",
                "data_origin": "verified_import",
                "raw_text": "Tenants in the United Kingdom repeatedly complain that repair communication is poor and maintenance updates are delayed.",
            },
        ],
    )

    production_progress = study_progress(db_path)
    demo_history_progress = study_progress(db_path, study_run_id=demo_run["id"], include_archived=True, include_demo=True)

    assert production_progress["active_run_id"] == production_run["id"]
    assert production_progress["signals_collected"] == 2
    assert production_progress["findings_created"] == 1
    assert production_progress["demo_records_count"] == 0
    assert demo_history_progress["signals_collected"] == 1


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
