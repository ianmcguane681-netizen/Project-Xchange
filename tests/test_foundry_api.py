from __future__ import annotations

import pytest

from project_exchange.database import init_db
from project_exchange.foundry_api import (
    blueprints_payload,
    create_app,
    discovery_payload,
    due_diligence_payload,
    intelligence_payload,
    mission_control_payload,
    sanitize_for_foundry,
    schema_examples,
    verification_payload,
)
from project_exchange.golden_study import DEFAULT_STUDY_ID, create_signal, switch_study_run_mode


def seeded_db(tmp_path):
    db_path = tmp_path / "foundry.db"
    init_db(db_path)
    switch_study_run_mode(db_path, DEFAULT_STUDY_ID, "production", production_confirmed=True)
    create_signal(
        db_path,
        "Tenant complaint says apartment maintenance request had no response and repair communication was delayed.",
        DEFAULT_STUDY_ID,
        "https://www.bbb.org/us/example/property-management-complaint",
        "BBB property management complaint",
        "complaint",
        "2026-07-04",
        "United States",
        "Tenant",
        "Example Property Management",
        "manual",
    )
    return db_path


def test_foundry_mission_control_payload(tmp_path):
    payload = mission_control_payload(seeded_db(tmp_path))

    assert payload["question"] == "What decision should we make next?"
    assert payload["current_run"]["study_mode"] == "production"
    assert payload["stage"] in {"Verification", "Intelligence", "Executive Due Diligence", "Blueprint Studio", "Component Warehouse"}
    assert payload["production_evidence_count"] >= 1
    assert payload["read_only"] is True


def test_foundry_discovery_payload(tmp_path):
    payload = discovery_payload(seeded_db(tmp_path))

    assert payload["question"] == "What did we find?"
    assert "configured_sources" in payload
    assert "source_health" in payload
    assert "latest_evidence_pulls" in payload


def test_foundry_verification_payload_has_three_layer_cards(tmp_path):
    payload = verification_payload(seeded_db(tmp_path))

    assert payload["question"] == "Can we trust it?"
    card = payload["accepted_production_evidence"][0]
    assert card["executive_summary"]
    assert card["decision"]["authority"] == "PASS"
    assert card["decision"]["traceability"] == "PASS"
    assert card["detail"]["source_url"].startswith("https://")
    assert "raw_record" in card["detail"]


def test_foundry_intelligence_payload(tmp_path):
    payload = intelligence_payload(seeded_db(tmp_path))

    assert payload["question"] == "What pattern exists?"
    assert "evidence_clusters" in payload
    assert "entities" in payload
    assert "geographic_spread" in payload
    assert payload["commercial_relevance"]["accepted_production_signals"] >= 1


def test_foundry_due_diligence_payload(tmp_path):
    payload = due_diligence_payload(seeded_db(tmp_path))

    assert payload["question"] == "Should we build software?"
    assert "scorecard" in payload
    assert "blockers" in payload
    assert "why_blocked" in payload


def test_foundry_blueprints_payload(tmp_path):
    payload = blueprints_payload(seeded_db(tmp_path))

    assert payload["question"] == "What are we building?"
    assert "generated_briefs" in payload
    assert "software_blueprints" in payload
    assert payload["component_warehouse"]["question"] == "What have we already built?"


def test_foundry_sanitizer_removes_secrets():
    payload = sanitize_for_foundry({"api_key": "secret", "nested": {"token": "secret", "safe": "ok"}})

    assert "api_key" not in payload
    assert "token" not in payload["nested"]
    assert payload["nested"]["safe"] == "ok"


def test_foundry_schema_examples_exist():
    examples = schema_examples()

    assert "/api/foundry/mission-control" in examples
    assert "/api/foundry/verification" in examples


def test_foundry_fastapi_endpoints_if_available(tmp_path):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    client = TestClient(create_app(seeded_db(tmp_path)))
    for route in [
        "/api/foundry/mission-control",
        "/api/foundry/discovery",
        "/api/foundry/verification",
        "/api/foundry/intelligence",
        "/api/foundry/due-diligence",
        "/api/foundry/blueprints",
    ]:
        response = client.get(route)
        assert response.status_code == 200
        assert response.json()["read_only"] is True
