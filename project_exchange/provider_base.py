from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderResult:
    provider: str
    title: str
    url: str
    snippet: str
    source_type: str = "search_result"


def build_query(command: dict[str, object]) -> str:
    parts = [
        str(command.get("company") or ""),
        str(command.get("industry") or ""),
        str(command.get("market") or ""),
        str(command.get("keyword") or ""),
        "complaints pricing competitors trends",
    ]
    return " ".join(part for part in parts if part).strip()
