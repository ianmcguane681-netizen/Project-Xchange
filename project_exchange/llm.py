from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Protocol

from project_exchange.provider_modules.openai_provider import OpenAIReasoningProvider

logger = logging.getLogger(__name__)


class LLMProvider(Protocol):
    name: str

    def reason(self, prompt: str, payload: dict[str, object]) -> dict[str, object]:
        """Return structured reasoning from an LLM provider."""


HEURISTIC_ENGINE = "Local Heuristic"


@dataclass(frozen=True)
class HeuristicLLMProvider:
    """Deterministic local reasoning.

    `name` records which provider was *requested*; the returned `provider` field
    always reports the engine that actually produced the result. Stamping the
    requested name onto heuristic output previously produced records that claimed
    an inference source which never ran.
    """

    name: str = HEURISTIC_ENGINE

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
            "provider": HEURISTIC_ENGINE,
            "requested_provider": self.name,
            "credibility": credibility,
            "source_quality": "strong" if source_count >= 3 else "limited",
            "evidence_quality": "strong" if evidence_score >= 75 else "moderate" if evidence_score >= 50 else "weak",
            "missing_information": missing,
            "bias": bias,
            "confidence": min(100, credibility),
            "recommendation": recommendation,
            "reasoning": "Local deterministic reasoning used because no external LLM provider is configured.",
        }


@dataclass(frozen=True)
class OpenAIProvider(HeuristicLLMProvider):
    name: str = "OpenAI"

    def reason(self, prompt: str, payload: dict[str, object]) -> dict[str, object]:
        provider = OpenAIReasoningProvider()
        if provider.status().status != "connected":
            return self._fallback(prompt, payload, "provider is not connected")
        try:
            result = provider.reason(prompt, payload)
        except Exception as exc:
            logger.warning("OpenAI reasoning failed, falling back to local heuristic: %s", exc)
            return self._fallback(prompt, payload, f"{type(exc).__name__}: {exc}")
        return {
            "credibility": int(result.get("credibility") or result.get("confidence") or 70),
            "source_quality": str(result.get("source_quality") or "unknown"),
            "evidence_quality": str(result.get("evidence_quality") or "unknown"),
            "missing_information": result.get("missing_information") or [],
            "bias": str(result.get("bias") or "unknown"),
            "confidence": int(result.get("confidence") or 70),
            "recommendation": str(result.get("recommendation") or "needs_review"),
            "reasoning": str(result.get("reasoning") or "OpenAI reasoning completed."),
            # self.name, not a hardcoded label: a real OpenAI result must not be
            # recorded as local heuristic output.
            "provider": self.name,
            "requested_provider": self.name,
        }

    def _fallback(self, prompt: str, payload: dict[str, object], why: str) -> dict[str, object]:
        result = HeuristicLLMProvider(self.name).reason(prompt, payload)
        result["fallback_reason"] = why
        return result


# Not yet implemented. These select the local heuristic engine, and the result
# records provider="Local Heuristic" with requested_provider set to the name
# below, so a record never claims an inference source that did not run.
@dataclass(frozen=True)
class AnthropicProvider(HeuristicLLMProvider):
    name: str = "Anthropic"


@dataclass(frozen=True)
class OllamaProvider(HeuristicLLMProvider):
    name: str = "Ollama"


@dataclass(frozen=True)
class GeminiProvider(HeuristicLLMProvider):
    name: str = "Gemini"


@dataclass(frozen=True)
class AzureOpenAIProvider(HeuristicLLMProvider):
    name: str = "Azure OpenAI"


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
