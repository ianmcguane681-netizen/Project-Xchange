from project_exchange.command_console import run_command
from project_exchange.database import fetch_all, init_db
from project_exchange.eos import JobType, create_job, execute_job
from project_exchange.os_services import (
    add_knowledge_edge,
    list_knowledge_edges,
    list_settings,
    list_worker_messages,
    send_worker_message,
    set_setting,
)
from project_exchange.provider_base import ProviderResult
from project_exchange.research_engine import run_internet_research
from components.comp_001_prompt_engine.prompt_engine import benchmark_prompt, create_prompt, list_prompt_benchmarks


class StaticProvider:
    name = "Static Test Provider"

    def search(self, command):
        return [
            ProviderResult(
                self.name,
                "Property software users complain about slow maintenance updates",
                "https://example.com/review",
                "Users complain support is slow. Pricing is $49 per month. Competitor Appfolio appears.",
            )
        ]


def test_internet_research_package_and_provider_runs(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    result = run_internet_research(
        db_path,
        {
            "company": "PropertyMe",
            "industry": "Property Management",
            "market": "Property Management",
            "keyword": "maintenance",
        },
        providers=[StaticProvider()],
    )

    assert result["research"]["id"].startswith("RES-")
    assert result["package"]["confidence_score"] >= 60
    assert fetch_all(db_path, "provider_runs")[0]["result_count"] == 1
    assert fetch_all(db_path, "research_packages")


def test_command_console_routes_to_job_engine(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    result = run_command(db_path, "Research Property Management software.")
    assert result["job"]["status"] == "Completed"
    assert fetch_all(db_path, "jobs")


def test_settings_worker_chat_graph_and_prompt_benchmark(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    set_setting(db_path, "llm_provider", "Local Heuristic", "LLM")
    assert list_settings(db_path)[0]["key"] == "llm_provider"

    message = send_worker_message(db_path, "PX-R001", "PX-A001", "Research ready.")
    assert message["id"]
    assert list_worker_messages(db_path)

    add_knowledge_edge(db_path, "research", "RES-X", "audited_by", "audit", "AUD-X")
    assert list_knowledge_edges(db_path, "RES-X")

    prompt = create_prompt(db_path, "PX-A001", "System prompt", "Return PX-A001 response.")
    benchmark = benchmark_prompt(db_path, prompt["id"], "Audit this", "PX-A001", "A")
    assert benchmark["score"] == 100
    assert list_prompt_benchmarks(db_path, prompt["id"])


def test_internet_research_job_type(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    job = create_job(
        db_path,
        JobType.INTERNET_RESEARCH.value,
        "PX-R001",
        {
            "market": "Property Management",
            "keyword": "maintenance updates",
            "source_name": "Manual verified maintenance complaint",
            "source_url": "https://example.com/manual-evidence",
            "source_text": "A tenant reports a delayed maintenance request and repeated communication failures.",
        },
    )
    finished = execute_job(db_path, job["id"])
    assert finished["status"] == "Completed"
