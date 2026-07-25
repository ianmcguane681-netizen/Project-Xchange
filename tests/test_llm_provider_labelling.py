"""A reasoning record must name the engine that actually produced it.

The provider subclasses set `name` as a plain class attribute over a frozen
dataclass field, so the generated __init__ reassigned the parent default and every
override was silently dead: OpenAIProvider().name was "Local Heuristic". A genuine
OpenAI result was therefore recorded as local heuristic output, and the requested
provider was lost entirely.
"""
from __future__ import annotations

import pytest

from project_exchange.llm import (
    HEURISTIC_ENGINE,
    AnthropicProvider,
    AzureOpenAIProvider,
    GeminiProvider,
    HeuristicLLMProvider,
    OllamaProvider,
    OpenAIProvider,
    get_llm_provider,
)

PAYLOAD = {
    "source_count": 3,
    "evidence_score": 80,
    "source_url": "https://example.com",
    "complaint_summary": "summary",
    "workflow_cluster": "cluster",
}


@pytest.mark.parametrize(
    ("provider_class", "expected_name"),
    [
        (AnthropicProvider, "Anthropic"),
        (OllamaProvider, "Ollama"),
        (GeminiProvider, "Gemini"),
        (AzureOpenAIProvider, "Azure OpenAI"),
        (OpenAIProvider, "OpenAI"),
        (HeuristicLLMProvider, HEURISTIC_ENGINE),
    ],
)
def test_provider_name_override_takes_effect(provider_class, expected_name):
    assert provider_class().name == expected_name


@pytest.mark.parametrize(
    ("requested", "expected_name"),
    [("anthropic", "Anthropic"), ("gemini", "Gemini"), ("ollama", "Ollama")],
)
def test_unimplemented_providers_report_the_engine_that_ran(requested, expected_name):
    result = get_llm_provider(requested).reason("prompt", PAYLOAD)

    assert result["provider"] == HEURISTIC_ENGINE
    assert result["requested_provider"] == expected_name


def test_openai_records_a_fallback_reason_when_disconnected(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    result = OpenAIProvider().reason("prompt", PAYLOAD)

    assert result["provider"] == HEURISTIC_ENGINE
    assert result["requested_provider"] == "OpenAI"
    assert result["fallback_reason"]


def test_successful_openai_result_is_not_labelled_as_heuristic(monkeypatch):
    class Connected:
        def status(self):
            return type("S", (), {"status": "connected"})()

        def reason(self, prompt, payload):
            return {"confidence": 88, "reasoning": "remote reasoning"}

    monkeypatch.setattr("project_exchange.llm.OpenAIReasoningProvider", Connected)

    result = OpenAIProvider().reason("prompt", PAYLOAD)

    assert result["provider"] == "OpenAI"
    assert "fallback_reason" not in result


def test_openai_transport_failure_falls_back_and_says_why(monkeypatch):
    class Failing:
        def status(self):
            return type("S", (), {"status": "connected"})()

        def reason(self, prompt, payload):
            raise RuntimeError("upstream unavailable")

    monkeypatch.setattr("project_exchange.llm.OpenAIReasoningProvider", Failing)

    result = OpenAIProvider().reason("prompt", PAYLOAD)

    assert result["provider"] == HEURISTIC_ENGINE
    assert "upstream unavailable" in result["fallback_reason"]
