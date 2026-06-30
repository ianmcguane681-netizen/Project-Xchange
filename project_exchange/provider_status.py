from __future__ import annotations

from project_exchange.config import env_file_status
from project_exchange.provider_modules.newsapi_provider import NewsAPIProvider
from project_exchange.provider_modules.openai_provider import OpenAIReasoningProvider
from project_exchange.provider_modules.tavily_serpapi_provider import SerpAPISearchProvider, TavilySearchProvider


def provider_connection_rows() -> list[dict[str, object]]:
    env_status = env_file_status()
    rows = []
    for provider in [
        OpenAIReasoningProvider(),
        TavilySearchProvider(),
        SerpAPISearchProvider(),
        NewsAPIProvider(),
    ]:
        status = provider.status()
        rows.append(
            {
                "provider": status.provider,
                "status": status.status,
                "detail": status.detail,
                "env_var": status.env_var,
                "env_file_detected": env_status["env_file_detected"],
            }
        )
    return rows
