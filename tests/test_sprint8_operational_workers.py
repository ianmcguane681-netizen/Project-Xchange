from components.comp_001_prompt_engine.prompt_engine import (
    PromptStatus,
    approve_prompt,
    benchmark_prompt,
    best_prompt_for_worker,
    create_prompt,
    list_prompt_usage,
)
from project_exchange.command_console import run_command
from project_exchange.database import fetch_all, init_db
from project_exchange.eos import JobType
from project_exchange.head_of_functions import (
    create_objective,
    create_operating_schedule,
    create_performance_snapshot,
    generate_operating_brief,
    list_objectives,
    list_operating_briefs,
    list_operating_schedules,
    run_operating_schedule,
    worker_load_monitor,
)
from project_exchange.provider_base import ProviderResult
from project_exchange.research_engine import run_internet_research
from workers.px_a001_audit.audit_engine import run_audit
from workers.px_l001_library.library_manager import store_approved_record


class StaticSprint8Provider:
    name = "Static Sprint 8 Provider"

    def search(self, command):
        return [
            ProviderResult(
                self.name,
                "Irish property managers complain about slow maintenance updates and pricing",
                "https://example.com/sprint8",
                "Customers complain repeatedly about maintenance workflow delays, pricing confusion, and weak tenant communication.",
            )
        ]


def test_objectives_schedules_briefs_and_performance(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    objective = create_objective(db_path, "Research Irish property management", "Find recurring complaints.", 1, "daily")
    schedule = create_operating_schedule(
        db_path,
        "Daily Irish property research",
        "daily",
        "PX-R001",
        JobType.INTERNET_RESEARCH.value,
        {
            "market": "Irish property management",
            "keyword": "maintenance complaints",
            "source_name": "Manual verified maintenance complaint",
            "source_url": "https://example.com/manual-schedule-evidence",
            "source_text": "A tenant reports repeated maintenance delays and a lack of communication from the property manager.",
        },
        objective["id"],
        1,
    )

    result = run_operating_schedule(db_path, schedule["id"])
    assert result["job"]["status"] == "Completed"
    assert list_objectives(db_path)
    assert list_operating_schedules(db_path)

    brief = generate_operating_brief(db_path, "daily")
    snapshot = create_performance_snapshot(db_path, "test")
    assert brief["id"].startswith("BRF-")
    assert snapshot["id"].startswith("PERF-")
    assert list_operating_briefs(db_path)
    assert worker_load_monitor(db_path)


def test_research_package_library_lineage_and_audit_reasoning(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    result = run_internet_research(
        db_path,
        {"market": "Irish property management", "country": "Ireland", "keyword": "maintenance complaints"},
        providers=[StaticSprint8Provider()],
    )
    package = result["package"]
    assert package["recommended_actions"]
    assert package["status"] == "pending_audit"
    assert fetch_all(db_path, "research_history")
    assert fetch_all(db_path, "research_performance")

    audit = run_audit(db_path, result["research"])
    if audit["decision"] == "approved":
        library = store_approved_record(db_path, audit, result["research"])
        assert library["library_id"]
        record = fetch_all(db_path, "library_records")[0]
        assert record["origin_research_id"] == result["research"]["id"]
        assert "PX-R001" in record["worker_history"]

    reasoning = fetch_all(db_path, "audit_reasoning")[0]
    assert reasoning["evidence_matrix"]
    assert reasoning["source_quality"]


def test_prompt_usage_and_best_prompt_selection(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    prompt = create_prompt(db_path, "PX-R001", "System prompt", "Return PX-R001 response.")
    approve_prompt(db_path, prompt["id"])
    benchmark_prompt(db_path, prompt["id"], "Research this market", "PX-R001", "A")

    assert list_prompt_usage(db_path, "PX-R001")
    best = best_prompt_for_worker(db_path, "PX-R001")
    assert best
    assert best["id"] == prompt["id"]


def test_command_console_generates_operating_brief(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    result = run_command(db_path, "Generate executive report.")
    assert result["brief"]["brief_type"] == "daily"
