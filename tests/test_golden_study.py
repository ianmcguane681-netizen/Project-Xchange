from project_exchange.database import fetch_all, init_db
from project_exchange.golden_study import (
    DEFAULT_STUDY_ID,
    archive_record,
    audit_finding,
    calculate_oci,
    create_signal,
    generate_executive_brief,
    generate_findings,
    get_or_create_default_study,
    list_opportunities,
    promote_approved_opportunities,
    run_audit_batch,
    run_research_batch,
    study_progress,
    traceability_chain,
)


def test_default_study_creation(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    study = get_or_create_default_study(db_path)
    assert study["id"] == DEFAULT_STUDY_ID
    assert study["market"] == "Property Management"
    assert study["status"] == "Active"


def test_signal_creation_and_finding_clustering(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

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


def test_audit_promotion_and_traceability_chain(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

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

    opportunities = promote_approved_opportunities(db_path)
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

    create_signal(db_path, "Property managers repeatedly complain about expensive software pricing and missing integrations.", source_name="A", data_origin="verified_import")
    create_signal(db_path, "Letting agents complain about expensive software pricing and missing integrations in property tools.", source_name="B", data_origin="verified_import")
    finding = generate_findings(db_path)[0]
    audit = audit_finding(db_path, finding["id"])

    assert audit["decision"] in {"Approve Opportunity", "Needs More Evidence", "Reject"}
    assert audit["reasoning_summary"]
    assert fetch_all(db_path, "finding_audits")
    assert list_opportunities(db_path) == []


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
