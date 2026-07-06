from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from project_exchange.database import DEFAULT_DB_PATH, fetch_all, init_db
from project_exchange.golden_study import (
    DEFAULT_STUDY_ID,
    build_evidence_clusters,
    data_source_health_dashboard,
    discovery_learning_dashboard,
    evidence_quality_dashboard,
    get_active_study_run,
    get_or_create_default_study,
    list_evidence_sources,
    list_finding_audits,
    list_findings,
    list_opportunities,
    list_signals,
    list_study_briefs,
    production_pipeline_statuses,
    signal_trace_card_view_model,
    study_progress,
)
from project_exchange.operators import provena_operator_registry

SECRET_FIELD_MARKERS = ("api_key", "apikey", "secret", "token", "password", "authorization")


def sanitize_for_foundry(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if any(marker in key_text.lower() for marker in SECRET_FIELD_MARKERS):
                continue
            sanitized[key_text] = sanitize_for_foundry(item)
        return sanitized
    if isinstance(value, list):
        return [sanitize_for_foundry(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_for_foundry(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def safe_table(db_path: str | Path, table_name: str) -> list[dict[str, Any]]:
    try:
        return fetch_all(db_path, table_name)
    except Exception:
        return []


def active_context(db_path: str | Path = DEFAULT_DB_PATH, study_id: str = DEFAULT_STUDY_ID) -> dict[str, Any]:
    init_db(db_path)
    study = get_or_create_default_study(db_path) if study_id == DEFAULT_STUDY_ID else {}
    active_run = get_active_study_run(db_path, study_id) or {}
    run_id = str(active_run.get("id") or "")
    include_demo = bool(active_run.get("study_mode") == "demo")
    progress = study_progress(db_path, study_id, run_id, include_demo=include_demo) if run_id else {}
    signals = list_signals(db_path, study_id, run_id, include_demo=include_demo) if run_id else []
    findings = list_findings(db_path, study_id, run_id, include_demo=include_demo) if run_id else []
    audits = list_finding_audits(db_path, study_id, run_id, include_demo=include_demo) if run_id else []
    opportunities = list_opportunities(db_path, study_id, run_id, include_demo=include_demo) if run_id else []
    briefs = list_study_briefs(db_path, study_id, run_id, include_demo=include_demo) if run_id else []
    quality = evidence_quality_dashboard(signals)
    supply = data_source_health_dashboard(db_path, study_id)
    pipeline = production_pipeline_statuses(progress) if progress else {}
    return {
        "study": study,
        "active_run": active_run,
        "run_id": run_id,
        "include_demo": include_demo,
        "progress": progress,
        "signals": signals,
        "findings": findings,
        "audits": audits,
        "opportunities": opportunities,
        "briefs": briefs,
        "quality": quality,
        "supply": supply,
        "pipeline": pipeline,
    }


def current_stage(progress: dict[str, Any]) -> str:
    if not progress or not progress.get("signals_collected"):
        return "Discovery"
    if not progress.get("findings_created"):
        return "Verification"
    if not progress.get("audits_completed"):
        return "Intelligence"
    if not progress.get("opportunities_approved"):
        return "Executive Due Diligence"
    if not progress.get("engineering_ready"):
        return "Blueprint Studio"
    return "Component Warehouse"


def current_recommendation(ctx: dict[str, Any]) -> str:
    progress = ctx["progress"]
    run = ctx["active_run"]
    quality = ctx["quality"]
    if not run:
        return "Create or activate a GS-001 study run."
    if run.get("study_mode") == "demo":
        return "Start a production run before making build decisions."
    if not progress.get("signals_collected"):
        return "Pull real market evidence or add the first verified source."
    if quality.get("production_readiness") != "Ready for finding generation":
        return "Continue evidence collection until source independence and trust thresholds are met."
    if not progress.get("findings_created"):
        return "Generate intelligence from accepted production evidence."
    if not progress.get("audits_completed"):
        return "Run Executive Due Diligence before approving any opportunity."
    if not progress.get("opportunities_approved"):
        return "Resolve blockers or approve only evidence-backed opportunities."
    if not progress.get("engineering_ready"):
        return "Create a software blueprint for the approved opportunity."
    return "Move reusable components into the Component Warehouse review."


def next_action(ctx: dict[str, Any]) -> str:
    stage = current_stage(ctx["progress"])
    actions = {
        "Discovery": "Pull Real Market Evidence",
        "Verification": "Review accepted and rejected evidence",
        "Intelligence": "Generate findings from evidence clusters",
        "Executive Due Diligence": "Run due diligence scorecard",
        "Blueprint Studio": "Create engineering blueprint",
        "Component Warehouse": "Review existing reusable components",
    }
    return actions.get(stage, "Review Mission Control")


def signal_decision_view(signal: dict[str, Any]) -> dict[str, Any]:
    view = signal_trace_card_view_model(signal)
    return {
        "title": view["source_name"],
        "executive_summary": view["executive_summary"],
        "decision": {
            "authority": view["authority_decision"],
            "commercial_relevance": view["commercial_relevance_decision"],
            "traceability": view["traceability_decision"],
            "independent_sources": view["independent_sources"],
            "independent_events": view["independent_events"],
            "organisations": view["organisations"],
            "current_recommendation": view["current_recommendation"],
        },
        "classification": {
            "evidence_classification": view["evidence_classification"],
            "evidence_relevance": view["evidence_relevance"],
            "evidence_tier": view["executive_evidence_tier"],
            "source_type": view["source_type"],
            "production_eligible": view["production_eligible"],
            "authority_score": view["authority_score"],
            "operational_relevance_score": view["operational_relevance_score"],
        },
        "detail": {
            "raw_evidence": view["raw_text"],
            "metadata": {
                "provider": view["provider"],
                "original_query": view["query"],
                "retrieved_at": view["retrieved"],
            },
            "source_url": view["source_url"],
            "entity_mapping": {
                "country": view["country"],
                "stakeholder": view["stakeholder"],
            },
            "reasoning": view["executive_explanation"],
            "raw_record": signal,
        },
    }


def mission_control_payload(db_path: str | Path = DEFAULT_DB_PATH, study_id: str = DEFAULT_STUDY_ID) -> dict[str, Any]:
    ctx = active_context(db_path, study_id)
    payload = {
        "question": "What decision should we make next?",
        "current_study": ctx["study"],
        "current_run": ctx["active_run"],
        "stage": current_stage(ctx["progress"]),
        "recommendation": current_recommendation(ctx),
        "next_action": next_action(ctx),
        "evidence_health": ctx["quality"],
        "production_evidence_count": ctx["quality"].get("accepted_production_signals", 0),
        "rejected_evidence_count": ctx["quality"].get("rejected", 0),
        "duplicate_count": ctx["quality"].get("duplicates", 0),
        "source_health_summary": {
            "overall_health": ctx["supply"].get("overall_health"),
            "coverage_confidence": ctx["supply"].get("coverage_confidence"),
            "tier_1_sources_configured": ctx["supply"].get("tier_1_sources_configured"),
            "failed_sources": ctx["supply"].get("failed_sources"),
            "working_apis": ctx["supply"].get("working_apis"),
        },
        "provena_operators": provena_operator_registry(db_path),
        "pipeline": ctx["pipeline"],
        "read_only": True,
    }
    return sanitize_for_foundry(payload)


def discovery_payload(db_path: str | Path = DEFAULT_DB_PATH, study_id: str = DEFAULT_STUDY_ID) -> dict[str, Any]:
    ctx = active_context(db_path, study_id)
    supply = ctx["supply"]
    sources = list_evidence_sources(db_path, study_id)
    source_runs = safe_table(db_path, "source_collection_runs")
    provider_runs = safe_table(db_path, "provider_runs")
    payload = {
        "question": "What did we find?",
        "configured_sources": sources,
        "source_statuses": [
            {
                "name": source.get("name") or source.get("source_name"),
                "status": source.get("current_status") or source.get("readiness_label"),
                "readiness": source.get("readiness_label"),
                "collection_method": source.get("collection_method"),
                "evidence_class": source.get("evidence_class"),
            }
            for source in sources
        ],
        "latest_evidence_pulls": provider_runs[:20],
        "documents_retrieved": supply.get("daily_documents_collected", 0),
        "source_health": supply,
        "failed_sources": [source for source in sources if str(source.get("current_status") or "").lower() in {"failed", "error"}],
        "collection_runs": source_runs[:20],
        "read_only": True,
    }
    return sanitize_for_foundry(payload)


def verification_payload(db_path: str | Path = DEFAULT_DB_PATH, study_id: str = DEFAULT_STUDY_ID) -> dict[str, Any]:
    ctx = active_context(db_path, study_id)
    accepted: list[dict[str, Any]] = []
    supporting: list[dict[str, Any]] = []
    market_context: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    rejection_reasons: dict[str, int] = {}
    for signal in ctx["signals"]:
        card = signal_decision_view(signal)
        classification = str(card["classification"]["evidence_classification"])
        eligible = card["classification"]["production_eligible"] == "YES"
        if eligible:
            accepted.append(card)
        elif classification == "community_signal":
            supporting.append(card)
        elif classification == "market_context":
            market_context.append(card)
        else:
            rejected.append(card)
            reason = str(signal.get("skip_reason") or card["detail"]["reasoning"] or "not_production_eligible")
            rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
    payload = {
        "question": "Can we trust it?",
        "accepted_production_evidence": accepted,
        "supporting_evidence": supporting,
        "market_context": market_context,
        "rejected_evidence": rejected,
        "rejection_reasons": rejection_reasons,
        "authority_relevance_summary": {
            "average_trust_score": ctx["quality"].get("average_trust_score"),
            "average_operational_relevance_score": ctx["quality"].get("average_operational_relevance_score"),
            "independent_domains": ctx["quality"].get("independent_domains"),
            "production_readiness": ctx["quality"].get("production_readiness"),
        },
        "read_only": True,
    }
    return sanitize_for_foundry(payload)


def intelligence_payload(db_path: str | Path = DEFAULT_DB_PATH, study_id: str = DEFAULT_STUDY_ID) -> dict[str, Any]:
    ctx = active_context(db_path, study_id)
    clusters = build_evidence_clusters(ctx["signals"]) if ctx["signals"] else []
    entities = sorted({str(signal.get("stakeholder_type") or "Unknown") for signal in ctx["signals"]})
    organisations = sorted({str(signal.get("company_product") or "") for signal in ctx["signals"] if signal.get("company_product")})
    countries = sorted({str(signal.get("country") or "Unknown") for signal in ctx["signals"]})
    payload = {
        "question": "What pattern exists?",
        "evidence_clusters": clusters,
        "entities": entities,
        "organisations": organisations,
        "owners": [entity for entity in entities if "owner" in entity.lower() or "landlord" in entity.lower()],
        "portfolios": sorted({str(signal.get("complaint_category") or "Unknown") for signal in ctx["signals"]}),
        "geographic_spread": countries,
        "commercial_relevance": {
            "production_readiness": ctx["quality"].get("production_readiness"),
            "accepted_production_signals": ctx["quality"].get("accepted_production_signals"),
            "average_trust_score": ctx["quality"].get("average_trust_score"),
            "findings_created": ctx["progress"].get("findings_created"),
        },
        "discovery_learning": discovery_learning_dashboard(db_path, study_id),
        "read_only": True,
    }
    return sanitize_for_foundry(payload)


def due_diligence_payload(db_path: str | Path = DEFAULT_DB_PATH, study_id: str = DEFAULT_STUDY_ID) -> dict[str, Any]:
    ctx = active_context(db_path, study_id)
    blockers: list[str] = []
    if int(ctx["quality"].get("accepted_production_signals") or 0) < 3:
        blockers.append("Fewer than 3 accepted production evidence records.")
    if int(ctx["quality"].get("independent_domains") or 0) < 2:
        blockers.append("Fewer than 2 independent source domains.")
    if not ctx["findings"]:
        blockers.append("No intelligence finding has been generated.")
    if not ctx["audits"]:
        blockers.append("No Executive Due Diligence audit has been completed.")
    risks = [
        audit.get("missing_evidence") or audit.get("missing_evidence_warnings")
        for audit in ctx["audits"]
        if audit.get("missing_evidence") or audit.get("missing_evidence_warnings")
    ]
    proceed = not blockers and any(str(audit.get("decision") or "") == "Approve Opportunity" for audit in ctx["audits"])
    payload = {
        "question": "Should we build software?",
        "current_recommendation": "Proceed to Blueprint Studio." if proceed else current_recommendation(ctx),
        "scorecard": [
            {
                "finding": audit.get("finding_id"),
                "decision": audit.get("decision"),
                "evidence_score": audit.get("evidence_score"),
                "pain_score": audit.get("pain_severity_score"),
                "traceability_score": audit.get("traceability_score"),
                "oci": audit.get("opportunity_confidence_index"),
            }
            for audit in ctx["audits"]
        ],
        "blockers": blockers,
        "risks": risks,
        "research_gaps": {
            "pending_verification": ctx["progress"].get("verification_pending_count", 0),
            "weak_evidence": ctx["progress"].get("weak_evidence", []),
            "source_coverage": ctx["progress"].get("source_coverage", 0),
        },
        "why_proceed": "Evidence, traceability, and audit decision meet build threshold." if proceed else "",
        "why_blocked": blockers,
        "read_only": True,
    }
    return sanitize_for_foundry(payload)


def blueprints_payload(db_path: str | Path = DEFAULT_DB_PATH, study_id: str = DEFAULT_STUDY_ID) -> dict[str, Any]:
    ctx = active_context(db_path, study_id)
    briefs = ctx["briefs"]
    opportunities = ctx["opportunities"]
    payload = {
        "question": "What are we building?",
        "generated_briefs": briefs,
        "software_blueprints": [
            {
                "component": opportunity.get("recommended_component"),
                "purpose": opportunity.get("problem_scope") or opportunity.get("problem"),
                "target_users": opportunity.get("target_users"),
                "inputs": opportunity.get("required_inputs"),
                "outputs": opportunity.get("expected_outputs"),
                "system_boundaries": opportunity.get("system_boundaries"),
                "recommendation": opportunity.get("engineering_recommendation"),
                "status": opportunity.get("engineering_status"),
            }
            for opportunity in opportunities
        ],
        "prototype_status": "Not started",
        "component_status": [
            {
                "component": opportunity.get("recommended_component"),
                "status": opportunity.get("engineering_status") or opportunity.get("status"),
                "oci": opportunity.get("opportunity_confidence_index"),
            }
            for opportunity in opportunities
        ],
        "downloadable_outputs": [
            {"title": brief.get("title"), "type": brief.get("brief_type"), "id": brief.get("id")}
            for brief in briefs
        ],
        "component_warehouse": {
            "question": "What have we already built?",
            "engineering_ready": ctx["progress"].get("engineering_ready", []),
            "approved_components": [
                opportunity for opportunity in opportunities
                if opportunity.get("engineering_status") in {"Engineering Ready", "Demo Engineering Ready"}
            ],
        },
        "read_only": True,
    }
    return sanitize_for_foundry(payload)


def schema_examples() -> dict[str, Any]:
    return {
        "/api/foundry/mission-control": {
            "question": "What decision should we make next?",
            "stage": "Discovery",
            "recommendation": "Pull real market evidence or add the first verified source.",
            "evidence_health": {"production_readiness": "Needs stronger evidence"},
        },
        "/api/foundry/verification": {
            "question": "Can we trust it?",
            "accepted_production_evidence": [
                {
                    "executive_summary": "Production evidence: BBB complaint has 82% decision confidence.",
                    "decision": {"authority": "PASS", "traceability": "PASS"},
                    "detail": {"source_url": "https://example.com/source"},
                }
            ],
        },
    }


def endpoint_map() -> dict[str, Any]:
    return {
        "mission-control": mission_control_payload,
        "discovery": discovery_payload,
        "verification": verification_payload,
        "intelligence": intelligence_payload,
        "due-diligence": due_diligence_payload,
        "blueprints": blueprints_payload,
    }


def create_app(db_path: str | Path = DEFAULT_DB_PATH):
    try:
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
    except ImportError as exc:
        raise RuntimeError("FastAPI is required for HTTP endpoints. Install requirements.txt first.") from exc

    app = FastAPI(
        title="Provena Foundry OS API",
        version="0.1.0",
        description="Read-only JSON API exposing Provena/GS-001 state to the Lovable Foundry OS frontend.",
    )
    origins = [origin.strip() for origin in os.getenv("FOUNDRY_CORS_ORIGINS", "*").split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=False,
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.get("/api/foundry/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "read_only": True}

    @app.get("/api/foundry/schema-examples")
    def examples() -> dict[str, Any]:
        return schema_examples()

    for slug, builder in endpoint_map().items():

        def route(payload_builder=builder) -> dict[str, Any]:
            try:
                return payload_builder(db_path)
            except Exception:
                return {"error": "Foundry API could not build this payload.", "read_only": True}

        app.get(f"/api/foundry/{slug}")(route)

    return app


try:
    app = create_app(os.getenv("PROVENA_DB_PATH", str(DEFAULT_DB_PATH))) if os.getenv("PROVENA_CREATE_API_APP", "1") == "1" else None
except RuntimeError:
    app = None
