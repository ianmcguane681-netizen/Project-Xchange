from __future__ import annotations

import json
import urllib.parse
import urllib.request

from project_exchange.config import secret, status_for_key
from project_exchange.provider_base import ProviderResult, build_query


class TavilySearchProvider:
    name = "Tavily"
    env_var = "TAVILY_API_KEY"

    def status(self):
        return status_for_key(self.name, self.env_var, (), 12)

    def search(self, command: dict[str, object]) -> list[ProviderResult]:
        api_key = secret(self.env_var)
        if not api_key:
            return []
        body = {
            "api_key": api_key,
            "query": build_query(command),
            "search_depth": "basic",
            "max_results": 5,
        }
        request = urllib.request.Request(
            "https://api.tavily.com/search",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
        return [
            ProviderResult(
                self.name,
                str(item.get("title") or item.get("url") or "Tavily result"),
                str(item.get("url") or ""),
                str(item.get("content") or ""),
                "api_search",
            )
            for item in data.get("results", [])
        ]


class SerpAPISearchProvider:
    name = "SerpAPI"
    env_var = "SERPAPI_API_KEY"

    def status(self):
        return status_for_key(self.name, self.env_var, (), 12)

    def search(self, command: dict[str, object]) -> list[ProviderResult]:
        api_key = secret(self.env_var)
        if not api_key:
            return []
        params = urllib.parse.urlencode(
            {
                "engine": "google",
                "q": build_query(command),
                "api_key": api_key,
                "num": 5,
            }
        )
        request = urllib.request.Request(f"https://serpapi.com/search.json?{params}")
        with urllib.request.urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
        return [
            ProviderResult(
                self.name,
                str(item.get("title") or item.get("link") or "SerpAPI result"),
                str(item.get("link") or ""),
                str(item.get("snippet") or ""),
                "api_search",
            )
            for item in data.get("organic_results", [])
        ]


class TavilySerpAPIProvider:
    name = "Tavily/SerpAPI"

    def __init__(self) -> None:
        self.tavily = TavilySearchProvider()
        self.serpapi = SerpAPISearchProvider()

    def status(self):
        tavily_status = self.tavily.status()
        serpapi_status = self.serpapi.status()
        if tavily_status.status == "connected" or serpapi_status.status == "connected":
            return type(tavily_status)(self.name, "connected", "At least one search API key loaded", "TAVILY_API_KEY or SERPAPI_API_KEY")
        if tavily_status.status == "invalid" or serpapi_status.status == "invalid":
            return type(tavily_status)(self.name, "invalid", "One or more search API keys look invalid", "TAVILY_API_KEY or SERPAPI_API_KEY")
        return type(tavily_status)(self.name, "disconnected", "No Tavily or SerpAPI key loaded", "TAVILY_API_KEY or SERPAPI_API_KEY")

    def search(self, command: dict[str, object]) -> list[ProviderResult]:
        results: list[ProviderResult] = []
        for provider in [self.tavily, self.serpapi]:
            try:
                results.extend(provider.search(command))
            except Exception:
                continue
        return results
