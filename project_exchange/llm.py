from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

from project_exchange.provider_modules.openai_provider import OpenAIReasoningProvider


class LLMProvider(Protocol):
    name: str

    def reason(self, prompt: str, payload: dict[str, object]) -> dict[str, object]:
        """Return structured reasoning from an LLM provider."""


@dataclass(frozen=True)
class HeuristicLLMProvider:
    name: str = "Local Heuristic"

    def reason(self, prompt: str, payload: dict[str, object]) -> dict[str, object]:
        text = json.dumps(payload, ensure_ascii=False).lower()
        source_count = int(payload.get("source_count") or 0)
        evidence_score = int(payload.get("evidence_score") or 0)
        credibility = min(100, 35 + source_count * 10 + evidence_score // 3)
        bias = "medium" if any(word in text for word in ["sponsored", "ad ", "affiliate"]) else "low"
        missing = []
        for field in ["source_url", "complaint_summary", "workflow_cluster"]:
            if not payload.get(field):
                missing.append(field)
        recommendation = "approve" if credibility >= 70 and not missing else "needs_review"
        if "duplicate" in text:
            recommendation = "needs_review"
        return {
            "provider": self.name,
            "credibility": credibility,
            "source_quality": "strong" if source_count >= 3 else "limited",
            "evidence_quality": "strong" if evidence_score >= 75 else "moderate" if evidence_score >= 50 else "weak",
            "missing_information": missing,
            "bias": bias,
            "confidence": min(100, credibility),
            "recommendation": recommendation,
            "reasoning": "Local deterministic reasoning used because no external LLM provider is configured.",
        }


class OpenAIProvider(HeuristicLLMProvider):
    name = "OpenAI"

    def reason(self, prompt: str, payload: dict[str, object]) -> dict[str, object]:
        provider = OpenAIReasoningProvider()
        if provider.status().status != "connected":
            return HeuristicLLMProvider(self.name).reason(prompt, payload)
        try:
            result = provider.reason(prompt, payload)
        except Exception:
            return HeuristicLLMProvider(self.name).reason(prompt, payload)
        return {
            "credibility": int(result.get("credibility") or result.get("confidence") or 70),
            "source_quality": str(result.get("source_quality") or "unknown"),
            "evidence_quality": str(result.get("evidence_quality") or "unknown"),
            "missing_information": result.get("missing_information") or [],
            "bias": str(result.get("bias") or "unknown"),
            "confidence": int(result.get("confidence") or 70),
            "recommendation": str(result.get("recommendation") or "needs_review"),
            "reasoning": str(result.get("reasoning") or "OpenAI reasoning completed."),
            "provider": self.name,
        }


class AnthropicProvider(HeuristicLLMProvider):
    name = "Anthropic"


class OllamaProvider(HeuristicLLMProvider):
    name = "Ollama"


class GeminiProvider(HeuristicLLMProvider):
    name = "Gemini"


class AzureOpenAIProvider(HeuristicLLMProvider):
    name = "Azure OpenAI"


def get_llm_provider(name: str = "") -> LLMProvider:
    providers: dict[str, LLMProvider] = {
        "openai": OpenAIProvider(),
        "anthropic": AnthropicProvider(),
        "ollama": OllamaProvider(),
        "gemini": GeminiProvider(),
        "azure openai": AzureOpenAIProvider(),
        "local heuristic": HeuristicLLMProvider(),
        "": HeuristicLLMProvider(),
    }
    return providers.get(name.lower().strip(), HeuristicLLMProvider())
