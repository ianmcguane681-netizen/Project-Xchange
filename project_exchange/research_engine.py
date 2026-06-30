from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path
from typing import Protocol

from project_exchange.database import add_changelog, connect, count_rows, utc_now
from project_exchange.eos import add_event, add_log
from project_exchange.ids import next_sequence_id
from project_exchange.provider_base import ProviderResult, build_query
from project_exchange.provider_modules.newsapi_provider import NewsAPIProvider
from project_exchange.provider_modules.tavily_serpapi_provider import TavilySerpAPIProvider
from workers.px_r001_research.research_scanner import run_market_scan


class ResearchProvider(Protocol):
    name: str

    def search(self, command: dict[str, object]) -> list[ProviderResult]:
        """Return normalized provider results."""


class SearchUrlProvider:
    name = "Search"
    base_url = "https://www.google.com/search?q="

    def search(self, command: dict[str, object]) -> list[ProviderResult]:
        query = build_query(command)
        return [
            ProviderResult(
                self.name,
                f"{self.name} search for {query}",
                self.base_url + urllib.parse.quote_plus(query),
                f"Search candidate for {query}",
            )
        ]


class GoogleSearchProvider(SearchUrlProvider):
    name = "Google Search"
    base_url = "https://www.google.com/search?q="


class NewsProvider(SearchUrlProvider):
    name = "News"
    base_url = "https://news.google.com/search?q="


class TrustpilotProvider(SearchUrlProvider):
    name = "Trustpilot"
    base_url = "https://www.trustpilot.com/search?query="


class RedditProvider(SearchUrlProvider):
    name = "Reddit"
    base_url = "https://www.reddit.com/search/?q="


class GitHubProvider(SearchUrlProvider):
    name = "GitHub Repositories"
    base_url = "https://github.com/search?q="


class ProductHuntProvider(SearchUrlProvider):
    name = "Product Hunt"
    base_url = "https://www.producthunt.com/search?q="


class DocumentationProvider(SearchUrlProvider):
    name = "Documentation Sites"
    base_url = "https://www.google.com/search?q="

    def search(self, command: dict[str, object]) -> list[ProviderResult]:
        query = build_query(command) + " documentation docs API"
        return [ProviderResult(self.name, f"Documentation search for {query}", self.base_url + urllib.parse.quote_plus(query), query)]


class PublicAPIProvider(SearchUrlProvider):
    name = "Public APIs"
    base_url = "https://www.google.com/search?q="

    def search(self, command: dict[str, object]) -> list[ProviderResult]:
        query = build_query(command) + " public API pricing"
        return [ProviderResult(self.name, f"Public API search for {query}", self.base_url + urllib.parse.quote_plus(query), query)]


class CompanyWebsiteProvider:
    name = "Company Website"

    def search(self, command: dict[str, object]) -> list[ProviderResult]:
        website = str(command.get("website") or "").strip()
        if not website:
            return []
        if not website.startswith(("http://", "https://")):
            website = "https://" + website
        text = fetch_text(website)
        snippet = text[:500] if text else f"Company website provided: {website}"
        return [ProviderResult(self.name, f"Company website: {website}", website, snippet, "website")]


class RSSProvider:
    name = "RSS Feeds"

    def search(self, command: dict[str, object]) -> list[ProviderResult]:
        feed_url = str(command.get("rss_url") or "").strip()
        if not feed_url:
            return []
        text = fetch_text(feed_url)
        titles = re.findall(r"<title>(.*?)</title>", text, flags=re.IGNORECASE | re.DOTALL)[:5]
        return [
            ProviderResult(self.name, clean_html(title), feed_url, clean_html(title), "rss")
            for title in titles
        ]


DEFAULT_PROVIDERS: list[ResearchProvider] = [
    TavilySerpAPIProvider(),
    NewsAPIProvider(),
    GoogleSearchProvider(),
    NewsProvider(),
    RSSProvider(),
    CompanyWebsiteProvider(),
    TrustpilotProvider(),
    RedditProvider(),
    GitHubProvider(),
    ProductHuntProvider(),
    DocumentationProvider(),
    PublicAPIProvider(),
]


def fetch_text(url: str, timeout: int = 5) -> str:
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "ProjectExchangeBot/0.1"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content = response.read(200_000)
        return clean_html(content.decode("utf-8", errors="ignore"))
    except Exception:
        return ""


def clean_html(value: str) -> str:
    value = re.sub(r"<script.*?</script>", " ", value, flags=re.IGNORECASE | re.DOTALL)
    value = re.sub(r"<style.*?</style>", " ", value, flags=re.IGNORECASE | re.DOTALL)
    value = re.sub(r"<[^>]+>", " ", value)
    return " ".join(value.split())


def dedupe_results(results: list[ProviderResult]) -> list[ProviderResult]:
    seen: set[str] = set()
    deduped: list[ProviderResult] = []
    for result in results:
        key = (result.url or result.title).lower().strip()
        if key and key not in seen:
            seen.add(key)
            deduped.append(result)
    return deduped


def extract_signals(results: list[ProviderResult], command: dict[str, object]) -> dict[str, object]:
    text = " ".join([result.title + " " + result.snippet for result in results])
    lower = text.lower()
    complaints = sentences_matching(text, ["complain", "slow", "issue", "problem", "bug", "expensive", "support"])
    opportunities = sentences_matching(text, ["manual", "workflow", "automate", "delay", "integration", "report"])
    competitors = sorted(set(re.findall(r"\b[A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)?\b", text)))[:10]
    pricing = sorted(set(re.findall(r"(?:[$€£]\s?\d+(?:\.\d+)?|\d+\s?(?:per month|/mo|monthly|pricing))", text, re.IGNORECASE)))[:10]
    trends = [word for word in ["ai", "automation", "integration", "self-service", "analytics", "workflow"] if word in lower]
    if not complaints:
        complaints = [f"More evidence needed for {command.get('company') or command.get('market') or 'this market'}."]
    return {
        "findings": [result.snippet for result in results[:8]],
        "complaints": complaints[:8],
        "opportunities": opportunities[:8],
        "competitors": competitors,
        "pricing": pricing,
        "trends": trends,
    }


def sentences_matching(text: str, keywords: list[str]) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    matches = []
    for sentence in sentences:
        lower = sentence.lower()
        if any(keyword in lower for keyword in keywords):
            matches.append(sentence.strip()[:240])
    return [match for match in matches if match]


def confidence_score(results: list[ProviderResult], signals: dict[str, object]) -> int:
    score = min(55 + len(results) * 4, 85)
    if signals["complaints"]:
        score += 5
    if signals["opportunities"]:
        score += 5
    if signals["pricing"]:
        score += 3
    return min(score, 100)


def run_internet_research(
    db_path: str | Path,
    command: dict[str, object],
    providers: list[ResearchProvider] | None = None,
) -> dict[str, object]:
    providers = providers or DEFAULT_PROVIDERS
    query = build_query(command)
    all_results: list[ProviderResult] = []
    for provider in providers:
        provider_id = record_provider_start(db_path, provider.name, query)
        try:
            results = provider.search(command)
            record_provider_finish(db_path, provider_id, "completed", len(results), "")
            all_results.extend(results)
        except Exception as exc:
            safe_error = f"{provider.name} request failed"
            record_provider_finish(db_path, provider_id, "failed", 0, safe_error)
            add_log(db_path, "warning", safe_error, "PX-R001", status="provider_failed")
    deduped = dedupe_results(all_results)
    signals = extract_signals(deduped, command)
    score = confidence_score(deduped, signals)
    source_text = "\n".join(f"{result.provider}: {result.title}. {result.snippet}" for result in deduped)
    research = run_market_scan(
        db_path,
        market=str(command.get("market") or command.get("industry") or "Unknown Market"),
        source_text=source_text or query,
        company=str(command.get("company") or ""),
        source_url=deduped[0].url if deduped else str(command.get("website") or ""),
        source_type="internet_research",
    )
    package = store_research_package(db_path, research["id"], command, deduped, signals, score, research)
    add_event(db_path, "InternetResearchCompleted", "PX-R001", "Internet research completed", "pending_audit", str(package["id"]))
    add_log(db_path, "info", f"Internet research package created: {package['id']}", "PX-R001", status="completed")
    return {"research": research, "package": package}


def record_provider_start(db_path: str | Path, provider_name: str, query: str) -> str:
    with connect(db_path) as connection:
        provider_id = next_sequence_id("PROV", count_rows(connection, "provider_runs"))
        connection.execute(
            """
            INSERT INTO provider_runs (id, provider_name, query, status, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (provider_id, provider_name, query, "running", utc_now()),
        )
    return provider_id


def record_provider_finish(db_path: str | Path, provider_id: str, status: str, result_count: int, error: str) -> None:
    with connect(db_path) as connection:
        connection.execute(
            "UPDATE provider_runs SET status = ?, result_count = ?, error = ? WHERE id = ?",
            (status, result_count, error, provider_id),
        )


def store_research_package(
    db_path: str | Path,
    research_id: str,
    command: dict[str, object],
    results: list[ProviderResult],
    signals: dict[str, object],
    score: int,
    research_record: dict[str, object] | None = None,
) -> dict[str, object]:
    with connect(db_path) as connection:
        package_id = next_sequence_id("RPK", count_rows(connection, "research_packages"))
        package = {
            "id": package_id,
            "research_id": research_id,
            "company": command.get("company") or "",
            "industry": command.get("industry") or "",
            "website": command.get("website") or "",
            "keyword": command.get("keyword") or "",
            "market": command.get("market") or "",
            "country": command.get("country") or "",
            "providers": sorted(set(result.provider for result in results)),
            "evidence_score": (research_record or {}).get("evidence_score") or score,
            "complaint_summary": "; ".join(signals.get("complaints", [])[:3]),
            "opportunity_summary": "; ".join(signals.get("opportunities", [])[:3]),
            "trend_summary": ", ".join(signals.get("trends", [])[:8]),
            "competitor_summary": ", ".join(signals.get("competitors", [])[:8]),
            "recommended_actions": json.dumps(recommended_actions(signals, score), ensure_ascii=False),
            "confidence_score": score,
            "status": "pending_audit",
            "research_history": json.dumps([{"timestamp": utc_now(), "action": "package_created", "worker": "PX-R001"}]),
            "research_schedule": str(command.get("schedule") or command.get("cadence") or "manual"),
            "research_performance": json.dumps({"result_count": len(results), "provider_count": len(set(result.provider for result in results)), "confidence_score": score}),
            "sources": [result.__dict__ for result in results],
            **signals,
        }
        connection.execute(
            """
            INSERT INTO research_packages
            (id, research_id, company, industry, website, keyword, market, country, providers, findings, complaints,
             opportunities, competitors, pricing, trends, evidence_score, complaint_summary, opportunity_summary,
             trend_summary, competitor_summary, recommended_actions, confidence_score, status, research_history,
             research_schedule, research_performance, sources, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                package_id,
                research_id,
                package["company"],
                package["industry"],
                package["website"],
                package["keyword"],
                package["market"],
                package["country"],
                json.dumps(package["providers"]),
                json.dumps(package["findings"]),
                json.dumps(package["complaints"]),
                json.dumps(package["opportunities"]),
                json.dumps(package["competitors"]),
                json.dumps(package["pricing"]),
                json.dumps(package["trends"]),
                package["evidence_score"],
                package["complaint_summary"],
                package["opportunity_summary"],
                package["trend_summary"],
                package["competitor_summary"],
                package["recommended_actions"],
                score,
                package["status"],
                package["research_history"],
                package["research_schedule"],
                package["research_performance"],
                json.dumps(package["sources"]),
                utc_now(),
            ),
        )
        connection.execute(
            """
            INSERT INTO research_history (research_id, action, details, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (research_id, "package_created", json.dumps({"package_id": package_id, "confidence_score": score}), utc_now()),
        )
        upsert_research_performance(connection, package)
        add_changelog(connection, package_id, "research_package", f"Created real-world research package for {package['company'] or package['market']}.")
    return package


def recommended_actions(signals: dict[str, object], score: int) -> list[str]:
    actions = []
    if signals.get("complaints"):
        actions.append("Send complaints to PX-A001 for evidence audit.")
    if signals.get("opportunities"):
        actions.append("Cluster opportunities against existing Library records.")
    if score < 70:
        actions.append("Schedule follow-up research with stronger sources.")
    if not actions:
        actions.append("Monitor this market again on the next operating cycle.")
    return actions


def upsert_research_performance(connection, package: dict[str, object]) -> None:
    market = str(package.get("market") or "")
    company = str(package.get("company") or "")
    existing = connection.execute(
        "SELECT * FROM research_performance WHERE market = ? AND company = ?",
        (market, company),
    ).fetchone()
    now = utc_now()
    if existing:
        package_count = int(existing["package_count"] or 0) + 1
        average_confidence = round(((float(existing["average_confidence"] or 0) * (package_count - 1)) + float(package["confidence_score"])) / package_count, 1)
        average_evidence = round(((float(existing["average_evidence"] or 0) * (package_count - 1)) + float(package.get("evidence_score") or 0)) / package_count, 1)
        connection.execute(
            """
            UPDATE research_performance
            SET package_count = ?, average_confidence = ?, average_evidence = ?, last_researched_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (package_count, average_confidence, average_evidence, now, now, existing["id"]),
        )
        return
    performance_id = next_sequence_id("RPF", count_rows(connection, "research_performance"))
    connection.execute(
        """
        INSERT INTO research_performance
        (id, market, company, package_count, average_confidence, average_evidence, duplicate_count, last_researched_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (performance_id, market, company, 1, float(package["confidence_score"]), float(package.get("evidence_score") or 0), 0, now, now),
    )
