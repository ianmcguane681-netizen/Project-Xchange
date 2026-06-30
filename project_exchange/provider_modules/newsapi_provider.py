from __future__ import annotations

import json
import urllib.parse
import urllib.request

from project_exchange.config import secret, status_for_key
from project_exchange.provider_base import ProviderResult, build_query


class NewsAPIProvider:
    name = "NewsAPI"
    env_var = "NEWSAPI_API_KEY"

    def status(self):
        return status_for_key(self.name, self.env_var, (), 12)

    def search(self, command: dict[str, object]) -> list[ProviderResult]:
        api_key = secret(self.env_var)
        if not api_key:
            return []
        params = urllib.parse.urlencode(
            {
                "q": build_query(command),
                "language": "en",
                "pageSize": 5,
                "apiKey": api_key,
            }
        )
        request = urllib.request.Request(f"https://newsapi.org/v2/everything?{params}")
        with urllib.request.urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
        return [
            ProviderResult(
                self.name,
                str(article.get("title") or "NewsAPI article"),
                str(article.get("url") or ""),
                str(article.get("description") or article.get("content") or ""),
                "news_api",
            )
            for article in data.get("articles", [])
        ]
