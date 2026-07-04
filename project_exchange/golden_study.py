from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

from project_exchange.database import connect, count_rows, row_to_dict, utc_now
from project_exchange.eos import add_event, add_notification
from project_exchange.ids import next_sequence_id
from project_exchange.provider_base import ProviderResult
from project_exchange.provider_modules.newsapi_provider import NewsAPIProvider
from project_exchange.provider_modules.tavily_serpapi_provider import SerpAPISearchProvider, TavilySearchProvider
from project_exchange.provider_status import provider_ready_for_research


DEFAULT_STUDY_ID = "GS-001"
ENGINEERING_READY_OCI = 85
PROVENANCE_TABLES = ["studies", "study_signals", "study_findings", "finding_audits", "opportunity_records", "study_briefs"]
RUN_SCOPED_TABLES = ["study_signals", "study_findings", "finding_audits", "opportunity_records", "study_briefs"]

STAKEHOLDER_KEYWORDS = {
    "Tenants": ["tenant", "renters", "resident"],
    "Property managers": ["property manager", "manager", "portfolio"],
    "Housing associations": ["housing association", "social housing"],
    "Facilities managers": ["facilities", "facility"],
    "Estate management companies": ["estate management", "estate manager"],
    "Condo / HOA managers": ["hoa", "condo", "strata"],
    "Commercial property managers": ["commercial", "office", "retail unit"],
    "Letting agents": ["letting agent", "lettings", "leasing"],
    "Property owners": ["landlord", "owner"],
    "Maintenance contractors": ["contractor", "maintenance team", "repair vendor"],
}

GS001_REAL_EVIDENCE_QUERIES = [
    "tenant maintenance complaint property management",
    "tenant maintenance ignored",
    "property management complaint maintenance delay",
    "property management repair complaint",
    "maintenance request ignored",
    "maintenance response time complaint",
    "property manager never fixes repairs",
    "site:bbb.org property management complaints",
    "site:bbb.org maintenance complaint",
    "site:bbb.org landlord complaint",
    "site:consumeraffairs.com property management",
    "site:consumeraffairs.com apartment management",
    "site:consumeraffairs.com landlord complaints",
    "site:.gov tenant maintenance complaint",
    "site:hud.gov maintenance complaint",
    "site:.gov landlord repairs",
    "site:.gov habitability complaint",
    "site:ag.* tenant complaint",
    "site:ag.* landlord complaint",
    "site:ombudsman.org property management",
    "site:housing-ombudsman.org.uk repairs",
    "tenant maintenance lawsuit",
    "property management lawsuit maintenance",
    "habitability lawsuit landlord",
    "tenant maintenance complaints",
    "property management fined maintenance",
    "landlord maintenance investigation",
    "property management reviews maintenance",
    "apartment management complaints",
    "reddit tenant maintenance ignored",
    "reddit landlord repair complaint",
]

GS_P001_PRIORITY_EVIDENCE_SOURCES: list[dict[str, object]] = [
    {
        "id": "EDS-HUD",
        "source_name": "HUD",
        "organisation": "U.S. Department of Housing and Urban Development",
        "evidence_class": "Government",
        "country": "United States",
        "authority_level": "High",
        "trust_default": 92,
        "collection_method": "API / HTML / PDF",
        "authentication_required": False,
        "rate_limits": "Public endpoints vary by dataset",
        "update_frequency": "Daily / periodic",
        "average_documents": 25,
        "production_ready": "Production Ready",
        "legal_terms_notes": "Use public records and respect endpoint terms.",
        "supported_golden_studies": "GS-001,GS-P001",
        "current_status": "Configured",
        "accessible": "YES",
        "structured": "YES",
        "automatable": "YES",
    },
    {
        "id": "EDS-HOUSING-AUTH",
        "source_name": "Housing Authorities",
        "organisation": "Local and state housing authorities",
        "evidence_class": "Housing Authority",
        "authority_level": "High",
        "trust_default": 90,
        "collection_method": "HTML / PDF / Open Dataset",
        "authentication_required": False,
        "rate_limits": "Varies by authority",
        "update_frequency": "Weekly / monthly",
        "average_documents": 15,
        "production_ready": "Production Ready",
        "legal_terms_notes": "Source-specific crawl policies required.",
        "supported_golden_studies": "GS-001,GS-P001",
        "current_status": "Configured",
        "accessible": "YES",
        "structured": "Medium",
        "automatable": "YES",
    },
    {
        "id": "EDS-AG",
        "source_name": "Attorney General Offices",
        "organisation": "State Attorneys General",
        "evidence_class": "Attorney General",
        "authority_level": "High",
        "trust_default": 92,
        "collection_method": "RSS / HTML / PDF",
        "authentication_required": False,
        "rate_limits": "Varies by state",
        "update_frequency": "Weekly",
        "average_documents": 10,
        "production_ready": "Production Ready",
        "legal_terms_notes": "Use official press releases and public enforcement records.",
        "supported_golden_studies": "GS-001,GS-P001",
        "current_status": "Configured",
        "accessible": "YES",
        "structured": "Medium",
        "automatable": "YES",
    },
    {
        "id": "EDS-BBB",
        "source_name": "Better Business Bureau",
        "organisation": "BBB",
        "evidence_class": "Consumer Complaints",
        "authority_level": "Medium",
        "trust_default": 95,
        "collection_method": "Search Provider / HTML",
        "authentication_required": False,
        "rate_limits": "Limited; respect terms",
        "update_frequency": "Daily",
        "average_documents": 30,
        "production_ready": "Supporting Evidence Only",
        "legal_terms_notes": "Use excerpts and links; avoid bulk scraping without permission.",
        "supported_golden_studies": "GS-001,GS-P001",
        "current_status": "Configured",
        "accessible": "Limited",
        "structured": "Medium",
        "automatable": "Limited",
    },
    {
        "id": "EDS-CONSUMER-AFFAIRS",
        "source_name": "Consumer Affairs",
        "organisation": "ConsumerAffairs",
        "evidence_class": "Consumer Protection",
        "authority_level": "Medium",
        "trust_default": 95,
        "collection_method": "Search Provider / HTML",
        "authentication_required": False,
        "rate_limits": "Limited; respect terms",
        "update_frequency": "Daily",
        "average_documents": 25,
        "production_ready": "Supporting Evidence Only",
        "legal_terms_notes": "Use source URLs and snippets; verify terms before automated collection.",
        "supported_golden_studies": "GS-001,GS-P001",
        "current_status": "Configured",
        "accessible": "Limited",
        "structured": "Medium",
        "automatable": "Limited",
    },
    {
        "id": "EDS-COURTS",
        "source_name": "Court Records",
        "organisation": "CourtListener and public court portals",
        "evidence_class": "Court",
        "authority_level": "High",
        "trust_default": 98,
        "collection_method": "API / HTML / PDF",
        "authentication_required": False,
        "rate_limits": "API dependent",
        "update_frequency": "Daily",
        "average_documents": 12,
        "production_ready": "Production Ready",
        "legal_terms_notes": "Use public legal records with citations.",
        "supported_golden_studies": "GS-001,GS-P001",
        "current_status": "Configured",
        "accessible": "YES",
        "structured": "Medium",
        "automatable": "YES",
    },
    {
        "id": "EDS-311",
        "source_name": "311 Complaint Systems",
        "organisation": "Municipal 311 open data portals",
        "evidence_class": "Housing Authority",
        "authority_level": "High",
        "trust_default": 90,
        "collection_method": "Open Dataset / API",
        "authentication_required": False,
        "rate_limits": "Portal dependent",
        "update_frequency": "Daily",
        "average_documents": 100,
        "production_ready": "Production Ready",
        "legal_terms_notes": "Use public open-data terms and preserve dataset references.",
        "supported_golden_studies": "GS-001,GS-P001",
        "current_status": "Configured",
        "accessible": "YES",
        "structured": "YES",
        "automatable": "YES",
    },
    {
        "id": "EDS-INVESTIGATIVE-NEWS",
        "source_name": "Investigative Journalism",
        "organisation": "Major and regional investigative publishers",
        "evidence_class": "Investigative Journalism",
        "authority_level": "Medium",
        "trust_default": 85,
        "collection_method": "RSS / Search Provider",
        "authentication_required": False,
        "rate_limits": "Publisher dependent",
        "update_frequency": "Daily",
        "average_documents": 10,
        "production_ready": "Supporting Evidence Only",
        "legal_terms_notes": "Cite source links; avoid reproducing article text.",
        "supported_golden_studies": "GS-001,GS-P001",
        "current_status": "Configured",
        "accessible": "YES",
        "structured": "Medium",
        "automatable": "YES",
    },
    {
        "id": "EDS-FEDERAL-REGISTER",
        "source_name": "Federal Register",
        "organisation": "Office of the Federal Register",
        "evidence_class": "Government",
        "authority_level": "High",
        "trust_default": 88,
        "collection_method": "API",
        "authentication_required": False,
        "rate_limits": "Public API limits",
        "update_frequency": "Daily",
        "average_documents": 40,
        "production_ready": "Market Context",
        "legal_terms_notes": "Public federal records; usually context until operational pain is explicit.",
        "supported_golden_studies": "GS-001,GS-P001",
        "current_status": "Configured",
        "accessible": "YES",
        "structured": "YES",
        "automatable": "YES",
    },
    {
        "id": "EDS-TENANT-ADVOCACY",
        "source_name": "Tenant Advocacy Organisations",
        "organisation": "Tenant unions and advocacy groups",
        "evidence_class": "Tenant Advocacy",
        "authority_level": "Medium",
        "trust_default": 78,
        "collection_method": "RSS / HTML",
        "authentication_required": False,
        "rate_limits": "Source dependent",
        "update_frequency": "Weekly",
        "average_documents": 8,
        "production_ready": "Supporting Evidence Only",
        "legal_terms_notes": "Verify claims against independent sources.",
        "supported_golden_studies": "GS-001,GS-P001",
        "current_status": "Configured",
        "accessible": "YES",
        "structured": "Low",
        "automatable": "Limited",
    },
    {
        "id": "EDS-SEARCH-PROVIDERS",
        "source_name": "Search Providers",
        "organisation": "Tavily / SerpAPI / NewsAPI",
        "evidence_class": "Search Provider",
        "authority_level": "Supplemental",
        "trust_default": 70,
        "collection_method": "API",
        "authentication_required": True,
        "rate_limits": "Provider plan dependent",
        "update_frequency": "On demand",
        "average_documents": 50,
        "production_ready": "Supplemental Provider",
        "legal_terms_notes": "Use to discover sources, not as proof by itself.",
        "supported_golden_studies": "GS-001,GS-P001",
        "current_status": "Configured",
        "accessible": "Limited",
        "structured": "YES",
        "automatable": "YES",
    },
]

GS001_EVIDENCE_QUERY_GROUPS = {
    "consumer_complaint": [
        "tenant maintenance complaint property management",
        "tenant maintenance ignored",
        "property management complaint maintenance delay",
        "property management repair complaint",
        "maintenance request ignored",
        "maintenance response time complaint",
        "property manager never fixes repairs",
    ],
    "bbb": [
        "site:bbb.org property management complaints",
        "site:bbb.org maintenance complaint",
        "site:bbb.org landlord complaint",
    ],
    "consumer_affairs": [
        "site:consumeraffairs.com property management",
        "site:consumeraffairs.com apartment management",
        "site:consumeraffairs.com landlord complaints",
    ],
    "government": [
        "site:.gov tenant maintenance complaint",
        "site:hud.gov maintenance complaint",
        "site:.gov landlord repairs",
        "site:.gov habitability complaint",
    ],
    "attorney_general": [
        "site:ag.* tenant complaint",
        "site:ag.* landlord complaint",
    ],
    "housing_ombudsman": [
        "site:ombudsman.org property management",
        "site:housing-ombudsman.org.uk repairs",
    ],
    "court_cases": [
        "tenant maintenance lawsuit",
        "property management lawsuit maintenance",
        "habitability lawsuit landlord",
    ],
    "news": [
        "tenant maintenance complaints",
        "property management fined maintenance",
        "landlord maintenance investigation",
    ],
    "review_platforms": [
        "property management reviews maintenance",
        "apartment management complaints",
    ],
    "forums": [
        "reddit tenant maintenance ignored",
        "reddit landlord repair complaint",
    ],
}

EVIDENCE_CLASS_TIERS: dict[str, dict[str, object]] = {
    "Government": {"tier": 1, "label": "Government source"},
    "Regulator": {"tier": 1, "label": "Regulatory source"},
    "Attorney General": {"tier": 1, "label": "Attorney General enforcement"},
    "Housing Authority": {"tier": 1, "label": "Housing authority source"},
    "Court": {"tier": 1, "label": "Court or legal record"},
    "Ombudsman": {"tier": 1, "label": "Ombudsman decision"},
    "Public Enforcement": {"tier": 1, "label": "Public enforcement action"},
    "Official Investigation": {"tier": 1, "label": "Official investigation"},
    "Consumer Protection": {"tier": 2, "label": "Consumer protection source"},
    "Consumer Complaints": {"tier": 2, "label": "Consumer complaint body"},
    "Tenant Advocacy": {"tier": 2, "label": "Tenant advocacy source"},
    "Investigative Journalism": {"tier": 3, "label": "Investigative journalism"},
    "Housing Trade Publication": {"tier": 3, "label": "Housing trade publication"},
    "Community Evidence": {"tier": 4, "label": "Community evidence"},
    "Search Provider": {"tier": 5, "label": "Search provider result"},
    "Vendor": {"tier": 6, "label": "Vendor content"},
    "Marketing": {"tier": 6, "label": "Marketing content"},
    "Unknown": {"tier": 6, "label": "Unknown source class"},
}

GS_P001_EVIDENCE_STRATEGY: dict[str, object] = {
    "id": "GS-P001",
    "study_id": DEFAULT_STUDY_ID,
    "principle": "Evidence quality before quantity",
    "country": "United States",
    "industry": "Residential Property Management",
    "operational_focus": "maintenance communication failures",
    "query_categories": [
        {
            "query_group": "government",
            "query_category": "Regulatory Actions",
            "evidence_class": "Regulator",
            "queries": [
                "site:.gov property management maintenance complaint enforcement",
                "site:.gov landlord repair communication complaint",
                "site:hud.gov tenant maintenance complaint repair communication",
            ],
        },
        {
            "query_group": "attorney_general",
            "query_category": "Attorney General Enforcement",
            "evidence_class": "Attorney General",
            "queries": [
                "attorney general landlord maintenance complaint enforcement",
                "site:ag.* tenant maintenance complaint landlord repair",
                "state attorney general property management maintenance complaint",
            ],
        },
        {
            "query_group": "government",
            "query_category": "Housing Authority Complaints",
            "evidence_class": "Housing Authority",
            "queries": [
                "housing authority maintenance complaint repair communication",
                "public housing maintenance complaint no response repair",
                "site:.gov housing maintenance work order complaint",
            ],
        },
        {
            "query_group": "court_cases",
            "query_category": "Court Judgments",
            "evidence_class": "Court",
            "queries": [
                "tenant maintenance lawsuit no response property management",
                "habitability lawsuit landlord maintenance communication",
                "court landlord repair complaint tenant maintenance delayed",
            ],
        },
        {
            "query_group": "housing_ombudsman",
            "query_category": "Maintenance Enforcement",
            "evidence_class": "Ombudsman",
            "queries": [
                "ombudsman repairs complaint landlord communication maintenance",
                "housing ombudsman maintenance complaint no repair updates",
                "resident complaint repairs not updated maintenance ombudsman",
            ],
        },
        {
            "query_group": "bbb",
            "query_category": "Consumer Complaints",
            "evidence_class": "Consumer Complaints",
            "queries": [
                "site:bbb.org property management maintenance complaints",
                "site:bbb.org landlord maintenance complaint no response",
                "site:bbb.org apartment maintenance repair complaint",
            ],
        },
        {
            "query_group": "consumer_affairs",
            "query_category": "Consumer Complaints",
            "evidence_class": "Consumer Protection",
            "queries": [
                "site:consumeraffairs.com property management maintenance complaint",
                "site:consumeraffairs.com apartment maintenance complaints no response",
                "site:consumeraffairs.com landlord repair complaint",
            ],
        },
        {
            "query_group": "consumer_complaint",
            "query_category": "Resident Communication Failures",
            "evidence_class": "Consumer Complaints",
            "queries": [
                "tenant complaint maintenance request no response property management",
                "apartment resident complaints maintenance not fixed property manager",
                "property manager maintenance request delayed tenant complaint",
            ],
        },
        {
            "query_group": "news",
            "query_category": "Public Investigations",
            "evidence_class": "Investigative Journalism",
            "queries": [
                "investigation landlord maintenance complaints no response",
                "news property management maintenance complaints tenants",
                "property management fined maintenance complaints investigation",
            ],
        },
        {
            "query_group": "consumer_complaint",
            "query_category": "Repair Communication Failures",
            "evidence_class": "Search Provider",
            "queries": [
                "rental property maintenance complaints poor communication",
                "tenant maintenance request ignored property manager complaint",
                "apartment maintenance no response resident complaint",
            ],
        },
        {
            "query_group": "consumer_complaint",
            "query_category": "Maintenance Work Order Failures",
            "evidence_class": "Search Provider",
            "queries": [
                "maintenance work order complaint tenant no update",
                "property management work order delayed tenant complaint",
                "resident complaint maintenance work order ignored",
            ],
        },
        {
            "query_group": "forums",
            "query_category": "Community Evidence",
            "evidence_class": "Community Evidence",
            "queries": [
                "reddit tenant maintenance ignored repair communication",
                "tenant forum landlord maintenance no response complaint",
            ],
        },
    ],
}

GS001_REAL_EVIDENCE_QUERIES = [
    query
    for category in GS_P001_EVIDENCE_STRATEGY["query_categories"]  # type: ignore[index]
    for query in category["queries"]  # type: ignore[index]
]

VALID_COMPLAINT_RELEVANCE = {"complaint", "operational_pain", "workflow_inefficiency"}
PRODUCTION_ELIGIBLE_CLASSIFICATIONS = {"verified_complaint", "operational_pain", "workflow_inefficiency"}
MIN_PRODUCTION_AUTHORITY_SCORE = 70
MIN_OPPORTUNITY_INDEPENDENT_SOURCES = 8
MIN_OPPORTUNITY_INDEPENDENT_EVENTS = 5
MIN_OPPORTUNITY_EVIDENCE_SCORE = 90
MIN_OPPORTUNITY_PAIN_SCORE = 85
MIN_OPPORTUNITY_CONFIDENCE = 90
MIN_OPPORTUNITY_TRACEABILITY = 100
MIN_OPPORTUNITY_GEOGRAPHIC_DIVERSITY = 3
MIN_OPPORTUNITY_STAKEHOLDER_DIVERSITY = 2
MIN_OPPORTUNITY_ORGANISATION_DIVERSITY = 4
SOURCE_TRUST_SCORES = {
    "government": 92,
    "court": 98,
    "ombudsman": 98,
    "consumer_review": 95,
    "verified_review_platform": 90,
    "news": 85,
    "industry_association": 80,
    "research": 80,
    "forum": 70,
    "community": 60,
    "social_media": 60,
    "facebook_group": 40,
    "article": 70,
    "search_result": 70,
    "manual_verified": 70,
    "vendor": 20,
    "marketing": 10,
    "unknown": 0,
}
MARKETING_CONTENT_PATTERNS = [
    "top 10",
    "ultimate guide",
    "everything you need to know",
    "industry trends",
    "market outlook",
    "best companies",
    "best software",
    "vendor landing page",
    "product feature",
    "sales page",
    "seo blog",
    "company home page",
    "generic market report",
    "promotional content",
    "we buy houses",
    "sell your house fast",
    "property management trends 2026",
    "essential things to know",
]
MARKETING_REJECTION_REASON = "Marketing / Promotional / Generic Industry Content"
PAIN_KEYWORDS = [
    "complaint",
    "complain",
    "complains",
    "issue",
    "problem",
    "poor",
    "slow",
    "delayed",
    "no response",
    "unresolved",
    "waiting",
    "broken",
    "repair",
    "maintenance request",
    "frustration",
    "dispute",
    "bad service",
    "ignored",
    "lack of communication",
    "not updated",
]
PROPERTY_MAINTENANCE_CONTEXT_KEYWORDS = [
    "tenant",
    "resident",
    "apartment",
    "landlord",
    "property manager",
    "property management",
    "hoa",
    "maintenance",
    "repair",
    "work order",
    "rental",
    "multifamily",
]
GS001_REQUIRED_MAINTENANCE_CONTEXT_KEYWORDS = [
    "maintenance",
    "maintenance request",
    "repair",
    "repairs",
    "work order",
    "habitability",
]
GS001_OPERATIONAL_RELEVANCE_KEYWORDS = [
    "repair communication",
    "status update",
    "status updates",
    "resident communication",
    "maintenance request handling",
    "repair follow-up",
    "follow up",
    "maintenance updates",
    "maintenance update",
    "maintenance communication",
    "maintenance coordination",
    "maintenance status",
    "communicate maintenance",
    "failed to communicate",
    "communication failure",
    "communication failures",
    "tenant communication",
    "property manager communication",
    "no response",
    "not updated",
    "ignored",
    "maintenance request",
    "work order",
    "repair updates",
]
GS001_CONTEXT_ONLY_PATTERNS = [
    "procurement",
    "agenda",
    "paving",
    "road maintenance",
    "infrastructure",
    "bid opening",
    "request for proposal",
    "rfp",
    "city council",
    "minutes",
    "capital improvement",
    "contract award",
    "public works",
    "street repair",
]
GS001_ADVICE_PAGE_PATTERNS = [
    "how to",
    "tips",
    "guide",
    "best practices",
    "advice",
    "overview",
    "what is",
]

CATEGORY_KEYWORDS = {
    "Maintenance issues": ["maintenance", "repair", "contractor", "work order"],
    "Tenant communication issues": ["communication", "message", "tenant", "update", "response"],
    "Accounting / payment issues": ["payment", "accounting", "invoice", "rent", "arrears"],
    "Reporting problems": ["report", "dashboard", "analytics", "export"],
    "Compliance problems": ["compliance", "regulation", "inspection", "certificate"],
    "Missing integrations": ["integration", "sync", "api", "spreadsheet"],
    "Expensive software complaints": ["expensive", "pricing", "cost", "subscription"],
    "Feature requests": ["feature", "wish", "request", "missing"],
    "Repetitive manual tasks": ["manual", "spreadsheet", "copy", "repetitive"],
    "Poor customer experiences": ["slow", "poor", "bad", "frustrating", "support"],
}

CANONICAL_GS001_CLUSTERS = {
    "Maintenance Communication Failure": {
        "summary": "Residents, tenants, landlords, or property teams do not receive clear repair status, explanations, or follow-up during maintenance handling.",
        "patterns": [
            "not updated",
            "no update",
            "resident not updated",
            "tenant not updated",
            "failed to communicate",
            "poor communication",
            "communication is poor",
            "repair communication",
            "communication updates",
            "lack of communication",
            "no repair updates",
            "unclear maintenance status",
            "complaint handling failed",
            "complaint handling",
            "emergency repair not explained",
            "lack of follow-up",
            "follow-up",
            "failure to respond",
            "no response",
            "repair took months",
            "not explain",
            "poor complaint handling",
            "work order updates",
            "maintenance coordination",
            "updates are slow",
            "updates are delayed",
        ],
    },
    "Maintenance Delay / Repair Delay": {
        "summary": "Maintenance requests, work orders, or repairs are delayed, ignored, unresolved, or require repeated chasing.",
        "patterns": [
            "repair took months",
            "work order delayed",
            "maintenance request ignored",
            "request ignored",
            "unresolved repair",
            "emergency repair delayed",
            "repair not completed",
            "repeated chasing",
            "chase repairs",
            "repairs delayed",
            "delayed",
            "unresolved",
            "ignored",
        ],
    },
    "Complaint Handling Failure": {
        "summary": "Complaint escalation, redress, learning, or resolution processes fail after maintenance problems are raised.",
        "patterns": [
            "complaint ignored",
            "complaint escalation failed",
            "complaint response poor",
            "complaint not resolved",
            "poor redress",
            "maladministration",
            "failure to learn",
            "complaint handling",
            "redress process",
        ],
    },
    "Property Management Coordination Failure": {
        "summary": "Property, housing, repair, or contractor teams fail to coordinate responsibility and handoffs for maintenance work.",
        "patterns": [
            "teams not coordinated",
            "not aligned",
            "poor handoff",
            "internal process failure",
            "no owner",
            "no accountability",
            "fragmented workflow",
            "coordination",
            "handoff",
            "contractor",
        ],
    },
    "Accounting / Payment Issues": {
        "summary": "Payment or accounting friction is present, but it only belongs in GS-001 if directly connected to maintenance communication.",
        "patterns": ["payment", "accounting", "invoice", "rent", "arrears", "deposit"],
    },
}

COUNTRY_HINTS = [
    "Ireland",
    "United Kingdom",
    "United States",
    "Canada",
    "Australia",
    "New Zealand",
    "Germany",
    "France",
    "Spain",
]


def get_or_create_default_study(db_path: str | Path) -> dict[str, object]:
    study = get_study(db_path, DEFAULT_STUDY_ID)
    if study:
        get_active_study_run(db_path, DEFAULT_STUDY_ID)
        return study
    return create_study(
        db_path,
        DEFAULT_STUDY_ID,
        "Global Property Management Golden Study",
        "Property Management",
        status="Active",
        scope="Global",
        countries="Global",
        stakeholders=", ".join(STAKEHOLDER_KEYWORDS),
        objective="Find verified, traceable market opportunities backed by repeated complaints and evidence.",
    )


def create_study(
    db_path: str | Path,
    study_id: str,
    name: str,
    market: str,
    scope: str = "",
    countries: str = "",
    stakeholders: str = "",
    objective: str = "",
    status: str = "Active",
    notes: str = "",
    data_origin: str = "demo",
    study_mode: str = "demo",
    production_confirmed: bool = False,
) -> dict[str, object]:
    mode = study_mode if study_mode in {"demo", "production"} else "demo"
    if mode == "production" and not production_confirmed:
        raise ValueError("Production GS-001 creation requires explicit confirmation.")
    if mode == "production" and data_origin == "demo":
        data_origin = "manual"
    existing_study = get_study(db_path, study_id)
    if existing_study:
        with connect(db_path) as connection:
            active = connection.execute(
                "SELECT study_mode FROM study_runs WHERE study_id = ? AND status = 'active' ORDER BY created_at DESC LIMIT 1",
                (study_id,),
            ).fetchone()
        if active and active["study_mode"] != mode:
            raise ValueError("Use switch_study_run_mode to change GS-001 run mode.")
    provenance = provenance_values(data_origin, "PX-H001")
    with connect(db_path) as connection:
        now = utc_now()
        connection.execute(
            """
            INSERT INTO studies
            (id, name, market, scope, countries, stakeholders, objective, status, started_at, lead_worker,
             research_worker, audit_worker, library_worker, notes, study_mode, data_origin, verification_status, is_demo,
             source_confidence, created_by_worker, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                market = excluded.market,
                scope = excluded.scope,
                countries = excluded.countries,
                stakeholders = excluded.stakeholders,
                objective = excluded.objective,
                status = excluded.status,
                notes = excluded.notes,
                study_mode = excluded.study_mode,
                data_origin = excluded.data_origin,
                verification_status = excluded.verification_status,
                is_demo = excluded.is_demo,
                last_updated = excluded.last_updated
            """,
            (
                study_id,
                name,
                market,
                scope,
                countries,
                stakeholders,
                objective,
                status,
                now,
                "PX-H001",
                "PX-R001",
                "PX-A001",
                "PX-L001",
                notes,
                mode,
                provenance["data_origin"],
                provenance["verification_status"],
                1 if provenance["is_demo"] else 0,
                provenance["source_confidence"],
                provenance["created_by_worker"],
                now,
            ),
        )
    add_event(db_path, "StudyCreated", "PX-H001", "Golden Study created", status, study_id)
    if not get_active_study_run(db_path, study_id):
        create_study_run(db_path, study_id, mode, provenance["data_origin"], "Initial Golden Study run.")
    return get_study(db_path, study_id) or {}


def get_study(db_path: str | Path, study_id: str) -> dict[str, object] | None:
    with connect(db_path) as connection:
        row = connection.execute("SELECT * FROM studies WHERE id = ?", (study_id,)).fetchone()
    return row_to_dict(row) if row else None


def list_studies(db_path: str | Path) -> list[dict[str, object]]:
    with connect(db_path) as connection:
        rows = connection.execute("SELECT * FROM studies ORDER BY started_at DESC").fetchall()
    return [row_to_dict(row) for row in rows]


def list_study_runs(db_path: str | Path, study_id: str = DEFAULT_STUDY_ID) -> list[dict[str, object]]:
    with connect(db_path) as connection:
        rows = connection.execute(
            "SELECT * FROM study_runs WHERE study_id = ? ORDER BY created_at DESC",
            (study_id,),
        ).fetchall()
    return [row_to_dict(row) for row in rows]


def get_active_study_run(db_path: str | Path, study_id: str = DEFAULT_STUDY_ID) -> dict[str, object] | None:
    with connect(db_path) as connection:
        row = connection.execute(
            "SELECT * FROM study_runs WHERE study_id = ? AND status = 'active' ORDER BY created_at DESC LIMIT 1",
            (study_id,),
        ).fetchone()
    if not row:
        study = get_study(db_path, study_id)
        if not study:
            return None
        return create_study_run(
            db_path,
            study_id,
            str(study.get("study_mode") or "demo"),
            str(study.get("data_origin") or "demo"),
            "Auto-created active study run.",
        )
    run = row_to_dict(row)
    assign_legacy_records_to_runs(db_path, study_id, str(run["id"]))
    return run


def create_study_run(
    db_path: str | Path,
    study_id: str,
    study_mode: str,
    data_origin: str,
    notes: str = "",
) -> dict[str, object]:
    mode = study_mode if study_mode in {"demo", "production"} else "demo"
    origin = normalize_data_origin(data_origin)
    if mode == "production" and origin == "demo":
        origin = "manual"
    provenance = provenance_values(origin, "PX-H001")
    with connect(db_path) as connection:
        active = connection.execute(
            "SELECT id FROM study_runs WHERE study_id = ? AND status = 'active'",
            (study_id,),
        ).fetchone()
        if active:
            raise ValueError(f"Study {study_id} already has an active run: {active['id']}")
        run_id = next_sequence_id("GSR", count_rows(connection, "study_runs"))
        now = utc_now()
        connection.execute(
            """
            INSERT INTO study_runs
            (id, study_id, study_mode, status, created_at, data_origin, verification_status, is_demo, notes, created_by_worker)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                study_id,
                mode,
                "active",
                now,
                provenance["data_origin"],
                provenance["verification_status"],
                1 if provenance["is_demo"] else 0,
                notes,
                "PX-H001",
            ),
        )
    add_event(db_path, "StudyRunCreated", "PX-H001", "Golden Study run created", mode, run_id)
    return get_study_run(db_path, run_id)


def get_study_run(db_path: str | Path, run_id: str) -> dict[str, object]:
    with connect(db_path) as connection:
        row = connection.execute("SELECT * FROM study_runs WHERE id = ?", (run_id,)).fetchone()
    if row is None:
        raise ValueError(f"Study run not found: {run_id}")
    return row_to_dict(row)


def close_active_study_run(db_path: str | Path, study_id: str, reason: str = "") -> dict[str, object] | None:
    run = get_active_study_run(db_path, study_id)
    if not run:
        return None
    with connect(db_path) as connection:
        connection.execute(
            "UPDATE study_runs SET status = 'closed', closed_at = ?, notes = ? WHERE id = ?",
            (utc_now(), reason or str(run.get("notes") or ""), run["id"]),
        )
    add_event(db_path, "StudyRunClosed", "PX-H001", "Golden Study run closed", reason, str(run["id"]))
    return get_study_run(db_path, str(run["id"]))


def switch_study_run_mode(
    db_path: str | Path,
    study_id: str,
    target_mode: str,
    production_confirmed: bool = False,
) -> dict[str, object]:
    mode = target_mode if target_mode in {"demo", "production"} else "demo"
    if mode == "production" and not production_confirmed:
        raise ValueError("Production GS-001 creation requires explicit confirmation.")
    active = get_active_study_run(db_path, study_id)
    if active and active["study_mode"] == mode:
        return active
    if active:
        if active["study_mode"] == "demo":
            archive_run_records(db_path, study_id, str(active["id"]), demo_only=True)
        close_active_study_run(db_path, study_id, f"Switched to {mode} run.")
    run = create_study_run(
        db_path,
        study_id,
        mode,
        "manual" if mode == "production" else "demo",
        f"Active {mode} run for {study_id}.",
    )
    with connect(db_path) as connection:
        connection.execute(
            """
            UPDATE studies
            SET study_mode = ?, data_origin = ?, verification_status = ?, is_demo = ?, last_updated = ?
            WHERE id = ?
            """,
            (
                mode,
                "manual" if mode == "production" else "demo",
                "pending_review" if mode == "production" else "unverified",
                0 if mode == "production" else 1,
                utc_now(),
                study_id,
            ),
        )
    return run


def archive_run_records(db_path: str | Path, study_id: str, study_run_id: str, demo_only: bool = True) -> list[dict[str, object]]:
    archived = []
    with connect(db_path) as connection:
        for table_name in RUN_SCOPED_TABLES:
            demo_clause = "AND is_demo = 1" if demo_only else ""
            rows = connection.execute(
                f"""
                SELECT id FROM {table_name}
                WHERE study_id = ? AND study_run_id = ? AND status != 'archived'
                {demo_clause}
                """,
                (study_id, study_run_id),
            ).fetchall()
            archived.extend({"table": table_name, "id": row["id"]} for row in rows)
    for row in archived:
        archive_record(db_path, str(row["table"]), str(row["id"]))
    return archived


def archive_all_demo_data(db_path: str | Path, study_id: str = DEFAULT_STUDY_ID) -> dict[str, object]:
    """Archive demo records and demo runs while preserving traceability."""
    archived: list[dict[str, object]] = []
    with connect(db_path) as connection:
        for table_name in RUN_SCOPED_TABLES:
            rows = connection.execute(
                f"""
                SELECT id FROM {table_name}
                WHERE study_id = ? AND is_demo = 1 AND status != 'archived'
                """,
                (study_id,),
            ).fetchall()
            archived.extend({"table": table_name, "id": row["id"]} for row in rows)
    for row in archived:
        archive_record(db_path, str(row["table"]), str(row["id"]))

    now = utc_now()
    with connect(db_path) as connection:
        demo_runs = connection.execute(
            """
            SELECT id, status FROM study_runs
            WHERE study_id = ? AND study_mode = 'demo' AND status != 'archived'
            """,
            (study_id,),
        ).fetchall()
        for run in demo_runs:
            connection.execute(
                """
                UPDATE study_runs
                SET status = 'archived', closed_at = COALESCE(closed_at, ?), notes = ?
                WHERE id = ?
                """,
                (now, "Demo data archived through Golden Study cleanup action.", run["id"]),
            )
        counts = {
            table_name: sum(1 for row in archived if row["table"] == table_name)
            for table_name in RUN_SCOPED_TABLES
        }
    add_event(
        db_path,
        "DemoDataArchived",
        "PX-H001",
        "Golden Study demo data archived instead of deleted",
        json.dumps(counts, ensure_ascii=False),
        study_id,
    )
    return {
        "study_id": study_id,
        "status": "archived",
        "records_archived": len(archived),
        "runs_archived": len(demo_runs),
        "counts": counts,
    }


def archive_current_production_run_and_start_fresh(db_path: str | Path, study_id: str = DEFAULT_STUDY_ID) -> dict[str, object]:
    active = get_active_study_run(db_path, study_id)
    if not active or active.get("study_mode") != "production":
        raise ValueError("Archive-and-reset is only available for an active production run.")
    run_id = str(active["id"])
    archived_records = archive_run_records(db_path, study_id, run_id, demo_only=False)
    note = "Archived before evidence-quality rerun. Records preserved for traceability under original study_run_id."
    with connect(db_path) as connection:
        connection.execute(
            "UPDATE study_runs SET status = 'archived', closed_at = ?, notes = ? WHERE id = ?",
            (utc_now(), note, run_id),
        )
    new_run = create_study_run(
        db_path,
        study_id,
        "production",
        "manual",
        "Clean production run started after evidence-quality reset.",
    )
    with connect(db_path) as connection:
        connection.execute(
            """
            UPDATE studies
            SET study_mode = 'production', data_origin = 'manual', verification_status = 'pending_review',
                is_demo = 0, last_updated = ?
            WHERE id = ?
            """,
            (utc_now(), study_id),
        )
    add_event(db_path, "ProductionRunArchived", "PX-H001", "Current production run archived. New clean production run started.", run_id, study_id)
    return {
        "status": "completed",
        "message": "Current production run archived. New clean production run started.",
        "archived_run_id": run_id,
        "new_run_id": new_run["id"],
        "records_archived": len(archived_records),
        "archived_records": archived_records,
    }


def delete_archived_demo_data(db_path: str | Path, study_id: str = DEFAULT_STUDY_ID) -> dict[str, object]:
    deleted: dict[str, int] = {}
    with connect(db_path) as connection:
        for table_name in RUN_SCOPED_TABLES:
            rows = connection.execute(
                f"SELECT id FROM {table_name} WHERE study_id = ? AND is_demo = 1 AND status = 'archived'",
                (study_id,),
            ).fetchall()
            deleted[table_name] = len(rows)
            connection.execute(
                f"DELETE FROM {table_name} WHERE study_id = ? AND is_demo = 1 AND status = 'archived'",
                (study_id,),
            )
        runs = connection.execute(
            "SELECT id FROM study_runs WHERE study_id = ? AND is_demo = 1 AND status = 'archived'",
            (study_id,),
        ).fetchall()
        deleted["study_runs"] = len(runs)
        connection.execute(
            "DELETE FROM study_runs WHERE study_id = ? AND is_demo = 1 AND status = 'archived'",
            (study_id,),
        )
    add_event(db_path, "ArchivedDemoDataDeleted", "PX-H001", "Archived demo data deleted by admin action.", str(sum(deleted.values())), study_id)
    return {"status": "completed", "deleted": deleted, "records_deleted": sum(deleted.values())}


def assign_legacy_records_to_runs(db_path: str | Path, study_id: str, active_run_id: str) -> None:
    demo_run_id = ensure_demo_history_run(db_path, study_id)
    with connect(db_path) as connection:
        for table_name in RUN_SCOPED_TABLES:
            columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()}
            if "study_run_id" not in columns:
                continue
            connection.execute(
                f"UPDATE {table_name} SET study_run_id = ? WHERE study_id = ? AND study_run_id IS NULL AND is_demo = 1",
                (demo_run_id, study_id),
            )
            connection.execute(
                f"UPDATE {table_name} SET study_run_id = ? WHERE study_id = ? AND study_run_id IS NULL AND COALESCE(is_demo, 0) = 0",
                (active_run_id, study_id),
            )


def ensure_demo_history_run(db_path: str | Path, study_id: str) -> str:
    with connect(db_path) as connection:
        row = connection.execute(
            "SELECT id FROM study_runs WHERE study_id = ? AND study_mode = 'demo' ORDER BY created_at ASC LIMIT 1",
            (study_id,),
        ).fetchone()
        if row:
            return str(row["id"])
        run_id = next_sequence_id("GSR", count_rows(connection, "study_runs"))
        now = utc_now()
        connection.execute(
            """
            INSERT INTO study_runs
            (id, study_id, study_mode, status, created_at, data_origin, verification_status, is_demo, notes, created_by_worker)
            VALUES (?, ?, 'demo', 'archived', ?, 'demo', 'unverified', 1, ?, 'PX-H001')
            """,
            (run_id, study_id, now, "Legacy demo/history run."),
        )
    return run_id


def create_signal(
    db_path: str | Path,
    raw_text: str,
    study_id: str = DEFAULT_STUDY_ID,
    source_url: str = "",
    source_name: str = "",
    source_type: str = "manual",
    source_date: str = "",
    country: str = "",
    stakeholder_type: str = "",
    company_product: str = "",
    data_origin: str = "demo",
    source_confidence: float | None = None,
) -> dict[str, object]:
    if not raw_text.strip():
        raise ValueError("Signal raw_text is required")
    study = get_or_create_default_study(db_path) if study_id == DEFAULT_STUDY_ID else get_study(db_path, study_id)
    if not study:
        raise ValueError(f"Study not found: {study_id}")
    active_run = get_active_study_run(db_path, study_id)
    if not active_run:
        raise ValueError(f"Study has no active run: {study_id}")
    origin = normalize_data_origin(data_origin)
    if source_url.strip() and origin == "demo":
        origin = "manual"
    if origin != "demo":
        if origin == "demo":
            raise ValueError("Production evidence cannot use demo data_origin.")
        if not (source_url.strip() or source_name.strip()):
            raise ValueError("Non-demo evidence requires a Source URL or Source name.")
        if str(active_run["study_mode"]) != "production":
            raise ValueError("Start a production run before adding production evidence.")
        if demo_records_count(db_path, study_id, str(active_run["id"])) > 0:
            raise ValueError("Archive demo records before adding production evidence.")
        quality = evidence_quality_profile(f"{source_name}\n{raw_text}", url=source_url, title=source_name, source_type_hint=source_type or origin)
        if not quality["accepted_complaint_evidence"]:
            raise ValueError(str(quality.get("rejection_reason") or "Production evidence must describe a real complaint, operational pain, or workflow inefficiency in property maintenance context."))
    elif str(active_run["study_mode"]) == "production":
        raise ValueError("Production studies cannot contain demo records.")
    elif non_demo_records_count(db_path, study_id, str(active_run["id"])) > 0:
        raise ValueError("Demo evidence cannot be added after production evidence has started.")
    enriched = enrich_signal(raw_text, country, stakeholder_type, company_product)
    provenance = provenance_values(origin, "PX-R001", source_confidence)
    if origin != "demo":
        provenance["verification_status"] = "pending_review"
        provenance["is_demo"] = False
    with connect(db_path) as connection:
        signal_id = next_sequence_id("SIG", count_rows(connection, "study_signals"))
        now = utc_now()
        connection.execute(
            """
            INSERT INTO study_signals
            (id, study_id, study_run_id, source_url, source_name, source_type, source_date, country, stakeholder_type,
             company_product, raw_text, complaint_category, summary, sentiment, evidence_strength,
             duplicate_group, status, created_at, data_origin, verification_status, is_demo, source_confidence,
             created_by_worker, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                signal_id,
                study_id,
                active_run["id"],
                source_url,
                source_name,
                source_type,
                source_date,
                enriched["country"],
                enriched["stakeholder_type"],
                enriched["company_product"],
                raw_text,
                enriched["complaint_category"],
                enriched["summary"],
                enriched["sentiment"],
                enriched["evidence_strength"],
                enriched["duplicate_group"],
                "active",
                now,
                provenance["data_origin"],
                provenance["verification_status"],
                1 if provenance["is_demo"] else 0,
                provenance["source_confidence"],
                provenance["created_by_worker"],
                now,
            ),
        )
    add_event(db_path, "StudySignalCreated", "PX-R001", "PX-R001 created study signal", study_id, signal_id)
    return get_signal(db_path, signal_id)


def get_signal(db_path: str | Path, signal_id: str) -> dict[str, object]:
    with connect(db_path) as connection:
        row = connection.execute("SELECT * FROM study_signals WHERE id = ?", (signal_id,)).fetchone()
    if row is None:
        raise ValueError(f"Signal not found: {signal_id}")
    return row_to_dict(row)


def list_signals(
    db_path: str | Path,
    study_id: str = DEFAULT_STUDY_ID,
    study_run_id: str | None = None,
    include_archived: bool = False,
    include_demo: bool = False,
) -> list[dict[str, object]]:
    run_id = study_run_id or str((get_active_study_run(db_path, study_id) or {}).get("id") or "")
    where, params = run_filter(study_id, run_id, include_archived, include_demo)
    with connect(db_path) as connection:
        rows = connection.execute(f"SELECT * FROM study_signals WHERE {where} ORDER BY created_at DESC", params).fetchall()
    return [row_to_dict(row) for row in rows]


def enrich_signal(raw_text: str, country: str, stakeholder_type: str, company_product: str) -> dict[str, object]:
    text = raw_text.strip()
    category = consolidate_category(text, choose_from_keywords(text, CATEGORY_KEYWORDS, "Poor customer experiences"))
    inferred_country = country or infer_country(text)
    inferred_stakeholder = stakeholder_type or choose_from_keywords(text, STAKEHOLDER_KEYWORDS, "Property managers")
    product = company_product or infer_product(text)
    sentiment = "negative" if any(word in text.lower() for word in ["complain", "slow", "poor", "expensive", "frustrating", "missing"]) else "mixed"
    strength = evidence_strength(text, bool(country or inferred_country), bool(product))
    summary = summarize(text)
    duplicate_group = normalize_group(f"{category} {summary}")
    return {
        "country": inferred_country,
        "stakeholder_type": inferred_stakeholder,
        "company_product": product,
        "complaint_category": category,
        "summary": summary,
        "sentiment": sentiment,
        "evidence_strength": strength,
        "duplicate_group": duplicate_group,
    }


def consolidate_category(text: str, category: str) -> str:
    lower = text.lower()
    maintenance_terms = ["maintenance", "repair", "contractor", "coordination"]
    communication_terms = ["communication", "update", "response", "tenant", "chase", "follow-up", "manual", "slow"]
    if any(term in lower for term in maintenance_terms) and any(term in lower for term in communication_terms):
        return "Maintenance communication issues"
    return category


def signal_semantic_text(signal: dict[str, object]) -> str:
    quality = signal_quality_metadata(signal)
    pain = quality.get("operational_pain") if isinstance(quality.get("operational_pain"), dict) else {}
    metadata = provider_signal_metadata(signal)
    parts = [
        str(metadata.get("original_title") or ""),
        str(signal.get("source_name") or ""),
        str(signal.get("summary") or ""),
        str(signal.get("raw_text") or ""),
        str(pain.get("what_pain") or ""),
        str(pain.get("why_it_occurs") or ""),
        str(pain.get("evidence_quote") or ""),
        str(pain.get("root_cause") or ""),
        str(signal.get("stakeholder_type") or ""),
        str(signal.get("complaint_category") or ""),
    ]
    return " ".join(part for part in parts if part).strip()


def signal_scope_text(signal: dict[str, object]) -> str:
    metadata = provider_signal_metadata(signal)
    parts = [
        str(metadata.get("original_title") or ""),
        str(signal.get("source_name") or ""),
        str(signal.get("summary") or ""),
        str(signal.get("raw_text") or ""),
        str(signal.get("stakeholder_type") or ""),
        str(signal.get("complaint_category") or ""),
        str(signal.get("source_url") or ""),
    ]
    return " ".join(part for part in parts if part).strip()


def is_signal_in_gs001_scope(signal: dict[str, object]) -> bool:
    text = signal_scope_text(signal).lower()
    property_context = any(
        keyword in text
        for keyword in [
            "residential",
            "property",
            "housing",
            "tenant",
            "resident",
            "landlord",
            "property manager",
            "apartment",
            "rental",
            "homeowner",
            "hoa",
        ]
    )
    maintenance_context = any(
        keyword in text
        for keyword in [
            "maintenance",
            "repair",
            "work order",
            "complaint handling",
            "complaint",
            "communication",
            "update",
            "follow-up",
            "maladministration",
            "redress",
            "habitability",
        ]
    )
    return property_context and maintenance_context and has_required_gs001_maintenance_context(text)


def canonical_pain_category(signal: dict[str, object]) -> dict[str, object]:
    text = signal_semantic_text(signal).lower()
    quality = signal_quality_metadata(signal)
    if not is_accepted_production_signal(signal):
        return {
            "canonical_category": str(quality.get("classification") or "Context Only").replace("_", " ").title(),
            "canonical_summary": "Signal is not production-eligible evidence for GS-001.",
            "matched_reasons": [str(quality.get("rejection_reason") or "Not production eligible")],
            "scope_status": "context_only",
            "confidence": 20,
        }
    if not is_signal_in_gs001_scope(signal):
        return {
            "canonical_category": "Out of Scope",
            "canonical_summary": "Evidence does not directly support GS-001 maintenance communication pain.",
            "matched_reasons": ["Missing residential/property context or maintenance communication context"],
            "scope_status": "out_of_scope",
            "confidence": 30,
        }

    best_category = "Maintenance Communication Failure"
    best_matches: list[str] = []
    for category, config in CANONICAL_GS001_CLUSTERS.items():
        matches = [pattern for pattern in config["patterns"] if pattern in text]
        if category == "Accounting / Payment Issues" and matches and not any(term in text for term in ["maintenance", "repair", "work order", "complaint handling"]):
            return {
                "canonical_category": category,
                "canonical_summary": str(config["summary"]),
                "matched_reasons": matches,
                "scope_status": "out_of_scope",
                "confidence": 60,
            }
        if len(matches) > len(best_matches):
            best_category = category
            best_matches = matches
    if not best_matches and any(term in text for term in ["update", "communicat", "response", "follow-up", "explain"]):
        best_matches = ["semantic communication/update language"]
        best_category = "Maintenance Communication Failure"
    elif not best_matches and any(term in text for term in ["delay", "unresolved", "ignored", "months", "not completed"]):
        best_matches = ["semantic repair delay language"]
        best_category = "Maintenance Delay / Repair Delay"
    elif not best_matches and "complaint" in text:
        best_matches = ["semantic complaint handling language"]
        best_category = "Complaint Handling Failure"
    if best_category != "Maintenance Communication Failure" and any(term in text for term in ["update", "updates", "communicat", "follow-up", "response", "not updated", "repair communication", "complaint handling"]):
        best_category = "Maintenance Communication Failure"
        best_matches = sorted(set([*best_matches, "semantic maintenance communication context"]))

    confidence = min(100, 65 + len(best_matches) * 8 + int(quality.get("authority_score") or quality.get("source_trust_score") or 0) // 10)
    return {
        "canonical_category": best_category,
        "canonical_summary": str(CANONICAL_GS001_CLUSTERS[best_category]["summary"]),
        "matched_reasons": best_matches or ["Accepted GS-001 operational pain"],
        "scope_status": "in_scope",
        "confidence": confidence,
    }


def build_evidence_clusters(signals: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, dict[str, object]] = {}
    excluded = 0
    for signal in signals:
        canonical = canonical_pain_category(signal)
        category = str(canonical["canonical_category"])
        cluster = grouped.setdefault(
            category,
            {
                "canonical_category": category,
                "canonical_summary": canonical["canonical_summary"],
                "supporting_signal_ids": [],
                "signals": [],
                "independent_source_domains": set(),
                "independent_organisations": set(),
                "independent_events": set(),
                "countries": set(),
                "stakeholders": set(),
                "trust_scores": [],
                "evidence_strengths": [],
                "source_dates": [],
                "representative_quotes": [],
                "rejected_or_context_signals_excluded": 0,
                "scope_status": canonical["scope_status"],
                "matched_reasons": [],
            },
        )
        if canonical["scope_status"] != "in_scope" or not is_accepted_production_signal(signal):
            cluster["rejected_or_context_signals_excluded"] = int(cluster["rejected_or_context_signals_excluded"]) + 1
            excluded += 1
            continue
        quality = signal_quality_metadata(signal)
        cluster["supporting_signal_ids"].append(str(signal["id"]))  # type: ignore[index]
        cluster["signals"].append(signal)  # type: ignore[index]
        cluster["independent_source_domains"].add(source_domain_or_identity(signal))  # type: ignore[union-attr]
        cluster["independent_organisations"].add(signal_organisation_identity(signal))  # type: ignore[union-attr]
        cluster["independent_events"].add(signal_market_event_id(signal))  # type: ignore[union-attr]
        cluster["countries"].add(str(signal.get("country") or "Unknown"))  # type: ignore[union-attr]
        cluster["stakeholders"].add(str(signal.get("stakeholder_type") or "Unknown"))  # type: ignore[union-attr]
        cluster["trust_scores"].append(int(quality.get("authority_score") or quality.get("source_trust_score") or 0))  # type: ignore[index]
        cluster["evidence_strengths"].append(int(signal.get("evidence_strength") or 0))  # type: ignore[index]
        if signal.get("source_date"):
            cluster["source_dates"].append(str(signal.get("source_date")))  # type: ignore[index]
        cluster["representative_quotes"].append(str((quality.get("operational_pain") or {}).get("evidence_quote") or signal.get("summary") or signal.get("raw_text") or "")[:240])  # type: ignore[index]
        cluster["matched_reasons"].extend(str(reason) for reason in canonical.get("matched_reasons", []))  # type: ignore[union-attr]

    clusters = []
    for cluster in grouped.values():
        trust_scores = list(cluster.pop("trust_scores"))  # type: ignore[arg-type]
        evidence_strengths = list(cluster.pop("evidence_strengths"))  # type: ignore[arg-type]
        source_dates = sorted(set(cluster.pop("source_dates")))  # type: ignore[arg-type]
        signal_count = len(cluster["supporting_signal_ids"])  # type: ignore[arg-type]
        domains = sorted(cluster["independent_source_domains"])  # type: ignore[arg-type]
        organisations = sorted(cluster["independent_organisations"])  # type: ignore[arg-type]
        events = sorted(cluster["independent_events"])  # type: ignore[arg-type]
        countries = sorted(cluster["countries"])  # type: ignore[arg-type]
        stakeholders = sorted(cluster["stakeholders"])  # type: ignore[arg-type]
        average_trust = round(sum(trust_scores) / len(trust_scores), 1) if trust_scores else 0
        evidence_score = min(100, round(average_trust + min(len(domains) * 2, 8) + min(len(events) * 3, 12))) if signal_count else 0
        pain_score = min(100, round((sum(evidence_strengths) / len(evidence_strengths)) + 10)) if evidence_strengths else 0
        status, why = cluster_finding_status(signal_count, domains, organisations, events, average_trust, str(cluster["scope_status"]))
        clusters.append(
            {
                "canonical_category": cluster["canonical_category"],
                "canonical_summary": cluster["canonical_summary"],
                "supporting_signal_ids": cluster["supporting_signal_ids"],
                "supporting_signals": cluster["signals"],
                "independent_source_domains": domains,
                "independent_organisations": organisations,
                "independent_events": events,
                "countries": countries,
                "stakeholders": stakeholders,
                "average_trust_score": average_trust,
                "evidence_score": evidence_score,
                "pain_score": pain_score,
                "earliest_evidence_date": source_dates[0] if source_dates else "",
                "latest_evidence_date": source_dates[-1] if source_dates else "",
                "representative_quotes": [quote for quote in cluster["representative_quotes"] if quote][:5],
                "rejected_or_context_signals_excluded": int(cluster["rejected_or_context_signals_excluded"]) + excluded if str(cluster["scope_status"]) == "in_scope" else int(cluster["rejected_or_context_signals_excluded"]),
                "scope_status": cluster["scope_status"],
                "matched_reasons": sorted(set(cluster["matched_reasons"])),
                "status": status,
                "why": why,
            }
        )
    return sorted(clusters, key=lambda item: (item["scope_status"] != "in_scope", -len(item["supporting_signal_ids"]), str(item["canonical_category"])))


def cluster_finding_status(
    signal_count: int,
    domains: list[str],
    organisations: list[str],
    events: list[str],
    average_trust: float,
    scope_status: str,
) -> tuple[str, str]:
    if scope_status == "out_of_scope":
        return "Out of scope for GS-001", "Evidence does not directly support maintenance communication pain."
    if scope_status == "context_only":
        return "Context only", "Evidence is not production-eligible and cannot support a finding."
    missing = []
    if signal_count < 3:
        missing.append(f"{signal_count}/3 production-eligible signals")
    if len(domains) < 2:
        missing.append(f"{len(domains)}/2 independent domains")
    if max(len(organisations), len(events)) < 2:
        missing.append(f"{len(organisations)} organisations and {len(events)} events; need 2 of either")
    if average_trust < MIN_PRODUCTION_AUTHORITY_SCORE:
        missing.append(f"average trust {average_trust}/{MIN_PRODUCTION_AUTHORITY_SCORE}")
    if missing:
        return "Evidence Cluster - Needs More Evidence", "Thresholds not met: " + "; ".join(missing)
    return "Draft finding ready", "Multiple independent sources describe repeated maintenance communication pain."


def choose_from_keywords(text: str, groups: dict[str, list[str]], fallback: str) -> str:
    lower = text.lower()
    best = fallback
    best_score = 0
    for group, keywords in groups.items():
        score = sum(1 for keyword in keywords if keyword.lower() in lower)
        if score > best_score:
            best = group
            best_score = score
    return best


def infer_country(text: str) -> str:
    lower = text.lower()
    for country in COUNTRY_HINTS:
        if country.lower() in lower:
            return country
    return "Unknown"


def infer_product(text: str) -> str:
    matches = re.findall(r"\b[A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)?\b", text)
    ignored = {"Property", "Tenant", "Maintenance", "Ireland", "United Kingdom", "United States"}
    products = [match for match in matches if match not in ignored]
    return ", ".join(products[:3])


def evidence_strength(text: str, has_country: bool, has_product: bool) -> int:
    words = len(text.split())
    score = 35
    if words >= 20:
        score += 20
    if words >= 50:
        score += 15
    if has_country:
        score += 10
    if has_product:
        score += 10
    if any(word in text.lower() for word in ["repeatedly", "multiple", "always", "every week", "again"]):
        score += 10
    return min(score, 100)


def summarize(text: str) -> str:
    compact = " ".join(text.split())
    return compact.split(".")[0][:220] or "Evidence requires review"


def normalize_group(text: str) -> str:
    tokens = [token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 3]
    important = tokens[:10]
    return "-".join(important) or "general"


def generate_findings(db_path: str | Path, study_id: str = DEFAULT_STUDY_ID, min_signals: int = 2) -> list[dict[str, object]]:
    active_run = get_active_study_run(db_path, study_id)
    include_demo = bool(active_run and active_run.get("study_mode") == "demo")
    signals = [signal for signal in list_signals(db_path, study_id, include_demo=include_demo) if signal["status"] == "active"]
    if active_run and active_run.get("study_mode") == "production":
        clusters = build_evidence_clusters(signals)
        created = []
        for cluster in clusters:
            if cluster["status"] != "Draft finding ready":
                continue
            finding = upsert_finding(db_path, study_id, list(cluster["supporting_signals"]), cluster)
            created.append(finding)
        add_event(db_path, "StudyFindingsGenerated", "PX-R001", "PX-R001 generated study findings", str(len(created)), study_id)
        return created
    groups: dict[str, list[dict[str, object]]] = {}
    for signal in signals:
        key = str(signal["complaint_category"] or "Market problem")
        groups.setdefault(key, []).append(signal)

    created = []
    for grouped_signals in groups.values():
        if len(grouped_signals) < min_signals:
            continue
        finding = upsert_finding(db_path, study_id, grouped_signals)
        created.append(finding)
    add_event(db_path, "StudyFindingsGenerated", "PX-R001", "PX-R001 generated study findings", str(len(created)), study_id)
    return created


def upsert_finding(db_path: str | Path, study_id: str, signals: list[dict[str, object]], cluster: dict[str, object] | None = None) -> dict[str, object]:
    study_run_id = str(signals[0].get("study_run_id") or "")
    category = str((cluster or {}).get("canonical_category") or signals[0]["complaint_category"] or "Market problem")
    theme = category
    signal_ids = [str(signal["id"]) for signal in signals]
    sources = sorted({source_domain_or_identity(signal) for signal in signals})
    event_ids = sorted({signal_market_event_id(signal) for signal in signals})
    organisations = sorted({signal_organisation_identity(signal) for signal in signals})
    countries = sorted({str(signal.get("country") or "Unknown") for signal in signals})
    stakeholders = sorted({str(signal.get("stakeholder_type") or "Unknown") for signal in signals})
    products = sorted({str(signal.get("company_product") or "") for signal in signals if signal.get("company_product")})
    trust_scores = [int(signal_quality_metadata(signal).get("authority_score") or signal_quality_metadata(signal).get("source_trust_score") or 0) for signal in signals]
    avg_trust = round(sum(trust_scores) / len(trust_scores), 1) if trust_scores else 0
    confidence = min(100, round((sum(int(signal["evidence_strength"] or 0) for signal in signals) / len(signals)) + min(len(event_ids) * 8, 24) + min(len(sources) * 3, 12)))
    if len(event_ids) <= 1 and not any(bool(signal.get("is_demo")) for signal in signals):
        confidence = min(confidence, 65)
    problem = str((cluster or {}).get("canonical_summary") or f"{category} appears across {len(signals)} evidence items, {len(sources)} independent sources, and {len(event_ids)} independent market events.")
    evidence_summary = json.dumps(
        {
            "evidence_cluster": {
                "canonical_category": category,
                "canonical_summary": problem,
                "supporting_signal_ids": signal_ids,
                "independent_source_domains": sources,
                "independent_organisations": organisations,
                "independent_events": event_ids,
                "countries": countries,
                "stakeholders": stakeholders,
                "average_trust_score": avg_trust,
                "representative_quotes": [str(signal["summary"]) for signal in signals[:3]],
                "scope_status": str((cluster or {}).get("scope_status") or "in_scope"),
                "cluster_status": str((cluster or {}).get("status") or "Draft finding ready"),
                "why": str((cluster or {}).get("why") or ""),
            }
        },
        ensure_ascii=False,
    )
    contains_demo = any(bool(signal.get("is_demo")) for signal in signals)
    non_demo_only = not contains_demo
    accepted_only = all(is_accepted_production_signal(signal) for signal in signals) if non_demo_only else False
    required_signal_count = 2 if contains_demo else 3
    sufficient = len(signals) >= required_signal_count and len(sources) >= 2 and max(len(organisations), len(event_ids)) >= 2 and avg_trust >= MIN_PRODUCTION_AUTHORITY_SCORE and non_demo_only and accepted_only
    status = "Demo Finding" if contains_demo and len(signals) >= 2 else "pending_audit" if sufficient else "Insufficient Evidence"
    data_origin = "demo" if contains_demo else "verified_import"
    verification_status = "unverified" if contains_demo else "pending_review"
    confidence_reasoning = (
        f"{len(signals)} supporting signals, {len(sources)} independent sources, "
        f"{len(event_ids)} independent market events, {len(countries)} countries, {len(stakeholders)} stakeholder groups, "
        f"{len(organisations)} organisations, average authority {avg_trust}. "
        f"{'Contains demo evidence; rehearsal only.' if contains_demo else 'Accepted complaint evidence only.' if accepted_only else 'Production signals did not pass complaint evidence gate.'}"
    )

    with connect(db_path) as connection:
        existing = connection.execute(
            "SELECT * FROM study_findings WHERE study_id = ? AND study_run_id = ? AND theme = ? AND complaint_category = ? AND status != 'archived'",
            (study_id, study_run_id, theme, category),
        ).fetchone()
        now = utc_now()
        if existing:
            finding_id = existing["id"]
            connection.execute(
                """
                UPDATE study_findings
                SET signal_count = ?, independent_source_count = ?, countries = ?, stakeholder_types = ?,
                    products_mentioned = ?, representative_signals = ?, evidence_summary = ?,
                    research_confidence = ?, confidence_score = ?, country_count = ?, stakeholder_count = ?,
                    supporting_evidence_count = ?, contradictory_evidence_count = ?, confidence_reasoning = ?,
                    status = ?, data_origin = ?, verification_status = ?, is_demo = ?, source_confidence = ?,
                    last_updated = ?
                WHERE id = ?
                """,
                (
                    len(signals),
                    len(sources),
                    json.dumps(countries),
                    json.dumps(stakeholders),
                    json.dumps(products),
                    json.dumps(signal_ids),
                    evidence_summary,
                    confidence,
                    confidence,
                    len(countries),
                    len(stakeholders),
                    len(signals),
                    0,
                    confidence_reasoning,
                    status,
                    data_origin,
                    verification_status,
                    1 if contains_demo else 0,
                    confidence,
                    now,
                    finding_id,
                ),
            )
        else:
            finding_id = next_sequence_id("FND", count_rows(connection, "study_findings"))
            connection.execute(
                """
                INSERT INTO study_findings
                (id, study_id, study_run_id, theme, problem_statement, complaint_category, signal_count,
                 independent_source_count, countries, stakeholder_types, products_mentioned,
                 representative_signals, evidence_summary, research_confidence, confidence_score, country_count,
                 stakeholder_count, supporting_evidence_count, contradictory_evidence_count, confidence_reasoning,
                 status, created_at, data_origin, verification_status, is_demo, source_confidence, created_by_worker,
                 last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    finding_id,
                    study_id,
                    study_run_id,
                    theme,
                    problem,
                    category,
                    len(signals),
                    len(sources),
                    json.dumps(countries),
                    json.dumps(stakeholders),
                    json.dumps(products),
                    json.dumps(signal_ids),
                    evidence_summary,
                    confidence,
                    confidence,
                    len(countries),
                    len(stakeholders),
                    len(signals),
                    0,
                    confidence_reasoning,
                    status,
                    now,
                    data_origin,
                    verification_status,
                    1 if contains_demo else 0,
                    confidence,
                    "PX-R001",
                    now,
                ),
            )
    return get_finding(db_path, finding_id)


def get_finding(db_path: str | Path, finding_id: str) -> dict[str, object]:
    with connect(db_path) as connection:
        row = connection.execute("SELECT * FROM study_findings WHERE id = ?", (finding_id,)).fetchone()
    if row is None:
        raise ValueError(f"Finding not found: {finding_id}")
    return row_to_dict(row)


def list_findings(
    db_path: str | Path,
    study_id: str = DEFAULT_STUDY_ID,
    study_run_id: str | None = None,
    include_archived: bool = False,
    include_demo: bool = False,
) -> list[dict[str, object]]:
    run_id = study_run_id or str((get_active_study_run(db_path, study_id) or {}).get("id") or "")
    where, params = run_filter(study_id, run_id, include_archived, include_demo)
    with connect(db_path) as connection:
        rows = connection.execute(f"SELECT * FROM study_findings WHERE {where} ORDER BY created_at DESC", params).fetchall()
    return [row_to_dict(row) for row in rows]


def calculate_oci(scores: dict[str, int]) -> int:
    if "traceability_score" in scores:
        oci = round(
            scores["evidence_score"] * 0.25
            + scores["frequency_score"] * 0.15
            + scores["market_size_score"] * 0.15
            + scores["pain_severity_score"] * 0.15
            + scores["competition_gap_score"] * 0.10
            + scores["traceability_score"] * 0.20
        )
        if scores["traceability_score"] < 100:
            return min(oci, 60)
        return oci
    return round(
        scores["evidence_score"] * 0.20
        + scores["frequency_score"] * 0.15
        + scores["market_size_score"] * 0.15
        + scores["pain_severity_score"] * 0.15
        + scores["competition_gap_score"] * 0.10
        + (100 - scores["build_complexity_score"]) * 0.10
        + scores["commercial_potential_score"] * 0.10
        + scores["strategic_fit_score"] * 0.05
    )


def audit_finding(db_path: str | Path, finding_id: str) -> dict[str, object]:
    finding = get_finding(db_path, finding_id)
    is_demo_finding = bool(finding.get("is_demo"))
    if is_demo_finding and finding["status"] == "Insufficient Evidence" and len(_loads_list(finding.get("representative_signals"))) >= 2:
        with connect(db_path) as connection:
            connection.execute(
                "UPDATE study_findings SET status = ?, last_updated = ? WHERE id = ?",
                ("Demo Finding", utc_now(), finding_id),
            )
        finding = get_finding(db_path, finding_id)
    if finding["status"] not in {"pending_audit", "Demo Finding"}:
        raise ValueError("Finding is not auditable until it has at least 2 supporting non-demo signals from 2 independent sources.")
    if is_demo_finding and finding["status"] != "Demo Finding":
        raise ValueError("Demo findings must use the demo rehearsal audit path.")
    scores = score_finding(finding)
    signals = [get_signal(db_path, str(signal_id)) for signal_id in _loads_list(finding.get("representative_signals"))]
    contains_demo = any(bool(signal.get("is_demo")) for signal in signals) or bool(finding.get("is_demo"))
    traceability_complete = traceability_complete_for_signals(signals)
    accepted_production_signals = [signal for signal in signals if is_accepted_production_signal(signal)]
    independent_domains = {source_domain_or_identity(signal) for signal in accepted_production_signals}
    independent_events = {signal_market_event_id(signal) for signal in accepted_production_signals}
    independent_organisations = {signal_organisation_identity(signal) for signal in accepted_production_signals}
    countries = {str(signal.get("country") or "Unknown") for signal in accepted_production_signals}
    stakeholders = {str(signal.get("stakeholder_type") or "Unknown") for signal in accepted_production_signals}
    trust_scores = [int(signal_quality_metadata(signal).get("source_trust_score") or 0) for signal in accepted_production_signals]
    average_trust_score = round(sum(trust_scores) / len(trust_scores), 1) if trust_scores else 0
    excluded_classes = [
        str(signal_quality_metadata(signal).get("classification") or "unknown")
        for signal in signals
        if signal_quality_metadata(signal).get("classification") not in PRODUCTION_ELIGIBLE_CLASSIFICATIONS
    ]
    scores["traceability_score"] = 100 if traceability_complete else 40
    scores["evidence_score"] = min(scores["evidence_score"], int(average_trust_score or 0))
    scores["frequency_score"] = min(100, len(independent_events) * 20)
    scores["market_size_score"] = min(100, 40 + len(countries) * 15 + len(independent_domains) * 4)
    scores["pain_severity_score"] = min(scores["pain_severity_score"], max([int(signal.get("evidence_strength") or 0) for signal in accepted_production_signals], default=0) + 10)
    oci = calculate_oci(scores)
    if contains_demo:
        oci = 0
    production_requirements_met = (
        contains_demo
        or (
            len(independent_domains) >= MIN_OPPORTUNITY_INDEPENDENT_SOURCES
            and len(independent_events) >= MIN_OPPORTUNITY_INDEPENDENT_EVENTS
            and scores["evidence_score"] >= MIN_OPPORTUNITY_EVIDENCE_SCORE
            and scores["pain_severity_score"] >= MIN_OPPORTUNITY_PAIN_SCORE
            and oci >= MIN_OPPORTUNITY_CONFIDENCE
            and scores["traceability_score"] >= MIN_OPPORTUNITY_TRACEABILITY
            and len(countries) >= MIN_OPPORTUNITY_GEOGRAPHIC_DIVERSITY
            and len(stakeholders) >= MIN_OPPORTUNITY_STAKEHOLDER_DIVERSITY
            and len(independent_organisations) >= MIN_OPPORTUNITY_ORGANISATION_DIVERSITY
            and average_trust_score >= MIN_PRODUCTION_AUTHORITY_SCORE
            and traceability_complete
            and len(accepted_production_signals) == len(signals)
        )
    )
    decision = (
        "Demo Audited"
        if contains_demo
        else "Approve Opportunity"
        if oci >= 80 and production_requirements_met
        else "Needs More Evidence"
        if oci >= 60 or not production_requirements_met
        else "Reject"
    )
    missing = []
    if len(independent_domains) < MIN_OPPORTUNITY_INDEPENDENT_SOURCES and not contains_demo:
        missing.append(f"Minimum independent sources not met: {len(independent_domains)}/{MIN_OPPORTUNITY_INDEPENDENT_SOURCES}")
    if len(independent_events) < MIN_OPPORTUNITY_INDEPENDENT_EVENTS and not contains_demo:
        missing.append(f"Minimum independent market events not met: {len(independent_events)}/{MIN_OPPORTUNITY_INDEPENDENT_EVENTS}")
    if scores["evidence_score"] < MIN_OPPORTUNITY_EVIDENCE_SCORE and not contains_demo:
        missing.append(f"Evidence score below threshold: {scores['evidence_score']}/{MIN_OPPORTUNITY_EVIDENCE_SCORE}")
    if scores["pain_severity_score"] < MIN_OPPORTUNITY_PAIN_SCORE and not contains_demo:
        missing.append(f"Pain score below threshold: {scores['pain_severity_score']}/{MIN_OPPORTUNITY_PAIN_SCORE}")
    if oci < MIN_OPPORTUNITY_CONFIDENCE and not contains_demo:
        missing.append(f"Confidence below threshold: {oci}/{MIN_OPPORTUNITY_CONFIDENCE}")
    if len(countries) < MIN_OPPORTUNITY_GEOGRAPHIC_DIVERSITY and not contains_demo:
        missing.append(f"Minimum geographic diversity not met: {len(countries)}/{MIN_OPPORTUNITY_GEOGRAPHIC_DIVERSITY}")
    if len(stakeholders) < MIN_OPPORTUNITY_STAKEHOLDER_DIVERSITY and not contains_demo:
        missing.append(f"Minimum stakeholder diversity not met: {len(stakeholders)}/{MIN_OPPORTUNITY_STAKEHOLDER_DIVERSITY}")
    if len(independent_organisations) < MIN_OPPORTUNITY_ORGANISATION_DIVERSITY and not contains_demo:
        missing.append(f"Minimum organisation diversity not met: {len(independent_organisations)}/{MIN_OPPORTUNITY_ORGANISATION_DIVERSITY}")
    if len(accepted_production_signals) < 3 and not contains_demo:
        missing.append("At least 3 accepted complaint/pain signals required")
    if average_trust_score < MIN_PRODUCTION_AUTHORITY_SCORE and not contains_demo:
        missing.append(f"Average source authority score must be at least {MIN_PRODUCTION_AUTHORITY_SCORE}")
    if not contains_demo and len(accepted_production_signals) != len(signals):
        missing.append("Only complaint, operational pain, or workflow inefficiency evidence can support approval")
    if len(_loads_list(finding.get("countries"))) < 2:
        missing.append("More country coverage")
    if contains_demo:
        missing.append("Non-demo verified evidence required")
    if not traceability_complete:
        missing.append("Complete traceability to sources required")
    reasoning = (
        f"Finding has {finding['signal_count']} signals, {finding['independent_source_count']} independent sources, "
        f"{len(independent_events)} independent market events, {len(independent_organisations)} organisations, "
        f"average authority score {average_trust_score}, traceability score {scores['traceability_score']}, "
        f"excluded classes {excluded_classes or 'none'}, OCI {oci}, decision {decision}."
    )
    with connect(db_path) as connection:
        audit_id = next_sequence_id("FAD", count_rows(connection, "finding_audits"))
        now = utc_now()
        connection.execute(
            """
            INSERT INTO finding_audits
            (id, study_id, study_run_id, finding_id, decision, evidence_score, frequency_score, market_size_score,
             pain_severity_score, competition_gap_score, build_complexity_score, commercial_potential_score,
             strategic_fit_score, traceability_score, opportunity_confidence_index, final_oci, score_breakdown,
             oci_reasoning, missing_evidence_warnings, contradictions, missing_evidence, reasoning_summary,
             recommendation, status, created_at, data_origin, verification_status, is_demo, source_confidence,
             created_by_worker, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                audit_id,
                finding["study_id"],
                finding.get("study_run_id"),
                finding_id,
                decision,
                scores["evidence_score"],
                scores["frequency_score"],
                scores["market_size_score"],
                scores["pain_severity_score"],
                scores["competition_gap_score"],
                scores["build_complexity_score"],
                scores["commercial_potential_score"],
                scores["strategic_fit_score"],
                scores["traceability_score"],
                oci,
                oci,
                json.dumps(scores, ensure_ascii=False),
                explain_oci(scores, oci, contains_demo),
                json.dumps(missing, ensure_ascii=False),
                "No direct contradictions detected.",
                ", ".join(missing) if missing else "None",
                reasoning,
                "Create demo opportunity for rehearsal." if decision == "Demo Audited" else "Approve into Approved Opportunities." if decision == "Approve Opportunity" else "Collect more evidence before approval.",
                "Demo Audited" if contains_demo else "active",
                now,
                "demo" if contains_demo else "verified_import",
                "unverified" if contains_demo else "verified",
                1 if contains_demo else 0,
                scores["evidence_score"],
                "PX-A001",
                now,
            ),
        )
        connection.execute("UPDATE study_findings SET status = ? WHERE id = ?", ("Demo Audited" if contains_demo else "audited", finding_id))
    add_event(db_path, "FindingAudited", "PX-A001", "PX-A001 audited finding", decision, audit_id)
    return get_finding_audit(db_path, audit_id)


def score_finding(finding: dict[str, object]) -> dict[str, int]:
    signal_count = int(finding.get("signal_count") or 0)
    source_count = int(finding.get("independent_source_count") or 0)
    countries = len(_loads_list(finding.get("countries")))
    confidence = int(finding.get("research_confidence") or 0)
    category = str(finding.get("complaint_category") or "").lower()
    build_complexity = 35 if any(word in category for word in ["communication", "report", "manual", "integration"]) else 55
    return {
        "evidence_score": min(100, confidence),
        "frequency_score": min(100, signal_count * 35),
        "market_size_score": min(100, 55 + countries * 15 + source_count * 5),
        "pain_severity_score": 90 if any(word in category for word in ["maintenance", "payment", "communication", "expensive"]) else 75,
        "competition_gap_score": 80,
        "build_complexity_score": build_complexity,
        "commercial_potential_score": 85,
        "strategic_fit_score": 90,
    }


def traceability_complete_for_signals(signals: list[dict[str, object]]) -> bool:
    return bool(signals) and all(signal.get("source_url") or signal.get("source_name") for signal in signals)


def explain_oci(scores: dict[str, int], oci: int, contains_demo: bool) -> str:
    if contains_demo:
        return "OCI forced to 0 because demo evidence cannot approve an opportunity."
    if scores.get("traceability_score", 0) < 100:
        return f"OCI capped at {oci} because traceability is incomplete."
    return f"OCI {oci} derived from evidence, frequency, market size, pain severity, competition gap, and traceability scores."


def get_finding_audit(db_path: str | Path, audit_id: str) -> dict[str, object]:
    with connect(db_path) as connection:
        row = connection.execute("SELECT * FROM finding_audits WHERE id = ?", (audit_id,)).fetchone()
    if row is None:
        raise ValueError(f"Finding audit not found: {audit_id}")
    return row_to_dict(row)


def list_finding_audits(
    db_path: str | Path,
    study_id: str = DEFAULT_STUDY_ID,
    study_run_id: str | None = None,
    include_archived: bool = False,
    include_demo: bool = False,
) -> list[dict[str, object]]:
    run_id = study_run_id or str((get_active_study_run(db_path, study_id) or {}).get("id") or "")
    where, params = run_filter(study_id, run_id, include_archived, include_demo)
    with connect(db_path) as connection:
        rows = connection.execute(f"SELECT * FROM finding_audits WHERE {where} ORDER BY created_at DESC", params).fetchall()
    return [row_to_dict(row) for row in rows]


def approve_audited_opportunities(db_path: str | Path, study_id: str = DEFAULT_STUDY_ID) -> list[dict[str, object]]:
    approved = []
    active_run = get_active_study_run(db_path, study_id)
    run_id = str((active_run or {}).get("id") or "")
    is_demo_run = bool(active_run and active_run.get("study_mode") == "demo")
    with connect(db_path) as connection:
        rows = connection.execute(
            f"""
            SELECT finding_audits.*
            FROM finding_audits
            LEFT JOIN opportunity_records ON opportunity_records.audit_id = finding_audits.id
            WHERE finding_audits.study_id = ?
              AND finding_audits.study_run_id = ?
              AND finding_audits.status != 'archived'
              AND finding_audits.is_demo = ?
              AND finding_audits.decision = ?
              AND opportunity_records.id IS NULL
            ORDER BY finding_audits.created_at ASC
            """,
            (study_id, run_id, 1 if is_demo_run else 0, "Demo Audited" if is_demo_run else "Approve Opportunity"),
        ).fetchall()
    for row in rows:
        audit = row_to_dict(row)
        if bool(audit.get("is_demo")) and not is_demo_run:
            continue
        approved.append(create_opportunity_from_audit(db_path, audit))
    add_event(db_path, "OpportunitiesApproved", "PX-L001", "PX-L001 approved audited opportunities", str(len(approved)), study_id)
    return approved


def approve_opportunities(db_path: str | Path, study_id: str = DEFAULT_STUDY_ID) -> list[dict[str, object]]:
    return approve_audited_opportunities(db_path, study_id)


def promote_approved_opportunities(db_path: str | Path, study_id: str = DEFAULT_STUDY_ID) -> list[dict[str, object]]:
    return approve_audited_opportunities(db_path, study_id)


def create_opportunity_from_audit(db_path: str | Path, audit: dict[str, object]) -> dict[str, object]:
    finding = get_finding(db_path, str(audit["finding_id"]))
    signals = [get_signal(db_path, str(signal_id)) for signal_id in _loads_list(finding.get("representative_signals"))]
    is_demo_opportunity = bool(audit.get("is_demo")) or bool(finding.get("is_demo")) or any(bool(signal.get("is_demo")) for signal in signals)
    active_run = get_active_study_run(db_path, str(audit["study_id"]))
    if is_demo_opportunity and not (active_run and active_run.get("study_mode") == "demo" and audit.get("study_run_id") == active_run.get("id")):
        raise ValueError("Demo data cannot be approved into a real Opportunity.")
    now = utc_now()
    with connect(db_path) as connection:
        opportunity_id = next_sequence_id("OPP", count_rows(connection, "opportunity_records"))
        oci = int(audit["opportunity_confidence_index"] or 0)
        status = "Demo Opportunity" if is_demo_opportunity else "Approved Opportunity"
        engineering_status = "Demo Opportunity" if is_demo_opportunity else "Engineering Specification Required"
        traceability_complete = traceability_complete_for_signals(signals)
        connection.execute(
            """
            INSERT INTO opportunity_records
            (id, study_id, study_run_id, industry, market, problem, evidence_summary, evidence_count, independent_sources,
             countries, products_mentioned, stakeholder_types, customer_segments, current_solutions,
             strengths_existing_solutions, weaknesses_existing_solutions, opportunity_confidence_index,
             commercial_potential, estimated_market_size, estimated_build_complexity, recommended_component,
             recommended_pricing_model, recommended_market_entry, engineering_recommendation, problem_scope,
             target_users, required_inputs, expected_outputs, system_boundaries, traceability_chain_complete,
             non_demo_evidence_only, audit_id, finding_id, status, engineering_status, owner, version, created_at,
             last_updated, data_origin, verification_status, is_demo, source_confidence, created_by_worker)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                opportunity_id,
                audit["study_id"],
                audit.get("study_run_id"),
                "Property Management",
                "Property Management",
                finding["problem_statement"],
                finding["evidence_summary"],
                finding["signal_count"],
                finding["independent_source_count"],
                finding["countries"],
                finding["products_mentioned"],
                finding["stakeholder_types"],
                finding["stakeholder_types"],
                finding["products_mentioned"],
                "Existing products have market presence and workflow coverage.",
                "Repeated complaints indicate gaps in speed, communication, cost, or usability.",
                oci,
                "Demo" if is_demo_opportunity else "High" if oci >= ENGINEERING_READY_OCI else "Medium",
                "Global niche-to-large SaaS opportunity",
                "Low" if int(audit["build_complexity_score"] or 100) <= 40 else "Medium",
                recommended_component(finding),
                "Subscription with usage-based tiers",
                "Start with a narrow verified workflow and one stakeholder segment.",
                "",
                "",
                "",
                "",
                "",
                "",
                1 if traceability_complete else 0,
                0 if is_demo_opportunity else 1,
                audit["id"],
                finding["id"],
                status,
                engineering_status,
                "PX-H001",
                "v1.0",
                now,
                now,
                "demo" if is_demo_opportunity else "verified_import",
                "unverified" if is_demo_opportunity else "verified",
                1 if is_demo_opportunity else 0,
                audit.get("source_confidence"),
                "PX-L001",
            ),
        )
        connection.execute("UPDATE study_findings SET status = ? WHERE id = ?", ("Demo Opportunity" if is_demo_opportunity else "opportunity_approved", finding["id"]))
    add_notification(db_path, "demo_opportunity_created" if is_demo_opportunity else "opportunity_approved", f"{'Demo opportunity created' if is_demo_opportunity else 'Opportunity approved'}: {opportunity_id}", opportunity_id)
    return get_opportunity(db_path, opportunity_id)


def mark_engineering_ready(db_path: str | Path, opportunity_id: str, spec: dict[str, object]) -> dict[str, object]:
    opportunity = get_opportunity(db_path, opportunity_id)
    is_demo_opportunity = bool(opportunity.get("is_demo"))
    required = [
        "recommended_component",
        "engineering_recommendation",
        "problem_scope",
        "target_users",
        "required_inputs",
        "expected_outputs",
        "system_boundaries",
    ]
    merged = {field: spec.get(field) or opportunity.get(field) for field in required}
    missing = [field for field, value in merged.items() if not value]
    chain = traceability_chain(db_path, opportunity_id)
    non_demo = not any(bool(record.get("is_demo")) for record in [chain["opportunity"], chain["audit"], chain["finding"], *chain["signals"]])
    traceability_complete = bool(chain["signals"]) and bool(chain["sources"])
    if missing or (not is_demo_opportunity and not non_demo) or not traceability_complete:
        return {"status": "blocked", "missing_fields": missing, "non_demo_evidence_only": non_demo, "traceability_chain_complete": traceability_complete}
    with connect(db_path) as connection:
        connection.execute(
            """
            UPDATE opportunity_records
            SET engineering_status = ?, status = ?, engineering_recommendation = ?, problem_scope = ?,
                target_users = ?, required_inputs = ?, expected_outputs = ?, system_boundaries = ?,
                traceability_chain_complete = ?, non_demo_evidence_only = ?, last_updated = ?
            WHERE id = ?
            """,
            (
                "Demo Engineering Ready" if is_demo_opportunity else "Engineering Ready",
                "Demo Engineering Ready" if is_demo_opportunity else "Engineering Ready",
                merged["engineering_recommendation"],
                merged["problem_scope"],
                merged["target_users"],
                merged["required_inputs"],
                merged["expected_outputs"],
                merged["system_boundaries"],
                1,
                1,
                utc_now(),
                opportunity_id,
            ),
        )
    return get_opportunity(db_path, opportunity_id)


def recommended_component(finding: dict[str, object]) -> str:
    category = str(finding.get("complaint_category") or "").lower()
    if "maintenance" in category:
        return "Maintenance Communication Component"
    if "payment" in category or "accounting" in category:
        return "Payment Reconciliation Component"
    if "report" in category:
        return "Property Reporting Component"
    if "integration" in category:
        return "Integration Sync Component"
    return "Workflow Automation Component"


def get_opportunity(db_path: str | Path, opportunity_id: str) -> dict[str, object]:
    with connect(db_path) as connection:
        row = connection.execute("SELECT * FROM opportunity_records WHERE id = ?", (opportunity_id,)).fetchone()
    if row is None:
        raise ValueError(f"Opportunity not found: {opportunity_id}")
    return row_to_dict(row)


def list_opportunities(
    db_path: str | Path,
    study_id: str = DEFAULT_STUDY_ID,
    study_run_id: str | None = None,
    include_archived: bool = False,
    include_demo: bool = False,
) -> list[dict[str, object]]:
    run_id = study_run_id or str((get_active_study_run(db_path, study_id) or {}).get("id") or "")
    where, params = run_filter(study_id, run_id, include_archived, include_demo)
    with connect(db_path) as connection:
        rows = connection.execute(f"SELECT * FROM opportunity_records WHERE {where} ORDER BY opportunity_confidence_index DESC, created_at DESC", params).fetchall()
    return [row_to_dict(row) for row in rows]


def archive_record(db_path: str | Path, table_name: str, record_id: str) -> dict[str, object]:
    allowed = {
        "study_signals": "id",
        "study_findings": "id",
        "finding_audits": "id",
        "opportunity_records": "id",
        "study_briefs": "id",
    }
    if table_name not in allowed:
        raise ValueError(f"Unsupported archive table: {table_name}")
    with connect(db_path) as connection:
        row = connection.execute(f"SELECT * FROM {table_name} WHERE {allowed[table_name]} = ?", (record_id,)).fetchone()
        if row is None:
            raise ValueError(f"Record not found: {record_id}")
        record = row_to_dict(row)
        now = utc_now()
        previous_status = str(record.get("status") or "")
        connection.execute(
            f"""
            UPDATE {table_name}
            SET status = ?, verification_status = ?, archive_reason = ?, archived_at = ?, archived_by = ?,
                previous_status = ?, last_updated = ?
            WHERE {allowed[table_name]} = ?
            """,
            ("archived", "archived", "Archived instead of deleted.", now, "PX-H001", previous_status, now, record_id),
        )
        if bool(record.get("is_demo")):
            connection.execute(
                """
                INSERT INTO demo_archive (table_name, record_id, record_json, archive_reason, archived_at, archived_by)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (table_name, record_id, json.dumps(record, ensure_ascii=False), "Archived demo data.", now, "PX-H001"),
            )
    add_event(db_path, "RecordArchived", "PX-H001", "Record archived instead of deleted", table_name, record_id)
    return {"table": table_name, "id": record_id, "status": "archived"}


def traceability_chain(db_path: str | Path, opportunity_id: str, include_archived: bool = False) -> dict[str, object]:
    opportunity = get_opportunity(db_path, opportunity_id)
    active_run = get_active_study_run(db_path, str(opportunity["study_id"]))
    if not include_archived:
        if opportunity.get("status") == "archived":
            raise ValueError("Archived opportunity traceability requires include_archived=True.")
        if active_run and opportunity.get("study_run_id") != active_run.get("id"):
            raise ValueError("Opportunity is not part of the active study run.")
    audit = get_finding_audit(db_path, str(opportunity["audit_id"]))
    finding = get_finding(db_path, str(opportunity["finding_id"]))
    signal_ids = _loads_list(finding.get("representative_signals"))
    signals = [get_signal(db_path, str(signal_id)) for signal_id in signal_ids]
    if not include_archived:
        signals = [signal for signal in signals if signal.get("status") != "archived" and signal.get("study_run_id") == opportunity.get("study_run_id")]
    sources = [
        {
            "signal_id": signal["id"],
            "source_url": signal.get("source_url"),
            "source_name": signal.get("source_name"),
            "source_type": signal.get("source_type"),
        }
        for signal in signals
    ]
    return {"opportunity": opportunity, "audit": audit, "finding": finding, "evidence_cluster": finding_cluster_metadata(finding), "signals": signals, "sources": sources}


def finding_evidence(db_path: str | Path, finding_id: str, include_archived: bool = False) -> dict[str, object]:
    finding = get_finding(db_path, finding_id)
    if not include_archived and finding.get("status") == "archived":
        raise ValueError("Archived finding evidence requires include_archived=True.")
    signals = [get_signal(db_path, str(signal_id)) for signal_id in _loads_list(finding.get("representative_signals"))]
    if not include_archived:
        signals = [signal for signal in signals if signal.get("status") != "archived" and signal.get("study_run_id") == finding.get("study_run_id")]
    return {"finding": finding, "evidence_cluster": finding_cluster_metadata(finding), "signals": signals}


def finding_cluster_metadata(finding: dict[str, object]) -> dict[str, object]:
    raw = str(finding.get("evidence_summary") or "")
    if raw.strip().startswith("{"):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {}
        if isinstance(parsed, dict) and isinstance(parsed.get("evidence_cluster"), dict):
            return parsed["evidence_cluster"]
    return {
        "canonical_category": finding.get("theme") or finding.get("complaint_category") or "Market problem",
        "canonical_summary": finding.get("problem_statement") or "",
        "supporting_signal_ids": _loads_list(finding.get("representative_signals")),
        "independent_source_domains": [],
        "independent_organisations": [],
        "independent_events": [],
        "scope_status": "legacy",
        "cluster_status": str(finding.get("status") or ""),
        "why": "Legacy finding created before semantic cluster metadata.",
    }


def study_progress(
    db_path: str | Path,
    study_id: str = DEFAULT_STUDY_ID,
    study_run_id: str | None = None,
    include_archived: bool = False,
    include_demo: bool = False,
) -> dict[str, object]:
    study = get_study(db_path, study_id)
    active_run = get_active_study_run(db_path, study_id)
    run_id = study_run_id or str((active_run or {}).get("id") or "")
    run = get_study_run(db_path, run_id) if run_id else None
    signals = list_signals(db_path, study_id, run_id, include_archived, include_demo)
    findings = list_findings(db_path, study_id, run_id, include_archived, include_demo)
    audits = list_finding_audits(db_path, study_id, run_id, include_archived, include_demo)
    opportunities = list_opportunities(db_path, study_id, run_id, include_archived, include_demo)
    archives = archived_count(db_path, study_id, run_id)
    demo_count = demo_records_count(db_path, study_id, run_id, include_archived)
    pending_verification = sum(1 for row in [*signals, *findings, *audits, *opportunities] if row.get("verification_status") in {"unverified", "pending_review", "pending_verification"})
    avg_oci_values = [int(opportunity.get("opportunity_confidence_index") or 0) for opportunity in opportunities]
    return {
        "study_id": study_id,
        "active_run_id": run_id,
        "run_status": str((run or {}).get("status") or ""),
        "study_mode": str((run or study or {}).get("study_mode") or "demo"),
        "signals_collected": len(signals),
        "findings_created": len(findings),
        "audits_completed": len(audits),
        "opportunities_approved": len([opportunity for opportunity in opportunities if opportunity["status"] in {"Approved Opportunity", "Engineering Ready", "Demo Opportunity", "Demo Engineering Ready"}]),
        "opportunities_rejected": len([audit for audit in audits if audit["decision"] == "Reject"]),
        "countries_covered": sorted({str(signal.get("country") or "Unknown") for signal in signals}),
        "stakeholders_covered": sorted({str(signal.get("stakeholder_type") or "Unknown") for signal in signals}),
        "source_coverage": len({str(signal.get("source_url") or signal.get("source_name") or signal["id"]) for signal in signals}),
        "engineering_ready": [opportunity for opportunity in opportunities if opportunity.get("engineering_status") in {"Engineering Ready", "Demo Engineering Ready"}],
        "top_opportunities": opportunities[:5],
        "weak_evidence": [finding for finding in findings if int(finding.get("research_confidence") or 0) < 75],
        "average_oci": round(sum(avg_oci_values) / len(avg_oci_values), 1) if avg_oci_values else 0,
        "high_priority_opportunities": [opportunity for opportunity in opportunities if int(opportunity.get("opportunity_confidence_index") or 0) >= ENGINEERING_READY_OCI],
        "archived_count": archives,
        "demo_records_count": demo_count,
        "verification_pending_count": pending_verification,
    }


def production_pipeline_statuses(progress: dict[str, object]) -> dict[str, str]:
    signals = int(progress.get("signals_collected") or 0)
    findings = int(progress.get("findings_created") or 0)
    audits = int(progress.get("audits_completed") or 0)
    opportunities = int(progress.get("opportunities_approved") or 0)
    specs = len(progress.get("top_opportunities") or []) if opportunities else 0
    engineering_ready = len(progress.get("engineering_ready") or [])

    return {
        "Evidence Collection": "Completed" if signals else "Active",
        "Signal Detection": "Completed" if signals else "Locked",
        "Finding Generation": "Completed" if findings else "Active" if signals else "Locked",
        "Audit": "Completed" if audits else "Active" if findings else "Locked",
        "Opportunity": "Completed" if opportunities else "Active" if audits else "Locked",
        "Engineering Spec": "Completed" if engineering_ready else "Active" if opportunities or specs else "Locked",
        "Prototype": "Locked",
        "Internal Validation": "Locked",
        "External Validation": "Locked",
        "Commercial Ready": "Locked",
    }


def evidence_quality_dashboard(signals: list[dict[str, object]], skipped: list[dict[str, object]] | None = None) -> dict[str, object]:
    qualities = [signal_quality_metadata(signal) for signal in signals]
    eligible = [quality for quality in qualities if quality.get("production_eligible")]
    trust_scores = [int(quality.get("source_trust_score") or 0) for quality in eligible]
    relevance_scores = [int(quality.get("operational_relevance_score") or 0) for quality in eligible]
    domains = {source_domain_or_identity(signal) for signal, quality in zip(signals, qualities) if quality.get("production_eligible")}
    classifications = [str(quality.get("classification") or "unknown") for quality in qualities]
    executive_tiers = [str(quality.get("executive_evidence_tier") or "") for quality in qualities]
    skipped = skipped or []
    return {
        "total_pulled": len(signals) + len(skipped),
        "accepted_production_signals": len(eligible),
        "tier_a_production_evidence": len([tier for tier in executive_tiers if tier.startswith("Tier A")]),
        "tier_b_supporting_evidence": len([tier for tier in executive_tiers if tier.startswith("Tier B")]),
        "tier_c_market_context": len([tier for tier in executive_tiers if tier.startswith("Tier C")]),
        "tier_d_rejected": len([tier for tier in executive_tiers if tier.startswith("Tier D")]) + len(skipped),
        "market_context": classifications.count("market_context"),
        "vendor_content": classifications.count("vendor_content"),
        "community_signals": classifications.count("community_signal"),
        "rejected": len([quality for quality in qualities if not quality.get("production_eligible")]) + len(skipped),
        "duplicates": len([item for item in skipped if item.get("reason") == "duplicate"]),
        "average_trust_score": round(sum(trust_scores) / len(trust_scores), 1) if trust_scores else 0,
        "average_operational_relevance_score": round(sum(relevance_scores) / len(relevance_scores), 1) if relevance_scores else 0,
        "independent_domains": len(domains),
        "production_readiness": "Ready for finding generation" if len(eligible) >= 3 and len(domains) >= 2 and (round(sum(trust_scores) / len(trust_scores), 1) if trust_scores else 0) >= 80 else "Needs stronger evidence",
    }


def source_readiness_assessment(source: dict[str, object]) -> dict[str, object]:
    score = 0
    accessible = str(source.get("accessible") or "Unknown")
    structured = str(source.get("structured") or "Unknown")
    automatable = str(source.get("automatable") or "Unknown")
    production_ready = str(source.get("production_ready") or "Unknown")
    method = str(source.get("collection_method") or "")
    if accessible == "YES":
        score += 25
    elif accessible == "Limited":
        score += 12
    if structured == "YES":
        score += 20
    elif structured == "Medium":
        score += 12
    elif structured == "Low":
        score += 5
    if automatable == "YES":
        score += 20
    elif automatable == "Limited":
        score += 10
    if "Production Ready" in production_ready:
        score += 25
    elif "Supporting" in production_ready or "Supplemental" in production_ready:
        score += 12
    elif "Market Context" in production_ready:
        score += 8
    if any(item in method for item in ["API", "Open Dataset", "RSS"]):
        score += 10
    if bool(source.get("authentication_required")) and "Search Provider" not in str(source.get("evidence_class") or ""):
        score -= 10
    score = max(0, min(100, score))
    label = "Production Ready" if score >= 80 else "Automatable Candidate" if score >= 65 else "Supporting Only" if score >= 45 else "Needs Review"
    return {"readiness_score": score, "readiness_label": label}


def ensure_data_source_registry(db_path: str | Path) -> None:
    now = utc_now()
    with connect(db_path) as connection:
        for source in GS_P001_PRIORITY_EVIDENCE_SOURCES:
            assessment = source_readiness_assessment(source)
            values = {
                **source,
                "evidence_tier": evidence_tier_for_class(str(source.get("evidence_class") or "Unknown")),
                "readiness_score": assessment["readiness_score"],
                "readiness_label": assessment["readiness_label"],
            }
            connection.execute(
                """
                INSERT INTO evidence_sources
                (id, source_name, organisation, evidence_class, evidence_tier, country, industry, authority_level,
                 trust_default, collection_method, authentication_required, rate_limits, update_frequency,
                 average_documents, production_ready, legal_terms_notes, supported_golden_studies, current_status,
                 accessible, structured, automatable, readiness_score, readiness_label, created_at, last_evaluated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    source_name = excluded.source_name,
                    organisation = excluded.organisation,
                    evidence_class = excluded.evidence_class,
                    evidence_tier = excluded.evidence_tier,
                    authority_level = excluded.authority_level,
                    trust_default = excluded.trust_default,
                    collection_method = excluded.collection_method,
                    authentication_required = excluded.authentication_required,
                    rate_limits = excluded.rate_limits,
                    update_frequency = excluded.update_frequency,
                    average_documents = excluded.average_documents,
                    production_ready = excluded.production_ready,
                    legal_terms_notes = excluded.legal_terms_notes,
                    supported_golden_studies = excluded.supported_golden_studies,
                    current_status = excluded.current_status,
                    accessible = excluded.accessible,
                    structured = excluded.structured,
                    automatable = excluded.automatable,
                    readiness_score = excluded.readiness_score,
                    readiness_label = excluded.readiness_label,
                    last_evaluated_at = excluded.last_evaluated_at
                """,
                (
                    values["id"],
                    values["source_name"],
                    values["organisation"],
                    values["evidence_class"],
                    values["evidence_tier"],
                    values.get("country", "United States"),
                    values.get("industry", "Residential Property Management"),
                    values["authority_level"],
                    values["trust_default"],
                    values["collection_method"],
                    1 if values.get("authentication_required") else 0,
                    values.get("rate_limits", ""),
                    values.get("update_frequency", ""),
                    values.get("average_documents", 0),
                    values["production_ready"],
                    values.get("legal_terms_notes", ""),
                    values.get("supported_golden_studies", DEFAULT_STUDY_ID),
                    values["current_status"],
                    values["accessible"],
                    values["structured"],
                    values["automatable"],
                    values["readiness_score"],
                    values["readiness_label"],
                    now,
                    now,
                ),
            )


def list_evidence_sources(db_path: str | Path, study_id: str = DEFAULT_STUDY_ID) -> list[dict[str, object]]:
    ensure_data_source_registry(db_path)
    with connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT * FROM evidence_sources
            WHERE supported_golden_studies LIKE ?
            ORDER BY evidence_tier ASC, readiness_score DESC, source_name ASC
            """,
            (f"%{study_id}%",),
        ).fetchall()
    return [row_to_dict(row) for row in rows]


def evidence_source_for_candidate(candidate: dict[str, object]) -> str:
    url = str(candidate.get("source_url") or "").lower()
    title = str(candidate.get("original_title") or "").lower()
    source_class = str(candidate.get("evidence_class") or "")
    combined = f"{url} {title}"
    if "hud.gov" in combined:
        return "EDS-HUD"
    if "housing-ombudsman" in combined or "ombudsman" in combined:
        return "EDS-HOUSING-AUTH"
    if "bbb.org" in combined:
        return "EDS-BBB"
    if "consumeraffairs" in combined or "consumer affairs" in combined:
        return "EDS-CONSUMER-AFFAIRS"
    if "court" in combined or source_class == "Court":
        return "EDS-COURTS"
    if "311" in combined:
        return "EDS-311"
    if "federalregister.gov" in combined:
        return "EDS-FEDERAL-REGISTER"
    if "attorney general" in combined or source_class == "Attorney General":
        return "EDS-AG"
    if source_class in {"Government", "Regulator", "Housing Authority"}:
        return "EDS-HOUSING-AUTH"
    if source_class == "Investigative Journalism":
        return "EDS-INVESTIGATIVE-NEWS"
    if source_class == "Tenant Advocacy":
        return "EDS-TENANT-ADVOCACY"
    return "EDS-SEARCH-PROVIDERS"


def data_source_health_dashboard(db_path: str | Path, study_id: str = DEFAULT_STUDY_ID) -> dict[str, object]:
    sources = list_evidence_sources(db_path, study_id)
    active_run = get_active_study_run(db_path, study_id)
    run_id = str((active_run or {}).get("id") or "")
    signals = list_signals(db_path, study_id, run_id, include_demo=bool(active_run and active_run.get("study_mode") == "demo")) if run_id else []
    quality = evidence_quality_dashboard(signals)
    today = utc_now()[:10]
    with connect(db_path) as connection:
        run_rows = connection.execute(
            """
            SELECT * FROM source_collection_runs
            WHERE study_id = ? AND created_at LIKE ?
            ORDER BY created_at DESC
            """,
            (study_id, f"{today}%"),
        ).fetchall()
    runs = [row_to_dict(row) for row in run_rows]
    working_methods = {str(source.get("collection_method") or "") for source in sources if str(source.get("readiness_label") or "") in {"Production Ready", "Automatable Candidate"}}
    failed = [source for source in sources if str(source.get("current_status") or "").lower() in {"failed", "error"}]
    coverage_by_industry = sorted({str(source.get("industry") or "Unknown") for source in sources})
    coverage_by_country = sorted({str(source.get("country") or "Unknown") for source in sources})
    coverage_by_study = sorted({item.strip() for source in sources for item in str(source.get("supported_golden_studies") or "").split(",") if item.strip()})
    production_ready_sources = [source for source in sources if source.get("readiness_label") == "Production Ready"]
    coverage_confidence = round((len(production_ready_sources) / len(sources)) * 100, 1) if sources else 0
    return {
        "sources": sources,
        "source_runs_today": runs,
        "tier_1_sources_configured": len([source for source in sources if int(source.get("evidence_tier") or 6) == 1]),
        "tier_2_sources_configured": len([source for source in sources if int(source.get("evidence_tier") or 6) == 2]),
        "working_apis": len([method for method in working_methods if "API" in method]),
        "working_crawlers": len([method for method in working_methods if "HTML" in method or "PDF" in method]),
        "working_rss_feeds": len([method for method in working_methods if "RSS" in method]),
        "working_search_providers": len([source for source in sources if source.get("evidence_class") == "Search Provider" and source.get("readiness_label") in {"Production Ready", "Automatable Candidate"}]),
        "failed_sources": len(failed),
        "collection_errors": len([run for run in runs if run.get("collection_error")]),
        "daily_documents_collected": sum(int(run.get("documents_collected") or 0) for run in runs),
        "accepted_production_evidence": quality["accepted_production_signals"],
        "rejected_evidence": quality["rejected"],
        "coverage_by_industry": coverage_by_industry,
        "coverage_by_country": coverage_by_country,
        "coverage_by_study": coverage_by_study,
        "coverage_confidence": coverage_confidence,
        "overall_health": "Healthy" if coverage_confidence >= 50 and not failed else "Developing" if sources else "Not configured",
    }


def archived_count(db_path: str | Path, study_id: str, study_run_id: str | None = None) -> int:
    run_id = study_run_id or str((get_active_study_run(db_path, study_id) or {}).get("id") or "")
    total = 0
    with connect(db_path) as connection:
        for table_name in RUN_SCOPED_TABLES:
            total += int(connection.execute(f"SELECT COUNT(*) AS count FROM {table_name} WHERE study_id = ? AND study_run_id = ? AND status = 'archived'", (study_id, run_id)).fetchone()["count"])
    return total


def generate_executive_brief(db_path: str | Path, study_id: str = DEFAULT_STUDY_ID) -> dict[str, object]:
    study = get_or_create_default_study(db_path) if study_id == DEFAULT_STUDY_ID else get_study(db_path, study_id)
    if not study:
        raise ValueError(f"Study not found: {study_id}")
    active_run = get_active_study_run(db_path, study_id)
    include_demo = bool(active_run and active_run.get("study_mode") == "demo")
    progress = study_progress(db_path, study_id)
    risks = []
    if not progress["countries_covered"]:
        risks.append("No country coverage yet.")
    if progress["signals_collected"] < 2:
        risks.append("Not enough repeated evidence for opportunity creation.")
    if progress["audits_completed"] == 0:
        risks.append("No findings audited yet.")
    missing = []
    if len(progress["countries_covered"]) < 2:
        missing.append("More countries")
    if progress["source_coverage"] < 2:
        missing.append("More independent sources")
    recommendation = (
        "Move engineering-ready opportunities into component planning."
        if progress["engineering_ready"]
        else "Collect more independent signals, then audit findings with repeated evidence."
    )
    body = (
        f"Study ID: {study_id}\n"
        f"Industry: Property Management\n"
        f"Market: {study['market']}\n"
        f"Signals collected: {progress['signals_collected']} signals\n"
        f"Findings created: {progress['findings_created']}\n"
        f"Audits completed: {progress['audits_completed']}\n"
        f"Approved Opportunities: {progress['opportunities_approved']}\n"
        f"Engineering Ready Opportunities: {len(progress['engineering_ready'])}\n"
        f"Countries covered: {', '.join(progress['countries_covered']) or 'None'}\n"
        f"Stakeholder types covered: {', '.join(progress['stakeholders_covered']) or 'None'}\n"
        f"Independent sources count: {progress['source_coverage']}\n"
        f"Highest OCI opportunities: {len(progress['top_opportunities'])}\n"
        f"Recommended next action: "
        f"{'Move engineering-ready opportunities into specification review.' if progress['engineering_ready'] else 'Collect verified non-demo evidence and audit only sufficiently supported findings.'}"
    )
    with connect(db_path) as connection:
        brief_id = next_sequence_id("GSB", count_rows(connection, "study_briefs"))
        connection.execute(
            """
            INSERT INTO study_briefs
            (id, study_id, study_run_id, brief_type, title, body, metrics, top_opportunities, risks, missing_evidence,
             engineering_recommendation, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                brief_id,
                study_id,
                str((active_run or {}).get("id") or ""),
                "executive",
                f"Executive Brief - {study_id}",
                body,
                json.dumps(progress, ensure_ascii=False),
                json.dumps(progress["top_opportunities"], ensure_ascii=False),
                json.dumps(risks, ensure_ascii=False),
                json.dumps(missing, ensure_ascii=False),
                recommendation,
                utc_now(),
            ),
        )
    add_event(db_path, "GoldenStudyBriefCreated", "PX-H001", "PX-H001 generated Golden Study executive brief", study_id, brief_id)
    return get_study_brief(db_path, brief_id)


def get_study_brief(db_path: str | Path, brief_id: str) -> dict[str, object]:
    with connect(db_path) as connection:
        row = connection.execute("SELECT * FROM study_briefs WHERE id = ?", (brief_id,)).fetchone()
    if row is None:
        raise ValueError(f"Study brief not found: {brief_id}")
    return row_to_dict(row)


def list_study_briefs(
    db_path: str | Path,
    study_id: str = DEFAULT_STUDY_ID,
    study_run_id: str | None = None,
    include_archived: bool = False,
    include_demo: bool = False,
) -> list[dict[str, object]]:
    run_id = study_run_id or str((get_active_study_run(db_path, study_id) or {}).get("id") or "")
    clauses = ["study_id = ?", "study_run_id = ?"]
    params: list[object] = [study_id, run_id]
    if not include_archived:
        clauses.append("(archived_at IS NULL OR archived_at = '')")
    if not include_demo:
        clauses.append("is_demo = 0")
    with connect(db_path) as connection:
        rows = connection.execute(f"SELECT * FROM study_briefs WHERE {' AND '.join(clauses)} ORDER BY created_at DESC", tuple(params)).fetchall()
    return [row_to_dict(row) for row in rows]


def run_research_batch(db_path: str | Path, raw_items: list[dict[str, object]], study_id: str = DEFAULT_STUDY_ID) -> dict[str, object]:
    signals = [
        create_signal(
            db_path,
            str(item.get("raw_text") or ""),
            study_id,
            str(item.get("source_url") or ""),
            str(item.get("source_name") or ""),
            str(item.get("source_type") or "manual"),
            str(item.get("source_date") or ""),
            str(item.get("country") or ""),
            str(item.get("stakeholder_type") or ""),
            str(item.get("company_product") or ""),
            str(item.get("data_origin") or "demo"),
            item.get("source_confidence"),
        )
        for item in raw_items
        if str(item.get("raw_text") or "").strip()
    ]
    findings = generate_findings(db_path, study_id)
    return {"signals": signals, "findings": findings}


def pull_real_market_evidence(
    db_path: str | Path,
    study_id: str = DEFAULT_STUDY_ID,
    providers: list[object] | None = None,
    max_sources: int = 10,
) -> dict[str, object]:
    active_run = get_active_study_run(db_path, study_id)
    if not active_run or active_run.get("study_mode") != "production":
        return {
            "status": "blocked",
            "message": "Real market evidence can only be pulled in Production Mode.",
            "sources_searched": 0,
            "queries_executed": 0,
            "urls_retrieved": 0,
            "urls_skipped": 0,
            "vendor_urls": 0,
            "government_urls": 0,
            "complaint_urls": 0,
            "accepted_signals": 0,
            "rejected_signals": 0,
            "candidate_results_found": 0,
            "signals_stored": 0,
            "skipped_duplicates": 0,
            "skipped_missing_source_or_text": 0,
            "skipped_not_complaint_or_pain_evidence": 0,
            "skipped_market_size_generic_or_marketing": 0,
            "providers_used": [],
            "active_run_id": "",
            "queries": GS001_REAL_EVIDENCE_QUERIES,
            "stored_signal_ids": [],
            "skipped": [],
            "signals": [],
            "technical_details": {},
        }
    if providers is None:
        readiness = provider_ready_for_research()
        if not readiness["ready"]:
            return {
                "status": "blocked",
                "message": str(readiness["message"]),
                "sources_searched": 0,
                "queries_executed": 0,
                "urls_retrieved": 0,
                "urls_skipped": 0,
                "vendor_urls": 0,
                "government_urls": 0,
                "complaint_urls": 0,
                "accepted_signals": 0,
                "rejected_signals": 0,
                "candidate_results_found": 0,
                "signals_stored": 0,
                "skipped_duplicates": 0,
                "skipped_missing_source_or_text": 0,
                "skipped_not_complaint_or_pain_evidence": 0,
                "skipped_market_size_generic_or_marketing": 0,
                "providers_used": [],
                "active_run_id": str(active_run["id"]),
                "queries": GS001_REAL_EVIDENCE_QUERIES,
                "stored_signal_ids": [],
                "skipped": [],
                "signals": [],
                "technical_details": readiness,
            }
        providers = configured_gs001_evidence_providers()

    retrieved_at = utc_now()
    research_run_id = f"GSDR-{retrieved_at.replace('-', '').replace(':', '').replace('T', '-')[:15]}"
    provider_names: list[str] = []
    candidates: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []
    skipped_openai = 0
    sources_searched = 0
    urls_retrieved = 0
    urls_skipped = 0
    query_runs = prioritized_evidence_query_runs(db_path, study_id)
    memory = discovery_domain_memory(db_path, study_id)
    for query_run in query_runs:
        query_group = str(query_run["query_group"])
        query = str(query_run["query"])
        query_category = str(query_run["query_category"])
        strategy_evidence_class = str(query_run["evidence_class"])
        strategy_evidence_tier = int(query_run["evidence_tier"])
        sources_searched += 1
        command = {
            "study": study_id,
            "acquisition_strategy": str(GS_P001_EVIDENCE_STRATEGY["id"]),
            "industry": "Residential Property Management",
            "market": "United States",
            "keyword": query,
            "query_group": query_group,
            "query_category": query_category,
            "evidence_class": strategy_evidence_class,
            "evidence_tier": strategy_evidence_tier,
            "focus": "Maintenance Communication",
            "objective": "collect high-quality source-backed complaint evidence; prefer authoritative evidence over volume",
            "preferred_sources": ["government", "regulators", "attorney general", "courts", "ombudsman", "public enforcement", "BBB", "Consumer Affairs", "tenant advocacy", "investigative journalism"],
            "avoid_sources": ["vendor websites", "pricing pages", "feature pages", "product landing pages", "software blogs"],
            "trusted_domains": memory["trusted_domains"][:10],
            "vendor_domains": memory["vendor_domains"][:10],
            "high_yield_queries": memory["high_yield_queries"][:10],
            "low_yield_queries": memory["low_yield_queries"][:10],
        }
        for provider in providers:
            provider_name = str(getattr(provider, "name", provider.__class__.__name__))
            if "openai" in provider_name.lower():
                skipped_openai += 1
                skipped.append({"reason": "openai_not_evidence", "provider": provider_name, "query": query})
                continue
            if provider_name not in provider_names:
                provider_names.append(provider_name)
            try:
                results = provider.search(command)  # type: ignore[attr-defined]
            except Exception:
                skipped.append({"reason": "provider_failed", "provider": provider_name, "query": query})
                continue
            for result in results:
                normalized = normalize_provider_result(result, query, retrieved_at)
                normalized["query_group"] = query_group
                normalized["query_category"] = query_category
                normalized["strategy_evidence_class"] = strategy_evidence_class
                normalized["strategy_evidence_tier"] = strategy_evidence_tier
                normalized["source_registry_id"] = evidence_source_for_candidate(normalized)
                candidates.append(normalized)
                urls_retrieved += 1

    deduped_candidates: list[dict[str, object]] = []
    seen_candidate_keys: set[str] = set()
    discovery_duplicates = 0
    prefilter_vendor_urls = 0
    government_urls = 0
    complaint_urls = 0
    for candidate in candidates:
        key = str(candidate.get("source_url") or candidate.get("raw_text") or "").strip().lower()
        if key and key in seen_candidate_keys:
            urls_skipped += 1
            discovery_duplicates += 1
            skipped.append({"reason": "duplicate", "stage": "discovery", "candidate": candidate})
            continue
        if key:
            seen_candidate_keys.add(key)
        if candidate.get("classification") == "vendor_content":
            prefilter_vendor_urls += 1
        if candidate.get("source_type_detected") in {"government", "court", "ombudsman"}:
            government_urls += 1
        if candidate.get("accepted_complaint_evidence"):
            complaint_urls += 1
        deduped_candidates.append(candidate)
    candidates = sorted(
        deduped_candidates,
        key=lambda candidate: int(candidate.get("discovery_priority_score") or 0),
        reverse=True,
    )

    stored = []
    skipped_missing = 0
    skipped_duplicates = 0
    skipped_not_pain = 0
    skipped_market_generic = 0
    skipped_marketing = 0
    skipped_low_authority = 0
    event_counts: dict[str, int] = {}
    for candidate in candidates:
        event_id = str(candidate.get("market_event_id") or candidate.get("underlying_event_id") or "")
        if event_id:
            event_counts[event_id] = event_counts.get(event_id, 0) + 1
        if len(stored) >= max_sources:
            break
        if "openai" in str(candidate.get("provider_name") or "").lower():
            skipped_openai += 1
            skipped.append({"reason": "openai_not_evidence", "candidate": candidate})
            continue
        has_source_url = bool(str(candidate.get("source_url") or "").strip())
        has_source_title = bool(str(candidate.get("original_title") or "").strip())
        if not (has_source_url or has_source_title):
            skipped_missing += 1
            skipped.append({"reason": "missing_source", "candidate": candidate})
            continue
        if not str(candidate.get("raw_text") or "").strip():
            skipped_missing += 1
            skipped.append({"reason": "missing_raw_text", "candidate": candidate})
            continue
        if not bool(candidate.get("accepted_complaint_evidence")):
            reason = str(candidate.get("skip_reason") or "not_complaint_or_pain_evidence")
            if reason == "marketing_content":
                skipped_marketing += 1
            elif reason == "low_authority_source":
                skipped_low_authority += 1
            elif reason == "market_size_generic_or_marketing":
                skipped_market_generic += 1
            else:
                skipped_not_pain += 1
                reason = "not_complaint_or_pain_evidence"
            skipped.append({"reason": reason, "candidate": candidate})
            continue
        if signal_duplicate_exists(
            db_path,
            study_id,
            str(active_run["id"]),
            str(candidate.get("source_url") or ""),
            str(candidate.get("raw_text") or ""),
        ):
            skipped_duplicates += 1
            skipped.append({"reason": "duplicate", "candidate": candidate})
            continue
        signal = create_signal(
            db_path,
            str(candidate["raw_text"]),
            study_id,
            str(candidate.get("source_url") or ""),
            str(candidate.get("source_name") or ""),
            str(candidate.get("source_type") or "search_result"),
            str(candidate.get("source_date") or retrieved_at),
            "United States",
            str(candidate.get("stakeholder_type") or "Unknown"),
            "",
            "provider",
            candidate.get("source_confidence"),  # type: ignore[arg-type]
        )
        with connect(db_path) as connection:
            connection.execute(
                "UPDATE study_signals SET verification_status = ?, last_updated = ? WHERE id = ?",
                ("pending_verification", utc_now(), signal["id"]),
            )
        stored.append(get_signal(db_path, str(signal["id"])))

    discovery_update = record_discovery_learning(
        db_path,
        study_id,
        str(active_run["id"]),
        research_run_id,
        candidates,
        skipped,
        stored,
    )
    status = "completed" if stored else "empty"
    message = "Research Run Complete" if stored else "No source-backed evidence found for this run."
    market_events = len({signal_market_event_id(signal) for signal in stored})
    merged_into_existing_events = sum(max(0, count - 1) for count in event_counts.values())
    reason_no_opportunity = ""
    if stored:
        if market_events < MIN_OPPORTUNITY_INDEPENDENT_EVENTS:
            reason_no_opportunity = f"Insufficient independent market events: {market_events}/{MIN_OPPORTUNITY_INDEPENDENT_EVENTS}."
        elif len({source_domain_or_identity(signal) for signal in stored}) < MIN_OPPORTUNITY_INDEPENDENT_SOURCES:
            reason_no_opportunity = f"Insufficient independent sources: {len({source_domain_or_identity(signal) for signal in stored})}/{MIN_OPPORTUNITY_INDEPENDENT_SOURCES}."
    result = {
        "status": status,
        "message": message,
        "sources_searched": sources_searched,
        "queries_executed": sources_searched,
        "urls_retrieved": urls_retrieved,
        "urls_skipped": urls_skipped,
        "vendor_urls": prefilter_vendor_urls,
        "government_urls": government_urls,
        "complaint_urls": complaint_urls,
        "accepted_signals": len(stored),
        "rejected_signals": skipped_not_pain + skipped_market_generic + skipped_marketing + skipped_low_authority,
        "marketing_pages_rejected": skipped_marketing,
        "low_authority_sources": skipped_low_authority,
        "merged_into_existing_events": merged_into_existing_events,
        "market_events": market_events,
        "candidate_results_found": len(candidates),
        "signals_stored": len(stored),
        "skipped_duplicates": skipped_duplicates + discovery_duplicates,
        "skipped_missing_source_or_text": skipped_missing,
        "skipped_not_complaint_or_pain_evidence": skipped_not_pain,
        "skipped_market_size_generic_or_marketing": skipped_market_generic + skipped_marketing,
        "skipped_marketing_content": skipped_marketing,
        "skipped_low_authority_source": skipped_low_authority,
        "skipped_openai_only": skipped_openai,
        "reason_no_opportunity_generated": reason_no_opportunity,
        "providers_used": provider_names,
        "active_run_id": str(active_run["id"]),
        "run_id": research_run_id,
        "queries": [str(query_run["query"]) for query_run in query_runs],
        "query_runs": query_runs,
        "stored_signal_ids": [str(signal["id"]) for signal in stored],
        "skipped": skipped,
        "signals": stored,
        "discovery_learning_update": discovery_update,
        "technical_details": {
            "study_id": study_id,
            "study_run_id": active_run["id"],
            "run_id": research_run_id,
            "queries": [str(query_run["query"]) for query_run in query_runs],
            "query_runs": query_runs,
            "query_groups": GS001_EVIDENCE_QUERY_GROUPS,
            "acquisition_strategy": GS_P001_EVIDENCE_STRATEGY,
            "discovery_memory_used": memory,
            "retrieved_at": retrieved_at,
            "skipped": skipped,
            "candidates": candidates,
            "domain_learning": discovery_domain_learning(candidates),
            "discovery_learning_update": discovery_update,
            "discovery_metrics": {
                "queries_executed": sources_searched,
                "urls_retrieved": urls_retrieved,
                "urls_skipped": urls_skipped,
                "discovery_duplicates": discovery_duplicates,
                "vendor_urls": prefilter_vendor_urls,
                "government_urls": government_urls,
                "complaint_urls": complaint_urls,
                "accepted_signals": len(stored),
                "rejected_signals": skipped_not_pain + skipped_market_generic + skipped_marketing + skipped_low_authority,
                "marketing_pages_rejected": skipped_marketing,
                "low_authority_sources": skipped_low_authority,
                "market_events": market_events,
                "merged_into_existing_events": merged_into_existing_events,
                "reason_no_opportunity_generated": reason_no_opportunity,
            },
        },
    }
    add_event(db_path, "GoldenStudyEvidencePulled", "PX-R001", message, str(len(stored)), study_id)
    return result


def normalize_provider_result(result: ProviderResult | object, query: str, retrieved_at: str) -> dict[str, object]:
    provider_name = str(getattr(result, "provider", "") or getattr(result, "name", "") or "Unknown Provider")
    title = str(getattr(result, "title", "") or "").strip()
    url = str(getattr(result, "url", "") or "").strip()
    snippet = str(getattr(result, "snippet", "") or "").strip()
    raw_text = snippet if snippet else ""
    source_type = normalize_source_type(str(getattr(result, "source_type", "") or ""), url, title)
    quality = evidence_quality_profile(f"{title}\n{snippet}", query, url, title, source_type)
    evidence_class = evidence_class_for_source(
        str(quality.get("source_type_detected") or source_type),
        url,
        title,
        provider_name,
        "",
    )
    quality["evidence_class"] = evidence_class
    quality["evidence_tier"] = evidence_tier_for_class(evidence_class)
    discovery_score = discovery_url_priority_score(url, title, snippet) + int(quality.get("source_trust_score") or 0)
    if quality.get("accepted_complaint_evidence"):
        discovery_score += 50
    discovery_score += max(0, 7 - int(quality.get("evidence_tier") or 6)) * 10
    return {
        "provider_name": provider_name,
        "query": query,
        "retrieved_at": retrieved_at,
        "original_title": title,
        "source_url": url,
        "source_name": encode_provider_signal_metadata(provider_name, query, retrieved_at, title, quality),
        "source_type": source_type,
        "source_date": retrieved_at,
        "country": "United States",
        "stakeholder_type": infer_gs001_stakeholder(f"{title} {snippet}"),
        "raw_text": raw_text,
        "summary": str((quality.get("operational_pain") or {}).get("what_pain") or summarize(snippet or title)),
        "source_confidence": rough_provider_evidence_strength(provider_name, url, snippet),
        "discovery_priority_score": discovery_score,
        "evidence_class": evidence_class,
        "evidence_tier": quality.get("evidence_tier"),
        **quality,
    }


def encode_provider_signal_metadata(
    provider_name: str,
    original_query: str,
    retrieved_at: str,
    original_title: str,
    quality: dict[str, object] | None = None,
) -> str:
    metadata = {
        "metadata_type": "provider_evidence",
        "provider_name": provider_name,
        "original_query": original_query,
        "retrieved_at": retrieved_at,
        "original_title": original_title,
    }
    if quality:
        metadata.update(
            {
                "evidence_relevance": quality.get("evidence_relevance"),
                "evidence_classification": quality.get("classification"),
                "classification": quality.get("classification"),
                "production_eligible": quality.get("production_eligible"),
                "source_type": quality.get("source_type_detected"),
                "evidence_class": quality.get("evidence_class"),
                "evidence_tier": quality.get("evidence_tier"),
                "executive_evidence_tier": quality.get("executive_evidence_tier"),
                "acquisition_strategy": quality.get("acquisition_strategy") or GS_P001_EVIDENCE_STRATEGY["id"],
                "source_trust_score": quality.get("source_trust_score"),
                "authority_score": quality.get("authority_score"),
                "operational_relevance_score": quality.get("operational_relevance_score"),
                "authority_threshold": quality.get("authority_threshold"),
                "authority_passed": quality.get("authority_passed"),
                "operational_relevance_passed": quality.get("operational_relevance_passed"),
                "classification_code": quality.get("classification_code"),
                "rejection_reason": quality.get("rejection_reason"),
                "executive_explanation": quality.get("executive_explanation"),
                "market_event_id": quality.get("market_event_id"),
                "underlying_event_id": quality.get("underlying_event_id"),
                "operational_pain": quality.get("operational_pain"),
                "why_accepted": quality.get("why_accepted"),
                "pain_keywords_matched": quality.get("pain_keywords_matched", []),
                "context_keywords_matched": quality.get("context_keywords_matched", []),
            }
        )
    return json.dumps(metadata, sort_keys=True)


def keyword_matches(text: str, keywords: list[str]) -> list[str]:
    lower = text.lower()
    return [keyword for keyword in keywords if keyword in lower]


def operational_relevance_score(text: str, query: str = "", url: str = "", title: str = "") -> int:
    lower = " ".join([query, url, title, text]).lower()
    score = 0
    if "united states" in lower or ".gov" in lower or "bbb.org" in lower or "consumeraffairs" in lower:
        score += 5
    if any(keyword in lower for keyword in ["tenant", "resident", "apartment", "landlord", "property manager", "property management", "rental", "multifamily"]):
        score += 20
    if any(keyword in lower for keyword in GS001_REQUIRED_MAINTENANCE_CONTEXT_KEYWORDS):
        score += 20
    if any(keyword in lower for keyword in GS001_OPERATIONAL_RELEVANCE_KEYWORDS):
        score += 35
    if "maintenance" in lower and "communication" in lower:
        score += 25
    if "repair" in lower and ("update" in lower or "communication" in lower):
        score += 25
    if any(keyword in lower for keyword in PAIN_KEYWORDS):
        score += 20
    if any(pattern in lower for pattern in GS001_CONTEXT_ONLY_PATTERNS):
        score -= 45
    if any(pattern in lower for pattern in GS001_ADVICE_PAGE_PATTERNS):
        score -= 20
    return max(0, min(100, score))


def evidence_tier_label(classification: str, production_eligible: bool, authority_score: int, relevance_score: int, source_type: str) -> str:
    if production_eligible:
        return "Tier A - Production Evidence"
    if classification in {"market_context", "news_report", "research_report"}:
        return "Tier C - Market Context"
    if classification in {"vendor_content", "marketing_content", "unknown"}:
        return "Tier D - Rejected"
    if source_type in {"vendor", "marketing"}:
        return "Tier D - Rejected"
    if authority_score >= 55 and relevance_score >= 45:
        return "Tier B - Supporting Evidence"
    if relevance_score >= 70 and authority_score < MIN_PRODUCTION_AUTHORITY_SCORE:
        return "Tier B - Supporting Evidence"
    return "Tier D - Rejected"


def plain_evidence_explanation(
    accepted: bool,
    classification: str,
    authority_score: int,
    relevance_score: int,
    source_type: str,
    reason: str,
) -> str:
    if accepted:
        if source_type in {"government", "court", "ombudsman", "consumer_review", "verified_review_platform", "news"}:
            return "Accepted because an independent, high-authority source describes residential maintenance communication pain with traceable source metadata."
        return "Accepted because the source describes repeated residential maintenance communication pain and passes the production evidence thresholds."
    if classification in {"market_context", "news_report", "research_report"}:
        return "Rejected for qualification because it provides market or background context rather than direct operational pain evidence."
    if classification in {"vendor_content", "marketing_content"}:
        return "Rejected because vendor, SEO, marketing or promotional content cannot support production qualification."
    if authority_score < MIN_PRODUCTION_AUTHORITY_SCORE and relevance_score >= 70:
        return "Rejected for production because operational pain is visible but the source authority is too low."
    if relevance_score < 70 and authority_score >= MIN_PRODUCTION_AUTHORITY_SCORE:
        return "Rejected for production because the source is authoritative but does not demonstrate maintenance communication failure."
    return reason or "Rejected because it does not meet production evidence authority and operational relevance thresholds."


def has_required_gs001_maintenance_context(text: str) -> bool:
    lower = text.lower()
    return any(keyword in lower for keyword in GS001_REQUIRED_MAINTENANCE_CONTEXT_KEYWORDS)


TRUSTED_NON_VENDOR_MARKERS = [
    "consumeraffairs",
    "consumer affairs",
    "bbb.org",
    "better business bureau",
    "ombudsman",
    ".gov",
    "government",
    "regulator",
    "court",
    "filing",
    "reuters",
    "apnews",
    "bbc",
    "guardian",
    "nytimes",
    "wsj",
]

VENDOR_LANGUAGE_MARKERS = [
    "sign up free",
    "book a demo",
    "request demo",
    "our platform",
    "our software",
    "our solution",
    "tracks",
    "automate",
    "automatic sla",
    "features",
    "pricing",
    "solution",
    "platform",
    "product page",
    "industries/",
    "/industries/",
    "use cases/",
    "/use-cases/",
    "customers/",
    "/customers/",
    "case studies/",
    "/case-studies/",
]


def is_trusted_non_vendor_source(text: str) -> bool:
    lower = text.lower()
    return any(marker in lower for marker in TRUSTED_NON_VENDOR_MARKERS)


def has_vendor_language(text: str) -> bool:
    lower = text.lower()
    return any(marker in lower for marker in VENDOR_LANGUAGE_MARKERS)


def is_marketing_content(text: str) -> bool:
    lower = text.lower()
    if any(pattern in lower for pattern in MARKETING_CONTENT_PATTERNS):
        return True
    generic_combinations = [
        ("guide", "property management"),
        ("trends", "property management"),
        ("outlook", "property management"),
        ("best", "software"),
        ("best", "companies"),
        ("market report", "property management"),
    ]
    return any(first in lower and second in lower for first, second in generic_combinations)


def extract_named_entities(text: str) -> list[str]:
    raw_entities = re.findall(r"\b[A-Z][A-Za-z&.-]*(?:\s+[A-Z][A-Za-z&.-]*){0,3}\b", text)
    stop = {"The", "A", "An", "And", "Tenant", "Property", "Maintenance", "United States"}
    return sorted({entity.strip() for entity in raw_entities if entity.strip() and entity.strip() not in stop})[:8]


def market_event_key(url: str, title: str, text: str) -> str:
    combined = " ".join([url, title, text])
    lower = combined.lower()
    domain = url_domain(url)
    entities = [normalize_group(entity) for entity in extract_named_entities(combined)]
    legal_markers = [marker for marker in ["lawsuit", "investigation", "fine", "settlement", "complaint", "ombudsman", "regulator", "court"] if marker in lower]
    years = re.findall(r"\b20\d{2}\b", combined)
    locations = [country.lower().replace(" ", "-") for country in COUNTRY_HINTS if country.lower() in lower]
    if entities or legal_markers or years or locations:
        parts = entities[:3] + legal_markers[:2] + years[:1] + locations[:1]
        return normalize_group(" ".join(parts))
    return normalize_group(f"{domain} {summarize(text or title)}")


def extract_operational_pain(text: str, title: str = "") -> dict[str, object]:
    combined = " ".join([title, text]).strip()
    lower = combined.lower()
    who = choose_from_keywords(combined, STAKEHOLDER_KEYWORDS, "Property managers")
    quote = summarize(text or title)
    what = quote
    if "no response" in lower or "not updated" in lower or "ignored" in lower:
        what = "Maintenance requests are not acknowledged or updated reliably."
    elif "delayed" in lower or "slow" in lower or "waiting" in lower:
        what = "Maintenance resolution and communication are delayed."
    elif "unresolved" in lower or "broken" in lower:
        what = "Repairs remain unresolved for affected residents or operators."
    why = "Fragmented maintenance communication and weak work-order visibility."
    if "manual" in lower:
        why = "Manual maintenance workflows create follow-up gaps."
    frequency = "Repeated" if any(word in lower for word in ["repeated", "multiple", "again", "often", "frequent"]) else "Observed"
    business_impact = "Higher support load, churn risk, and operational cost."
    customer_impact = "Poor resident satisfaction and uncertainty about repairs."
    operational_impact = "Teams spend extra time chasing status updates and coordinating work orders."
    financial_impact = "Delayed maintenance can increase repair cost and retention risk."
    regulatory_impact = "Potential habitability or compliance exposure." if any(word in lower for word in ["habitability", "court", "regulator", "ombudsman", "lawsuit", "fine"]) else "Not indicated."
    root_cause = "No reliable maintenance communication workflow." if any(word in lower for word in ["communication", "update", "status"]) else "Maintenance process lacks enough traceability."
    return {
        "who_experiences_pain": who,
        "what_pain": what,
        "why_it_occurs": why,
        "frequency_observed": frequency,
        "business_impact": business_impact,
        "customer_impact": customer_impact,
        "operational_impact": operational_impact,
        "financial_impact": financial_impact,
        "regulatory_impact": regulatory_impact,
        "evidence_quote": quote,
        "root_cause": root_cause,
    }


def detect_source_type(url: str = "", title: str = "", text: str = "", source_type_hint: str = "") -> str:
    lower = " ".join([source_type_hint, url, title, text]).lower()
    advice_like = any(pattern in lower for pattern in GS001_ADVICE_PAGE_PATTERNS)
    if advice_like and not any(word in lower for word in ["complaint", "enforcement", "case decision", "judgment", "lawsuit filed", "settlement"]):
        return "article"
    if any(word in lower for word in ["311", "service request", "housing complaint portal"]):
        return "government"
    if any(word in lower for word in ["court", "filing", "lawsuit", "docket"]):
        return "court"
    if any(word in lower for word in ["gov", "regulator", "government", "attorney general"]):
        return "government"
    if "ombudsman" in lower:
        return "ombudsman"
    if any(word in lower for word in ["consumeraffairs", "consumer affairs", "bbb.org", "better business bureau"]):
        return "consumer_review"
    if any(word in lower for word in ["trustpilot", "g2.com", "capterra", "software advice"]):
        return "verified_review_platform"
    if any(word in lower for word in ["facebook", "discord", "instagram", "tiktok", "threads.net"]):
        return "facebook_group" if "facebook" in lower else "social_media"
    if any(word in lower for word in ["reddit", "linkedin", "x.com", "twitter"]):
        return "social_media"
    if any(word in lower for word in ["forum", "community"]):
        return "forum"
    if any(word in lower for word in ["research", "university", "institute", "white paper"]):
        return "research"
    if any(word in lower for word in ["news", "reuters", "apnews", "bbc", "guardian", "nyt", "wsj", "forbes"]):
        return "news"
    if any(word in lower for word in ["manual", "verified_import", "verified import"]):
        return "manual_verified"
    if "article" in lower:
        return "article"
    if "search_result" in lower or "search result" in lower:
        return "search_result"
    if not is_trusted_non_vendor_source(lower) and has_vendor_language(lower):
        return "vendor"
    if any(word in lower for word in ["blog", "help.", "support.", "docs.", "features", "pricing", "demo", "vendor"]):
        return "vendor"
    if any(word in lower for word in ["marketing", "landing page", "sales page"]):
        return "marketing"
    return "unknown"


def source_trust_score(source_type: str, url: str = "", title: str = "", text: str = "") -> int:
    lower = " ".join([url, title, text]).lower()
    if "housing ombudsman" in lower:
        return 98
    if "consumer affairs" in lower or "consumeraffairs" in lower or "bbb.org" in lower or "better business bureau" in lower:
        return 95
    return SOURCE_TRUST_SCORES.get(source_type, 0)


def evidence_quality_profile(text: str, query: str = "", url: str = "", title: str = "", source_type_hint: str = "") -> dict[str, object]:
    combined = text.strip()
    lower = combined.lower()
    all_text = " ".join([source_type_hint, url, title, combined])
    vendor_detected = has_vendor_language(all_text) and not is_trusted_non_vendor_source(all_text)
    marketing_detected = is_marketing_content(all_text)
    source_type = detect_source_type(url, title, combined, source_type_hint)
    trust_score = source_trust_score(source_type, url, title, combined)
    relevance_score = operational_relevance_score(combined, query, url, title)
    pain_matches = keyword_matches(combined, PAIN_KEYWORDS)
    context_matches = keyword_matches(combined, PROPERTY_MAINTENANCE_CONTEXT_KEYWORDS)
    required_maintenance_context = has_required_gs001_maintenance_context(all_text)
    pain_profile = extract_operational_pain(combined, title)
    event_key = market_event_key(url, title, combined)
    strong_complaint = bool(pain_matches and context_matches)
    strong_pain_language = any(
        keyword in lower
        for keyword in [
            "complaint",
            "complain",
            "complains",
            "issue",
            "problem",
            "poor",
            "slow",
            "delayed",
            "no response",
            "unresolved",
            "waiting",
            "broken",
            "frustration",
            "dispute",
            "bad service",
            "ignored",
            "lack of communication",
            "not updated",
        ]
    )

    context_only_detected = any(pattern in all_text.lower() for pattern in GS001_CONTEXT_ONLY_PATTERNS)
    advice_page_detected = any(pattern in all_text.lower() for pattern in GS001_ADVICE_PAGE_PATTERNS)

    if marketing_detected:
        source_type = "marketing"
        trust_score = 40
        classification = "marketing_content"
        relevance = "vendor_marketing"
        reason = MARKETING_REJECTION_REASON
    elif vendor_detected or source_type in {"vendor", "marketing"}:
        source_type = "vendor"
        trust_score = 20
        classification = "vendor_content"
        relevance = "vendor_marketing"
        reason = "Vendor-authored guidance. Useful background information only."
    elif source_type in {"social_media", "facebook_group"}:
        classification = "community_signal"
        relevance = "unknown"
        reason = "Community discussion. Requires independent verification."
    elif context_only_detected:
        classification = "market_context"
        relevance = "market_size_only"
        reason = "Government or public context only; not residential maintenance communication pain evidence."
    elif advice_page_detected:
        classification = "market_context"
        relevance = "generic_article"
        reason = "Advice or guidance page; useful context but not direct complaint evidence."
    elif any(word in lower for word in ["market size", "market report", "forecast", "cagr", "industry revenue", "statistics", "funding", "investment", "industry trends", "software trends"]):
        classification = "market_context"
        relevance = "market_size_only"
        reason = "Market context only; not direct complaint evidence."
    elif source_type == "research":
        classification = "research_report"
        relevance = "generic_article"
        reason = "Research report; background context only unless corroborated by complaint evidence."
    elif source_type == "news" and not strong_complaint:
        classification = "news_report"
        relevance = "generic_article"
        reason = "News report without direct complaint evidence."
    elif (advice_page_detected or any(word in lower for word in ["article", "guide", "overview", "best practices", "tips"])) and not strong_pain_language:
        classification = "market_context"
        relevance = "generic_article"
        reason = "Generic article; useful context but not independent complaint evidence."
    elif any(word in lower for word in ["complaint", "complain", "complains", "bad service", "no response", "not updated"]):
        classification = "verified_complaint" if source_type in {"consumer_review", "verified_review_platform", "government", "court", "ombudsman", "news"} else "operational_pain"
        relevance = "complaint"
        reason = "Independent complaint matching GS-001." if classification == "verified_complaint" else "Complaint or pain evidence from a lower-trust source."
    elif any(word in lower for word in ["issue", "problem", "poor", "slow", "delayed", "unresolved", "waiting", "broken", "repair", "frustration", "dispute", "ignored"]):
        classification = "operational_pain"
        relevance = "operational_pain"
        reason = "Operational pain evidence matching GS-001."
    elif any(word in lower for word in ["manual", "workflow", "work order", "lack of communication", "maintenance request"]):
        classification = "workflow_inefficiency"
        relevance = "workflow_inefficiency"
        reason = "Workflow inefficiency evidence matching GS-001."
    else:
        classification = "unknown"
        relevance = "unknown"
        reason = "Unknown evidence class; not production eligible."

    authority_passed = trust_score >= MIN_PRODUCTION_AUTHORITY_SCORE
    relevance_passed = relevance_score >= 70
    production_eligible = (
        classification in PRODUCTION_ELIGIBLE_CLASSIFICATIONS
        and bool(pain_matches)
        and bool(context_matches)
        and required_maintenance_context
        and authority_passed
        and relevance_passed
        and not context_only_detected
        and not advice_page_detected
    )
    if production_eligible:
        why = f"{reason} Matched pain keywords and property-maintenance context."
        skip_reason = ""
    elif classification == "marketing_content":
        why = f"Rejected: {MARKETING_REJECTION_REASON}."
        skip_reason = "marketing_content"
    elif not required_maintenance_context and classification in PRODUCTION_ELIGIBLE_CLASSIFICATIONS:
        why = "Rejected: No Operational Pain. Evidence does not mention maintenance, repairs, work orders, or habitability."
        skip_reason = "not_complaint_or_pain_evidence"
    elif not authority_passed and classification in PRODUCTION_ELIGIBLE_CLASSIFICATIONS:
        why = f"Rejected: Low Authority Source. Authority score {trust_score} is below {MIN_PRODUCTION_AUTHORITY_SCORE}."
        skip_reason = "low_authority_source"
    elif not relevance_passed and classification in PRODUCTION_ELIGIBLE_CLASSIFICATIONS:
        why = f"Rejected: Low Operational Relevance. Operational relevance score {relevance_score} is below 70."
        skip_reason = "not_complaint_or_pain_evidence"
    elif classification in {"market_context", "vendor_content", "news_report", "research_report"}:
        why = reason
        skip_reason = "market_size_generic_or_marketing"
    elif classification == "community_signal":
        why = reason
        skip_reason = "not_complaint_or_pain_evidence"
    else:
        why = "Rejected: missing complaint/pain language or property-maintenance context."
        skip_reason = "not_complaint_or_pain_evidence"
    evidence_class = evidence_class_for_source(source_type, url, title, "", query)
    tier_label = evidence_tier_label(classification, production_eligible, trust_score, relevance_score, source_type)
    explanation = plain_evidence_explanation(production_eligible, classification, trust_score, relevance_score, source_type, why)
    return {
        "classification": classification,
        "evidence_classification": classification,
        "evidence_class": evidence_class,
        "evidence_tier": evidence_tier_for_class(evidence_class),
        "executive_evidence_tier": tier_label,
        "production_eligible": production_eligible,
        "source_type_detected": source_type,
        "source_trust_score": trust_score,
        "authority_score": trust_score,
        "operational_relevance_score": relevance_score,
        "authority_threshold": MIN_PRODUCTION_AUTHORITY_SCORE,
        "authority_passed": authority_passed,
        "operational_relevance_passed": relevance_passed,
        "required_maintenance_context": required_maintenance_context,
        "evidence_relevance": relevance,
        "classification_code": str(classification).upper(),
        "rejection_reason": "" if production_eligible else why.replace("Rejected: ", "").strip(),
        "market_event_id": event_key,
        "underlying_event_id": event_key,
        "operational_pain": pain_profile,
        "pain_keywords_matched": pain_matches,
        "context_keywords_matched": context_matches,
        "why_accepted": why,
        "executive_explanation": explanation,
        "accepted_complaint_evidence": production_eligible,
        "skip_reason": skip_reason,
    }


def signal_quality_metadata(signal: dict[str, object]) -> dict[str, object]:
    metadata = provider_signal_metadata(signal)
    if metadata.get("evidence_classification") or metadata.get("classification") or metadata.get("evidence_relevance"):
        classification = metadata.get("evidence_classification") or metadata.get("classification") or {
            "complaint": "verified_complaint",
            "operational_pain": "operational_pain",
            "workflow_inefficiency": "workflow_inefficiency",
            "market_size_only": "market_context",
            "vendor_marketing": "vendor_content",
            "generic_article": "market_context",
        }.get(str(metadata.get("evidence_relevance") or ""), "unknown")
        production_eligible = bool(metadata.get("production_eligible"))
        if "production_eligible" not in metadata:
            production_eligible = classification in PRODUCTION_ELIGIBLE_CLASSIFICATIONS and bool(metadata.get("pain_keywords_matched")) and bool(metadata.get("context_keywords_matched"))
        return {
            "classification": classification,
            "evidence_classification": classification,
            "production_eligible": production_eligible,
            "source_type_detected": metadata.get("source_type") or "unknown",
            "evidence_class": metadata.get("evidence_class") or evidence_class_for_source(str(metadata.get("source_type") or ""), str(signal.get("source_url") or ""), str(metadata.get("original_title") or signal.get("source_name") or "")),
            "evidence_tier": int(metadata.get("evidence_tier") or evidence_tier_for_class(str(metadata.get("evidence_class") or ""))),
            "executive_evidence_tier": metadata.get("executive_evidence_tier") or evidence_tier_label(str(classification), production_eligible, int(metadata.get("authority_score") or metadata.get("source_trust_score") or 0), int(metadata.get("operational_relevance_score") or 0), str(metadata.get("source_type") or "unknown")),
            "acquisition_strategy": metadata.get("acquisition_strategy") or "",
            "source_trust_score": int(metadata.get("source_trust_score") or 0),
            "authority_score": int(metadata.get("authority_score") or metadata.get("source_trust_score") or 0),
            "operational_relevance_score": int(metadata.get("operational_relevance_score") or 0),
            "authority_threshold": int(metadata.get("authority_threshold") or MIN_PRODUCTION_AUTHORITY_SCORE),
            "authority_passed": bool(metadata.get("authority_passed")) if "authority_passed" in metadata else int(metadata.get("source_trust_score") or 0) >= MIN_PRODUCTION_AUTHORITY_SCORE,
            "operational_relevance_passed": bool(metadata.get("operational_relevance_passed")) if "operational_relevance_passed" in metadata else int(metadata.get("operational_relevance_score") or 0) >= 70,
            "evidence_relevance": metadata.get("evidence_relevance"),
            "classification_code": metadata.get("classification_code") or str(classification).upper(),
            "rejection_reason": metadata.get("rejection_reason") or "",
            "executive_explanation": metadata.get("executive_explanation") or metadata.get("why_accepted") or "",
            "market_event_id": metadata.get("market_event_id") or metadata.get("underlying_event_id") or "",
            "underlying_event_id": metadata.get("underlying_event_id") or metadata.get("market_event_id") or "",
            "operational_pain": metadata.get("operational_pain") or {},
            "pain_keywords_matched": metadata.get("pain_keywords_matched") or [],
            "context_keywords_matched": metadata.get("context_keywords_matched") or [],
            "why_accepted": metadata.get("why_accepted") or "",
            "accepted_complaint_evidence": production_eligible,
        }
    return evidence_quality_profile(
        f"{signal.get('source_name') or ''}\n{signal.get('summary') or ''}\n{signal.get('raw_text') or ''}",
        str(signal.get("query") or ""),
        str(signal.get("source_url") or ""),
        str(signal.get("source_name") or ""),
        str(signal.get("source_type") or ""),
    )


def source_domain_or_identity(signal: dict[str, object]) -> str:
    url = str(signal.get("source_url") or "").strip()
    if url:
        parsed = urlparse(url)
        return parsed.netloc.lower().removeprefix("www.") or url
    return str(signal.get("source_name") or signal.get("id") or "unknown")


def signal_market_event_id(signal: dict[str, object]) -> str:
    quality = signal_quality_metadata(signal)
    return str(
        quality.get("market_event_id")
        or quality.get("underlying_event_id")
        or signal.get("duplicate_group")
        or normalize_group(f"{signal.get('source_name') or ''} {signal.get('summary') or ''}")
    )


def signal_organisation_identity(signal: dict[str, object]) -> str:
    product = str(signal.get("company_product") or "").strip()
    if product:
        return normalize_group(product)
    domain = source_domain_or_identity(signal)
    return normalize_group(domain)


def url_domain(url: str) -> str:
    parsed = urlparse(str(url or "").strip())
    return parsed.netloc.lower().removeprefix("www.") or str(url or "").strip().lower()


def discovery_url_priority_score(url: str, title: str = "", text: str = "") -> int:
    lower = " ".join([url, title, text]).lower()
    score = 0
    boosts = {
        "bbb.org": 95,
        "consumeraffairs.com": 95,
        ".gov": 95,
        ".gov.uk": 95,
        "housing-ombudsman": 94,
        "ombudsman": 90,
        "courtlistener": 90,
        "justice.gov": 95,
        "hud.gov": 95,
        "attorneygeneral": 90,
        "reuters": 85,
        "apnews": 85,
        "bbc": 85,
        "guardian": 80,
        "reddit": 45,
        "forum": 40,
    }
    penalties = ["pricing", "features", "product", "demo", "blog", "our-software", "industries", "solution", "use-cases", "customers", "case-studies"]
    for marker, boost in boosts.items():
        if marker in lower:
            score += boost
    for marker in penalties:
        if marker in lower:
            score -= 45
    return score


def discovery_domain_learning(candidates: list[dict[str, object]]) -> dict[str, list[str]]:
    accepted_domains = sorted({url_domain(str(candidate.get("source_url") or "")) for candidate in candidates if candidate.get("accepted_complaint_evidence") and candidate.get("source_url")})
    trusted_domains = sorted({url_domain(str(candidate.get("source_url") or "")) for candidate in candidates if int(candidate.get("source_trust_score") or 0) >= 80 and candidate.get("source_url")})
    vendor_domains = sorted({url_domain(str(candidate.get("source_url") or "")) for candidate in candidates if candidate.get("classification") == "vendor_content" and candidate.get("source_url")})
    rejected_domains = sorted({url_domain(str(candidate.get("source_url") or "")) for candidate in candidates if not candidate.get("accepted_complaint_evidence") and candidate.get("source_url")})
    return {
        "accepted_domains": [domain for domain in accepted_domains if domain],
        "trusted_domains": [domain for domain in trusted_domains if domain],
        "vendor_domains": [domain for domain in vendor_domains if domain],
        "rejected_domains": [domain for domain in rejected_domains if domain],
    }


def discovery_memory_rows(db_path: str | Path, study_id: str = DEFAULT_STUDY_ID) -> list[dict[str, object]]:
    with connect(db_path) as connection:
        rows = connection.execute(
            "SELECT * FROM discovery_memory WHERE study_id = ? ORDER BY score DESC, last_seen_at DESC",
            (study_id,),
        ).fetchall()
    return [row_to_dict(row) for row in rows]


def discovery_learning_dashboard(db_path: str | Path, study_id: str = DEFAULT_STUDY_ID) -> dict[str, object]:
    rows = discovery_memory_rows(db_path, study_id)
    runs = []
    with connect(db_path) as connection:
        run_rows = connection.execute(
            "SELECT * FROM discovery_runs WHERE study_id = ? ORDER BY created_at DESC",
            (study_id,),
        ).fetchall()
    runs = [row_to_dict(row) for row in run_rows]
    provider_rows = [row for row in rows if row.get("memory_type") == "provider"]
    best_provider = max(provider_rows, key=lambda row: float(row.get("score") or 0), default={})
    accepted_total = sum(int(row.get("accepted_count") or 0) for row in provider_rows)
    rejected_total = sum(int(row.get("rejected_count") or 0) for row in provider_rows)
    total = accepted_total + rejected_total
    trust_values = [float(row.get("average_trust_score") or 0) for row in rows if float(row.get("average_trust_score") or 0) > 0]
    evidence_class_rows = [row for row in rows if row.get("memory_type") == "evidence_class"]
    best_evidence_class = max(evidence_class_rows, key=lambda row: float(row.get("score") or 0), default={})
    return {
        "best_domains": [row for row in rows if row.get("memory_type") == "trusted_domain"][:5],
        "worst_domains": [row for row in rows if row.get("memory_type") in {"rejected_domain", "vendor_domain"}][:5],
        "best_queries": [row for row in rows if row.get("memory_type") == "high_yield_query"][:5],
        "worst_queries": [row for row in rows if row.get("memory_type") == "low_yield_query"][:5],
        "evidence_classes": evidence_class_rows[:8],
        "best_evidence_class": best_evidence_class,
        "best_provider": best_provider,
        "acceptance_rate": round((accepted_total / total) * 100, 1) if total else 0,
        "average_trust_score": round(sum(trust_values) / len(trust_values), 1) if trust_values else 0,
        "runs_analysed": len({str(row.get("run_id")) for row in runs}),
        "rows": rows,
        "runs": runs,
    }


def evidence_tier_for_class(evidence_class: str) -> int:
    config = EVIDENCE_CLASS_TIERS.get(str(evidence_class or "").strip(), EVIDENCE_CLASS_TIERS["Unknown"])
    return int(config.get("tier") or 6)


def evidence_class_for_source(
    source_type: str = "",
    url: str = "",
    title: str = "",
    provider_name: str = "",
    query_group: str = "",
) -> str:
    lower = " ".join([source_type, url, title, provider_name, query_group]).lower()
    if "vendor" in lower:
        return "Vendor"
    if "marketing" in lower:
        return "Marketing"
    if "ombudsman" in lower:
        return "Ombudsman"
    if any(marker in lower for marker in ["court", "lawsuit", "docket", "judgment", "filing"]):
        return "Court"
    if any(marker in lower for marker in ["attorney general", "site:ag.", ".ag.", "/ag/", " ag "]):
        return "Attorney General"
    if any(marker in lower for marker in ["housing authority", "public housing"]):
        return "Housing Authority"
    if any(marker in lower for marker in ["311", "service request", "housing complaint portal"]):
        return "Housing Authority"
    if any(marker in lower for marker in [".gov", "hud.gov", "regulator", "enforcement", "government"]):
        return "Regulator"
    if any(marker in lower for marker in ["bbb.org", "better business bureau", "consumer affairs", "consumeraffairs"]):
        return "Consumer Complaints"
    if any(marker in lower for marker in ["tenant advocacy", "tenant union"]):
        return "Tenant Advocacy"
    if any(marker in lower for marker in ["reuters", "apnews", "guardian", "nytimes", "wsj", "investigation", "news"]):
        return "Investigative Journalism"
    if any(marker in lower for marker in ["housing trade", "property management trade"]):
        return "Housing Trade Publication"
    if any(marker in lower for marker in ["reddit", "forum", "community", "social_media", "facebook_group"]):
        return "Community Evidence"
    if any(marker in lower for marker in ["search_result", "tavily", "serpapi", "newsapi"]):
        return "Search Provider"
    return "Unknown"


def gs_p001_query_runs() -> list[dict[str, object]]:
    runs: list[dict[str, object]] = []
    for index, category in enumerate(GS_P001_EVIDENCE_STRATEGY["query_categories"]):  # type: ignore[index]
        evidence_class = str(category["evidence_class"])  # type: ignore[index]
        evidence_tier = evidence_tier_for_class(evidence_class)
        for query in category["queries"]:  # type: ignore[index]
            runs.append(
                {
                    "query_group": str(category["query_group"]),  # type: ignore[index]
                    "query_category": str(category["query_category"]),  # type: ignore[index]
                    "query": str(query),
                    "evidence_class": evidence_class,
                    "evidence_tier": evidence_tier,
                    "strategy": str(GS_P001_EVIDENCE_STRATEGY["id"]),
                    "base_index": index,
                }
            )
    return sorted(runs, key=lambda run: (int(run["evidence_tier"]), int(run["base_index"])))


def prioritized_evidence_query_runs(db_path: str | Path, study_id: str = DEFAULT_STUDY_ID) -> list[dict[str, object]]:
    base = gs_p001_query_runs()
    memory = discovery_memory_rows(db_path, study_id)
    scores = {str(row.get("memory_key")): float(row.get("score") or 0) for row in memory if row.get("memory_type") in {"high_yield_query", "low_yield_query"}}
    vendor_domains = {str(row.get("memory_key")) for row in memory if row.get("memory_type") == "vendor_domain"}
    indexed = list(enumerate(base))

    def rank(item: tuple[int, dict[str, object]]) -> tuple[int, float, int]:
        index, run = item
        query = str(run.get("query") or "")
        tier = int(run.get("evidence_tier") or 6)
        score = scores.get(query, 0)
        if any(domain and domain in query for domain in vendor_domains):
            score -= 100
        return (tier, -score, index)

    ordered_runs = [run for _, run in sorted(indexed, key=rank)]
    seen: set[str] = set()
    unique: list[dict[str, object]] = []
    for run in ordered_runs:
        query = str(run.get("query") or "")
        if query not in seen:
            unique.append(run)
            seen.add(query)
    return unique


def prioritized_query_runs(db_path: str | Path, study_id: str = DEFAULT_STUDY_ID) -> list[tuple[str, str]]:
    return [(str(run["query_group"]), str(run["query"])) for run in prioritized_evidence_query_runs(db_path, study_id)]


def discovery_domain_memory(db_path: str | Path, study_id: str = DEFAULT_STUDY_ID) -> dict[str, list[str]]:
    rows = discovery_memory_rows(db_path, study_id)
    return {
        "trusted_domains": [str(row.get("memory_key")) for row in rows if row.get("memory_type") == "trusted_domain"],
        "rejected_domains": [str(row.get("memory_key")) for row in rows if row.get("memory_type") == "rejected_domain"],
        "vendor_domains": [str(row.get("memory_key")) for row in rows if row.get("memory_type") == "vendor_domain"],
        "high_yield_queries": [str(row.get("memory_key")) for row in rows if row.get("memory_type") == "high_yield_query"],
        "low_yield_queries": [str(row.get("memory_key")) for row in rows if row.get("memory_type") == "low_yield_query"],
    }


def upsert_discovery_memory(
    db_path: str | Path,
    study_id: str,
    memory_type: str,
    memory_key: str,
    accepted: int = 0,
    rejected: int = 0,
    vendor: int = 0,
    market_context: int = 0,
    community: int = 0,
    duplicates: int = 0,
    trust_score: float = 0,
    provider: str = "",
    query: str = "",
) -> None:
    if not memory_key:
        return
    score = accepted * 10 + trust_score - rejected * 3 - vendor * 8 - market_context * 4 - community * 2 - duplicates
    now = utc_now()
    with connect(db_path) as connection:
        existing = connection.execute(
            "SELECT * FROM discovery_memory WHERE study_id = ? AND memory_type = ? AND memory_key = ?",
            (study_id, memory_type, memory_key),
        ).fetchone()
        if existing:
            old = row_to_dict(existing)
            new_accepted = int(old.get("accepted_count") or 0) + accepted
            new_rejected = int(old.get("rejected_count") or 0) + rejected
            old_trust = float(old.get("average_trust_score") or 0)
            new_trust = round(((old_trust + trust_score) / 2), 1) if old_trust and trust_score else trust_score or old_trust
            connection.execute(
                """
                UPDATE discovery_memory
                SET score = score + ?, accepted_count = ?, rejected_count = ?,
                    vendor_count = vendor_count + ?, market_context_count = market_context_count + ?,
                    community_count = community_count + ?, duplicate_count = duplicate_count + ?,
                    average_trust_score = ?, provider = COALESCE(NULLIF(?, ''), provider),
                    query = COALESCE(NULLIF(?, ''), query), last_seen_at = ?
                WHERE id = ?
                """,
                (score, new_accepted, new_rejected, vendor, market_context, community, duplicates, new_trust, provider, query, now, old["id"]),
            )
        else:
            connection.execute(
                """
                INSERT INTO discovery_memory
                (study_id, memory_type, memory_key, provider, query, score, accepted_count, rejected_count,
                 vendor_count, market_context_count, community_count, duplicate_count, average_trust_score, last_seen_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (study_id, memory_type, memory_key, provider, query, score, accepted, rejected, vendor, market_context, community, duplicates, trust_score, now),
            )


def _candidate_domain(candidate: dict[str, object]) -> str:
    return url_domain(str(candidate.get("source_url") or ""))


def _candidate_query_key(candidate: dict[str, object]) -> tuple[str, str, str]:
    provider = str(candidate.get("provider_name") or "Unknown Provider")
    query = str(candidate.get("query") or "")
    query_group = str(candidate.get("query_group") or "")
    return provider, query, query_group


def record_discovery_learning(
    db_path: str | Path,
    study_id: str,
    study_run_id: str,
    run_id: str,
    candidates: list[dict[str, object]],
    skipped: list[dict[str, object]],
    stored_signals: list[dict[str, object]],
) -> dict[str, object]:
    ensure_data_source_registry(db_path)
    stored_urls = {str(signal.get("source_url") or "").strip().lower() for signal in stored_signals if signal.get("source_url")}
    duplicate_keys = {
        (
            str((item.get("candidate") or {}).get("provider_name") or item.get("provider") or "Unknown Provider"),
            str((item.get("candidate") or {}).get("query") or item.get("query") or ""),
        )
        for item in skipped
        if item.get("reason") == "duplicate"
    }
    grouped: dict[tuple[str, str, str], list[dict[str, object]]] = {}
    for candidate in candidates:
        grouped.setdefault(_candidate_query_key(candidate), []).append(candidate)

    inserted_rows: list[dict[str, object]] = []
    now = utc_now()
    with connect(db_path) as connection:
        for (provider, query, query_group), rows in grouped.items():
            accepted = [row for row in rows if str(row.get("source_url") or "").strip().lower() in stored_urls]
            rejected = [row for row in rows if row not in accepted]
            vendor = [row for row in rejected if row.get("classification") == "vendor_content"]
            market_context = [row for row in rejected if row.get("classification") == "market_context" or row.get("evidence_relevance") == "market_size_only"]
            community = [row for row in rejected if row.get("source_type_detected") in {"forum", "social_media", "facebook_group"}]
            unknown = [row for row in rejected if row.get("classification") in {"unknown", None, ""}]
            accepted_domains = sorted({domain for domain in (_candidate_domain(row) for row in accepted) if domain})
            rejected_domains = sorted({domain for domain in (_candidate_domain(row) for row in rejected) if domain})
            trust_values = [int(row.get("source_trust_score") or 0) for row in accepted if int(row.get("source_trust_score") or 0) > 0]
            avg_trust = round(sum(trust_values) / len(trust_values), 1) if trust_values else 0
            duplicates = 1 if (provider, query) in duplicate_keys else 0
            evidence_classes = sorted(
                {
                    str(row.get("evidence_class") or evidence_class_for_source(str(row.get("source_type_detected") or ""), str(row.get("source_url") or ""), str(row.get("original_title") or ""), provider, query_group))
                    for row in rows
                }
            )
            values = (
                study_id,
                study_run_id,
                run_id,
                provider,
                query,
                query_group,
                len(rows),
                len(rejected),
                len(accepted),
                len(vendor),
                len(market_context),
                len(community),
                len(unknown),
                duplicates,
                avg_trust,
                json.dumps(accepted_domains),
                json.dumps(rejected_domains),
                now,
            )
            connection.execute(
                """
                INSERT INTO discovery_runs
                (study_id, study_run_id, run_id, provider, query, query_group, urls_returned, urls_skipped,
                 accepted_signals, rejected_vendor, rejected_market_context, rejected_community,
                 rejected_unknown, duplicates, average_trust_score, accepted_domains, rejected_domains, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            source_groups: dict[str, list[dict[str, object]]] = {}
            for row in rows:
                source_groups.setdefault(str(row.get("source_registry_id") or evidence_source_for_candidate(row)), []).append(row)
            for source_id, source_rows in source_groups.items():
                source_accepted = [row for row in source_rows if str(row.get("source_url") or "").strip().lower() in stored_urls]
                source_rejected = [row for row in source_rows if row not in source_accepted]
                source_duplicates = 1 if duplicates else 0
                source_marketing = [row for row in source_rejected if row.get("classification") in {"vendor_content", "marketing_content"}]
                source_trust = [int(row.get("source_trust_score") or 0) for row in source_accepted if int(row.get("source_trust_score") or 0) > 0]
                source_relevance = [int(row.get("operational_relevance_score") or 0) for row in source_accepted if int(row.get("operational_relevance_score") or 0) > 0]
                connection.execute(
                    """
                    INSERT INTO source_collection_runs
                    (source_id, study_id, run_id, provider, documents_collected, accepted_evidence, rejected_evidence,
                     duplicates, marketing_rejected, average_trust_score, average_commercial_relevance,
                     average_operational_pain, collection_error, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        source_id,
                        study_id,
                        run_id,
                        provider,
                        len(source_rows),
                        len(source_accepted),
                        len(source_rejected),
                        source_duplicates,
                        len(source_marketing),
                        round(sum(source_trust) / len(source_trust), 1) if source_trust else 0,
                        round(sum(source_relevance) / len(source_relevance), 1) if source_relevance else 0,
                        round(sum(source_relevance) / len(source_relevance), 1) if source_relevance else 0,
                        "",
                        now,
                    ),
                )
            inserted_rows.append(
                {
                    "provider": provider,
                    "query": query,
                    "query_group": query_group,
                    "urls_returned": len(rows),
                    "accepted_signals": len(accepted),
                    "rejected_vendor": len(vendor),
                    "rejected_market_context": len(market_context),
                    "rejected_community": len(community),
                    "rejected_unknown": len(unknown),
                    "duplicates": duplicates,
                    "average_trust_score": avg_trust,
                    "accepted_domains": accepted_domains,
                    "rejected_domains": rejected_domains,
                    "evidence_classes": evidence_classes,
                }
            )

    for row in inserted_rows:
        accepted_count = int(row["accepted_signals"])
        rejected_count = int(row["urls_returned"]) - accepted_count
        trust_score = float(row["average_trust_score"] or 0)
        provider = str(row["provider"])
        query = str(row["query"])
        for domain in row["accepted_domains"]:
            upsert_discovery_memory(db_path, study_id, "trusted_domain", str(domain), accepted=accepted_count, trust_score=trust_score, provider=provider, query=query)
        for domain in row["rejected_domains"]:
            upsert_discovery_memory(db_path, study_id, "rejected_domain", str(domain), rejected=1, provider=provider, query=query)
        for candidate in candidates:
            if _candidate_query_key(candidate)[:2] != (provider, query):
                continue
            domain = _candidate_domain(candidate)
            if candidate.get("classification") == "vendor_content" and domain:
                upsert_discovery_memory(db_path, study_id, "vendor_domain", domain, rejected=1, vendor=1, provider=provider, query=query)
        for evidence_class in row.get("evidence_classes") or []:
            class_candidates = [
                candidate
                for candidate in candidates
                if _candidate_query_key(candidate)[:2] == (provider, query)
                and str(candidate.get("evidence_class") or evidence_class_for_source(str(candidate.get("source_type_detected") or ""), str(candidate.get("source_url") or ""), str(candidate.get("original_title") or ""), provider, str(candidate.get("query_group") or ""))) == str(evidence_class)
            ]
            class_accepted = [
                candidate
                for candidate in class_candidates
                if str(candidate.get("source_url") or "").strip().lower() in stored_urls
            ]
            class_rejected = len(class_candidates) - len(class_accepted)
            class_trust_values = [int(candidate.get("source_trust_score") or 0) for candidate in class_accepted if int(candidate.get("source_trust_score") or 0) > 0]
            class_avg_trust = round(sum(class_trust_values) / len(class_trust_values), 1) if class_trust_values else 0
            upsert_discovery_memory(
                db_path,
                study_id,
                "evidence_class",
                str(evidence_class),
                accepted=len(class_accepted),
                rejected=class_rejected,
                vendor=len([candidate for candidate in class_candidates if candidate.get("classification") == "vendor_content"]),
                market_context=len([candidate for candidate in class_candidates if candidate.get("classification") == "market_context"]),
                community=len([candidate for candidate in class_candidates if candidate.get("source_type_detected") in {"forum", "social_media", "facebook_group"}]),
                duplicates=int(row["duplicates"]),
                trust_score=class_avg_trust,
                provider=provider,
                query=query,
            )
        if accepted_count:
            upsert_discovery_memory(db_path, study_id, "high_yield_query", query, accepted=accepted_count, rejected=rejected_count, trust_score=trust_score, provider=provider, query=query)
        elif rejected_count:
            upsert_discovery_memory(db_path, study_id, "low_yield_query", query, rejected=rejected_count, provider=provider, query=query)
        upsert_discovery_memory(
            db_path,
            study_id,
            "provider",
            provider,
            accepted=accepted_count,
            rejected=rejected_count,
            vendor=int(row["rejected_vendor"]),
            market_context=int(row["rejected_market_context"]),
            community=int(row["rejected_community"]),
            duplicates=int(row["duplicates"]),
            trust_score=trust_score,
            provider=provider,
            query=query,
        )

    dashboard = discovery_learning_dashboard(db_path, study_id)
    vendor_domains = [str(row.get("memory_key")) for row in dashboard["rows"] if row.get("memory_type") == "vendor_domain"][:5]
    accepted_domains = sorted({domain for row in inserted_rows for domain in row["accepted_domains"]})
    best_query_row = max((row for row in dashboard["rows"] if row.get("memory_type") == "high_yield_query"), key=lambda row: float(row.get("score") or 0), default={})
    provider_rows = [row for row in inserted_rows if row.get("provider")]
    return {
        "run_id": run_id,
        "accepted_domains": accepted_domains,
        "rejected_vendor_domains": vendor_domains,
        "best_query": best_query_row.get("memory_key") or "",
        "provider_performance": provider_rows,
        "dashboard": dashboard,
    }


def is_accepted_production_signal(signal: dict[str, object]) -> bool:
    if bool(signal.get("is_demo")):
        return False
    if str(signal.get("data_origin") or "") == "demo":
        return False
    quality = signal_quality_metadata(signal)
    return bool(quality.get("production_eligible")) and quality.get("classification") in PRODUCTION_ELIGIBLE_CLASSIFICATIONS


def provider_signal_metadata(signal: dict[str, object]) -> dict[str, object]:
    raw = signal.get("source_name")
    if not isinstance(raw, str) or not raw.strip().startswith("{"):
        return {}
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    if isinstance(parsed, dict) and parsed.get("metadata_type") == "provider_evidence":
        return parsed
    return {}


def _score_as_int(value: object) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def _decision_pass(value: object, threshold: int = 70) -> str:
    return "PASS" if _score_as_int(value) >= threshold else "NEEDS EVIDENCE"


def _decision_count(value: bool) -> str:
    return "1 / 2" if value else "0 / 2"


def _evidence_decision_recommendation(
    signal: dict[str, object],
    quality: dict[str, object],
    source_name: object,
) -> str:
    if quality.get("production_eligible"):
        return "Use as accepted production evidence, then collect independent corroboration."
    classification = str(quality.get("classification") or quality.get("evidence_classification") or "unknown")
    if classification == "vendor_content":
        return "Reject for qualification; vendor content cannot support a build decision."
    if classification == "market_context":
        return "Keep as context only; collect complaint or operational pain evidence."
    if classification == "community_signal":
        return "Verify with an authoritative source before using in qualification."
    if not (signal.get("source_url") or source_name):
        return "Collect a traceable source URL or named source."
    if _score_as_int(quality.get("source_trust_score")) < 70:
        return "Find a more authoritative independent source."
    if _score_as_int(quality.get("operational_relevance_score")) < 70:
        return "Collect evidence that directly shows maintenance communication pain."
    return "Collect additional independent evidence before qualification."


def signal_trace_card_view_model(signal: dict[str, object]) -> dict[str, str]:
    metadata = provider_signal_metadata(signal)
    source_name = (
        signal.get("source_name")
        or signal.get("source_url")
        or metadata.get("provider_name")
        or "Unknown source"
    )
    if metadata.get("original_title"):
        source_name = metadata["original_title"]
    provider = metadata.get("provider_name") or signal.get("provider_name") or "Unknown provider"
    query = metadata.get("original_query") or signal.get("query") or "Not recorded"
    retrieved = metadata.get("retrieved_at") or signal.get("retrieved_at") or signal.get("source_date") or "Not recorded"
    raw_text = signal.get("raw_text") or signal.get("summary") or "No evidence quote recorded."
    quality = signal_quality_metadata(signal)
    authority_score = quality.get("authority_score") or quality.get("source_trust_score") or 0
    relevance_score = quality.get("operational_relevance_score") or 0
    raw_source_name = signal.get("source_name")
    traceable = bool(signal.get("source_url") or (raw_source_name and str(raw_source_name).strip() and str(raw_source_name).strip() != "Unknown source"))
    domain = source_domain_or_identity(signal)
    has_event = bool(signal.get("market_event_id") or quality.get("market_event_id"))
    accepted = bool(quality.get("production_eligible"))
    confidence = min(_score_as_int(authority_score), _score_as_int(relevance_score))
    if accepted and confidence <= 0:
        confidence = _score_as_int(quality.get("source_trust_score"))
    executive_label = "Production evidence" if accepted else "Evidence review"
    executive_summary = (
        f"{executive_label}: {source_name} has {confidence}% decision confidence."
        if confidence
        else f"{executive_label}: {source_name} needs more qualification."
    )
    recommendation = _evidence_decision_recommendation(signal, quality, source_name)
    return {
        "source_name": str(source_name),
        "provider": str(provider),
        "query": str(query),
        "retrieved": str(retrieved),
        "source_url": str(signal.get("source_url") or "No source URL"),
        "raw_text": str(raw_text),
        "country": str(signal.get("country") or "Unknown"),
        "stakeholder": str(signal.get("stakeholder_type") or "Unknown"),
        "verification_status": str(signal.get("verification_status") or "Not recorded"),
        "evidence_strength": str(signal.get("evidence_strength") or 0),
        "classification": str(quality.get("classification") or "unknown"),
        "evidence_classification": str(quality.get("evidence_classification") or quality.get("classification") or "unknown"),
        "executive_evidence_tier": str(quality.get("executive_evidence_tier") or "Tier D - Rejected"),
        "evidence_class": str(quality.get("evidence_class") or "Unknown"),
        "source_type": str(quality.get("source_type_detected") or "unknown"),
        "source_trust_score": str(quality.get("source_trust_score") or 0),
        "authority_score": str(authority_score),
        "operational_relevance_score": str(relevance_score),
        "production_eligible": "YES" if quality.get("production_eligible") else "NO",
        "evidence_relevance": str(quality.get("evidence_relevance") or "unknown"),
        "executive_explanation": str(quality.get("executive_explanation") or quality.get("why_accepted") or "Not recorded"),
        "rejection_reason": str(quality.get("rejection_reason") or ""),
        "why_accepted": str(quality.get("why_accepted") or "Not recorded"),
        "pain_keywords_matched": ", ".join(str(item) for item in quality.get("pain_keywords_matched", []) or []) or "None",
        "context_keywords_matched": ", ".join(str(item) for item in quality.get("context_keywords_matched", []) or []) or "None",
        "decision_question": "Can we trust it?",
        "executive_summary": executive_summary,
        "confidence": str(confidence),
        "authority_decision": _decision_pass(authority_score),
        "commercial_relevance_decision": _decision_pass(relevance_score),
        "traceability_decision": "PASS" if traceable else "NEEDS EVIDENCE",
        "independent_sources": _decision_count(bool(domain and domain != "unknown")),
        "independent_events": _decision_count(has_event),
        "organisations": _decision_count(bool(domain and domain != "unknown")),
        "current_recommendation": recommendation,
    }


def configured_gs001_evidence_providers() -> list[object]:
    providers: list[object] = []
    for provider in [TavilySearchProvider(), SerpAPISearchProvider(), NewsAPIProvider()]:
        try:
            status = provider.status()
        except Exception:
            continue
        if getattr(status, "status", "") == "connected":
            providers.append(provider)
    return providers


def infer_gs001_stakeholder(text: str) -> str:
    lower = text.lower()
    if any(word in lower for word in ["tenant", "resident", "renter", "apartment"]):
        return "Tenant"
    if any(word in lower for word in ["property manager", "property management", "manager"]):
        return "Property Manager"
    if any(word in lower for word in ["owner", "landlord", "investor"]):
        return "Property Owner"
    if any(word in lower for word in ["hoa", "board", "association"]):
        return "HOA Board"
    if any(word in lower for word in ["contractor", "maintenance technician", "repair"]):
        return "Maintenance Contractor"
    if any(word in lower for word in ["software", "platform", "buyer", "vendor"]):
        return "Software Buyer"
    return "Unknown"


def normalize_source_type(source_type: str, url: str, title: str) -> str:
    lower = " ".join([source_type, url, title]).lower()
    if "news" in lower:
        return "news"
    if any(word in lower for word in ["forum", "reddit", "community"]):
        return "forum"
    if any(word in lower for word in ["review", "trustpilot", "g2", "capterra"]):
        return "review"
    if any(word in lower for word in ["article", "blog"]):
        return "article"
    if source_type:
        return "search_result"
    return "unknown"


def rough_provider_evidence_strength(provider_name: str, url: str, text: str) -> int:
    score = 45
    if url:
        score += 15
    if len(text) > 160:
        score += 15
    if any(word in text.lower() for word in ["complaint", "complain", "issue", "problem", "maintenance", "communication", "request"]):
        score += 15
    if provider_name.lower() in {"tavily", "serpapi", "newsapi"}:
        score += 10
    return min(score, 100)


def signal_duplicate_exists(db_path: str | Path, study_id: str, study_run_id: str, source_url: str, raw_text: str) -> bool:
    with connect(db_path) as connection:
        if source_url.strip():
            url_match = connection.execute(
                """
                SELECT COUNT(*) AS count FROM study_signals
                WHERE study_id = ? AND study_run_id = ? AND source_url = ?
                """,
                (study_id, study_run_id, source_url),
            ).fetchone()["count"]
            if int(url_match):
                return True
        text_match = connection.execute(
            """
            SELECT COUNT(*) AS count FROM study_signals
            WHERE study_id = ? AND study_run_id = ? AND raw_text = ?
            """,
            (study_id, study_run_id, raw_text),
        ).fetchone()["count"]
    return bool(int(text_match))


def run_audit_batch(db_path: str | Path, study_id: str = DEFAULT_STUDY_ID) -> list[dict[str, object]]:
    audits = []
    active_run = get_active_study_run(db_path, study_id)
    include_demo = bool(active_run and active_run.get("study_mode") == "demo")
    for finding in list_findings(db_path, study_id, include_demo=include_demo):
        demo_rehearsal_ready = bool(finding.get("is_demo")) and finding.get("status") == "Insufficient Evidence" and len(_loads_list(finding.get("representative_signals"))) >= 2
        if finding["status"] in {"pending_audit", "Demo Finding"} or demo_rehearsal_ready:
            audits.append(audit_finding(db_path, str(finding["id"])))
    return audits


def findings_feedback(findings: list[dict[str, object]]) -> tuple[str, str]:
    count = len(findings)
    if count:
        return "success", f"{count} findings generated"
    return "warning", "Evidence clusters reviewed. No production finding created because thresholds were not met."


def audit_batch_feedback(audits: list[dict[str, object]], findings: list[dict[str, object]]) -> tuple[str, str]:
    count = len(audits)
    if count:
        return "success", f"{count} audits completed"
    demo_ready = any(bool(finding.get("is_demo")) and finding.get("status") in {"Demo Finding", "Demo Audited", "Demo Opportunity"} for finding in findings)
    if demo_ready:
        return "success", "Demo audit rehearsal completed safely."
    return "warning", "No auditable findings found"


def approval_feedback(opportunities: list[dict[str, object]], demo_present: bool = False) -> tuple[str, str]:
    count = len(opportunities)
    if count:
        if all(bool(opportunity.get("is_demo")) for opportunity in opportunities):
            return "success", f"{count} demo opportunities created"
        return "success", f"{count} opportunities approved"
    if demo_present:
        return "warning", "No demo opportunities available for rehearsal."
    return "warning", "No approved opportunities available"


def demo_warning_active(db_path: str | Path, study_id: str = DEFAULT_STUDY_ID) -> bool:
    return demo_records_count(db_path, study_id) > 0


def demo_records_count(
    db_path: str | Path,
    study_id: str = DEFAULT_STUDY_ID,
    study_run_id: str | None = None,
    include_archived: bool = False,
) -> int:
    run_id = study_run_id or str((get_active_study_run(db_path, study_id) or {}).get("id") or "")
    archived_sql = "" if include_archived else "AND status != 'archived'"
    with connect(db_path) as connection:
        total = 0
        for table_name in ["study_signals", "study_findings", "finding_audits", "opportunity_records"]:
            total += int(
                connection.execute(
                    f"SELECT COUNT(*) AS count FROM {table_name} WHERE study_id = ? AND study_run_id = ? AND is_demo = 1 {archived_sql}",
                    (study_id, run_id),
                ).fetchone()["count"]
            )
    return total


def non_demo_records_count(
    db_path: str | Path,
    study_id: str = DEFAULT_STUDY_ID,
    study_run_id: str | None = None,
    include_archived: bool = False,
) -> int:
    run_id = study_run_id or str((get_active_study_run(db_path, study_id) or {}).get("id") or "")
    archived_sql = "" if include_archived else "AND status != 'archived'"
    with connect(db_path) as connection:
        total = 0
        for table_name in ["study_signals", "study_findings", "finding_audits", "opportunity_records"]:
            total += int(
                connection.execute(
                    f"SELECT COUNT(*) AS count FROM {table_name} WHERE study_id = ? AND study_run_id = ? AND is_demo = 0 {archived_sql}",
                    (study_id, run_id),
                ).fetchone()["count"]
            )
    return total


def run_filter(study_id: str, study_run_id: str, include_archived: bool, include_demo: bool) -> tuple[str, tuple[object, ...]]:
    clauses = ["study_id = ?", "study_run_id = ?"]
    params: list[object] = [study_id, study_run_id]
    if not include_archived:
        clauses.append("status != 'archived'")
    if not include_demo:
        clauses.append("is_demo = 0")
    return " AND ".join(clauses), tuple(params)


def validate_golden_study_integrity(db_path: str | Path, study_id: str = DEFAULT_STUDY_ID) -> dict[str, object]:
    study = get_study(db_path, study_id)
    active_run = get_active_study_run(db_path, study_id)
    active_run_id = str((active_run or {}).get("id") or "")
    signals = list_signals(db_path, study_id, active_run_id, include_archived=False, include_demo=True)
    findings = list_findings(db_path, study_id, active_run_id, include_archived=False, include_demo=True)
    audits = list_finding_audits(db_path, study_id, active_run_id, include_archived=False, include_demo=True)
    opportunities = list_opportunities(db_path, study_id, active_run_id, include_archived=False, include_demo=True)
    production_progress = study_progress(db_path, study_id, active_run_id, include_archived=False, include_demo=False)
    checks = []
    def check(name: str, passed: bool, recommended_fix: str, **extra: object) -> None:
        row = {"check": name, "passed": passed, "recommended_fix": "" if passed else recommended_fix}
        row.update(extra)
        checks.append(row)

    runs = list_study_runs(db_path, study_id)
    active_runs = [run for run in runs if run.get("status") == "active"]
    check(
        "Only one active run exists per study",
        len(active_runs) == 1,
        "Close duplicate active study runs so only one run is active.",
        active_count=len(active_runs),
    )
    for table_name in RUN_SCOPED_TABLES:
        missing = missing_run_id_count(db_path, table_name, study_id)
        check(
            f"All {table_name} records belong to a study run",
            missing == 0,
            f"Assign legacy {table_name} rows to their demo or production study run.",
            missing_count=missing,
        )
    production_mode = str((active_run or study or {}).get("study_mode") or "demo") == "production"
    active_records = [*signals, *findings, *audits, *opportunities]
    check(
        "Active production run contains no demo records",
        not production_mode or not any(bool(row.get("is_demo")) and row.get("status") != "archived" for row in active_records),
        "Switch to a clean production run or archive demo records under their demo run.",
    )
    check(
        "Production KPIs exclude demo and archived records",
        not production_mode or (production_progress["demo_records_count"] == 0 and production_progress["archived_count"] == 0),
        "Calculate production KPIs from the active production run with include_demo=False and include_archived=False.",
    )
    check(
        "Engineering Ready metrics are active production only",
        not production_mode or all(
            not bool(row.get("is_demo")) and row.get("study_run_id") == active_run_id and row.get("status") != "archived"
            for row in production_progress["engineering_ready"]
        ),
        "Filter Engineering Ready metrics to the active production run only.",
    )
    check(
        "OCI metrics are active production only",
        not production_mode or all(
            not bool(row.get("is_demo")) and row.get("study_run_id") == active_run_id and row.get("status") != "archived"
            for row in production_progress["top_opportunities"]
        ),
        "Filter OCI metrics to active non-demo production opportunities.",
    )
    check(
        "No demo record is approved",
        not production_mode or not any(bool(row.get("is_demo")) and row.get("status") in {"Approved Opportunity", "Engineering Ready", "opportunity_approved"} for row in active_records),
        "Archive demo records and rerun approval with non-demo evidence only.",
    )
    check(
        "No demo record is Engineering Ready",
        not production_mode or not any(bool(row.get("is_demo")) and (row.get("engineering_status") == "Engineering Ready" or row.get("status") == "Engineering Ready") for row in opportunities),
        "Remove Engineering Ready status from demo records and archive them.",
    )
    for signal in signals:
        if not bool(signal.get("is_demo")) and signal.get("status") != "archived":
            check(
                f"Non-demo signal {signal['id']} has source",
                bool(signal.get("source_url") or signal.get("source_name")),
                "Add a source URL or source name to the signal.",
            )
    for finding in findings:
        check(
            f"Finding {finding['id']} links to signals",
            bool(_loads_list(finding.get("representative_signals"))),
            "Regenerate findings from sourced signals.",
        )
    for audit in audits:
        check(f"Audit {audit['id']} links to finding", bool(audit.get("finding_id")), "Rerun audit from a valid finding.")
        check(f"Audit {audit['id']} has explainable OCI", bool(audit.get("score_breakdown") and audit.get("oci_reasoning")), "Rerun audit to create score breakdown and reasoning.")
        check(f"Demo audit {audit['id']} is not approved", not production_mode or not (bool(audit.get("is_demo")) and audit.get("decision") == "Approve Opportunity"), "Archive demo audit and approve only non-demo evidence.")
    for opportunity in opportunities:
        try:
            chain = traceability_chain(db_path, str(opportunity["id"]), include_archived=False)
            chain_complete = bool(chain["audit"] and chain["finding"] and chain["signals"] and chain["sources"])
            non_demo = not any(bool(record.get("is_demo")) for record in [chain["opportunity"], chain["audit"], chain["finding"], *chain["signals"]])
            source_complete = all(source.get("source_url") or source.get("source_name") for source in chain["sources"])
        except Exception:
            chain_complete = False
            non_demo = False
            source_complete = False
        required = ["recommended_component", "engineering_recommendation", "problem_scope", "target_users", "required_inputs", "expected_outputs", "system_boundaries"]
        missing_engineering = [field for field in required if not opportunity.get(field)]
        check(f"Opportunity {opportunity['id']} links to audit", bool(opportunity.get("audit_id")), "Recreate opportunity from an audited finding.")
        check(f"Opportunity {opportunity['id']} traces to sources", chain_complete and source_complete, "View Evidence Chain and add missing source metadata.")
        check(f"Opportunity {opportunity['id']} uses non-demo evidence", non_demo, "Archive demo evidence and approve from production evidence only.")
        check(
            f"Engineering Ready {opportunity['id']} has required fields",
            opportunity.get("engineering_status") != "Engineering Ready" or not missing_engineering,
            f"Complete engineering fields: {', '.join(missing_engineering)}.",
        )
    archived_preserved = True
    with connect(db_path) as connection:
        archived_rows = connection.execute("SELECT COUNT(*) AS count FROM demo_archive").fetchone()["count"]
        archived_demo_runs = connection.execute("SELECT COUNT(*) AS count FROM study_runs WHERE study_id = ? AND study_mode = 'demo' AND status IN ('closed', 'archived')", (study_id,)).fetchone()["count"]
    check("Archived demo records are preserved", archived_preserved, "Do not hard-delete archived demo records.", count=int(archived_rows))
    check("Archived demo run remains traceable", int(archived_demo_runs) > 0 or production_mode is False, "Close demo runs instead of deleting them when switching to production.", count=int(archived_demo_runs))
    failed = [check for check in checks if not check["passed"]]
    return {"passed": not failed, "failed_count": len(failed), "checks": checks}


def missing_run_id_count(db_path: str | Path, table_name: str, study_id: str) -> int:
    if table_name not in RUN_SCOPED_TABLES:
        raise ValueError(f"Unsupported run scoped table: {table_name}")
    with connect(db_path) as connection:
        return int(
            connection.execute(
                f"SELECT COUNT(*) AS count FROM {table_name} WHERE study_id = ? AND (study_run_id IS NULL OR study_run_id = '')",
                (study_id,),
            ).fetchone()["count"]
        )


def normalize_data_origin(data_origin: str) -> str:
    return data_origin if data_origin in {"demo", "manual", "verified_import", "provider"} else "demo"


def provenance_values(data_origin: str, worker_id: str, source_confidence: float | None = None) -> dict[str, object]:
    origin = normalize_data_origin(data_origin)
    is_demo = origin == "demo"
    verification_status = "unverified" if is_demo else "pending_review"
    return {
        "data_origin": origin,
        "verification_status": verification_status,
        "is_demo": is_demo,
        "source_confidence": source_confidence,
        "created_by_worker": worker_id,
    }


def _loads_list(raw: object) -> list[object]:
    if not raw:
        return []
    try:
        parsed = json.loads(str(raw))
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []
