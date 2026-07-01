import json

from project_exchange.config import provider_statuses, status_for_key
from project_exchange.provider_modules.newsapi_provider import NewsAPIProvider
from project_exchange.provider_modules.openai_provider import OpenAIReasoningProvider
from project_exchange.provider_modules.tavily_serpapi_provider import SerpAPISearchProvider, TavilySearchProvider
from project_exchange.provider_base import ProviderResult
from project_exchange.provider_status import provider_connection_rows, provider_ready_for_research
from project_exchange.research_engine import run_internet_research
from project_exchange.database import fetch_all, init_db


class BrokenProvider:
    name = "Broken Provider"

    def search(self, command):
        raise RuntimeError("secret-value-should-not-leak")


class LiveLikeProvider:
    name = "Live Like Provider"

    def search(self, command):
        return [
            ProviderResult(
                self.name,
                "Users complain about slow support and expensive pricing",
                "https://example.com/live",
                "Users complain about slow support. Pricing is $29 per month. Automation opportunity.",
            )
        ]


def test_provider_status_does_not_expose_secret(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-secret-value-long-enough")
    rows = provider_connection_rows()
    openai = next(row for row in rows if row["provider"] == "OpenAI")
    assert openai["status"] == "connected"
    assert "sk-test" not in json.dumps(rows)
    assert provider_statuses()


def test_invalid_and_disconnected_status(monkeypatch):
    monkeypatch.delenv("NEWSAPI_API_KEY", raising=False)
    monkeypatch.setenv("TAVILY_API_KEY", "short")
    assert status_for_key("NewsAPI", "NEWSAPI_API_KEY").status == "disconnected"
    assert TavilySearchProvider().status().status == "invalid"


def test_provider_classes_return_empty_when_disconnected(monkeypatch):
    for key in ["TAVILY_API_KEY", "SERPAPI_API_KEY", "NEWSAPI_API_KEY", "OPENAI_API_KEY"]:
        monkeypatch.delenv(key, raising=False)
    assert TavilySearchProvider().search({"market": "x"}) == []
    assert SerpAPISearchProvider().search({"market": "x"}) == []
    assert NewsAPIProvider().search({"market": "x"}) == []
    assert OpenAIReasoningProvider().status().status == "disconnected"


def test_provider_guard_blocks_unconfigured_research(monkeypatch, tmp_path):
    for key in ["TAVILY_API_KEY", "SERPAPI_API_KEY", "NEWSAPI_API_KEY", "OPENAI_API_KEY"]:
        monkeypatch.delenv(key, raising=False)
    db_path = tmp_path / "px.db"
    init_db(db_path)

    readiness = provider_ready_for_research()
    assert readiness["ready"] is False
    assert readiness["message"] == "No provider configured. Add API keys in Provider Settings or paste evidence manually."
    try:
        run_internet_research(db_path, {"market": "Property Management"})
    except ValueError as exc:
        assert str(exc) == readiness["message"]
    else:
        raise AssertionError("Unconfigured production research should be blocked.")
    assert fetch_all(db_path, "research_records") == []
    assert fetch_all(db_path, "research_packages") == []


def test_provider_failure_does_not_create_fake_fallback_evidence(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    try:
        run_internet_research(db_path, {"market": "Property Management"}, providers=[BrokenProvider()])
    except ValueError as exc:
        assert "No placeholder, demo, or invented evidence was created" in str(exc)
    else:
        raise AssertionError("Provider failure should not create fallback evidence.")
    assert fetch_all(db_path, "research_records") == []
    assert fetch_all(db_path, "research_packages") == []


def test_live_research_gracefully_handles_provider_failure(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    result = run_internet_research(
        db_path,
        {"market": "Property Management", "keyword": "maintenance"},
        providers=[BrokenProvider(), LiveLikeProvider()],
    )

    assert result["research"]["id"].startswith("RES-")
    provider_runs = fetch_all(db_path, "provider_runs")
    assert any(row["status"] == "failed" for row in provider_runs)
    assert "secret-value" not in json.dumps(provider_runs)
    assert fetch_all(db_path, "research_packages")
