# Provena Foundry OS API

The Streamlit/Python engine remains the source of truth. This API is read-only and exposes current Provena/GS-001 state as JSON for the Lovable Foundry OS frontend.

Run locally:

```powershell
python foundry_api.py
```

Base URL:

```text
http://localhost:8000
```

Set CORS origins for Lovable if needed:

```powershell
$env:FOUNDRY_CORS_ORIGINS="https://*.lovable.app,http://localhost:5173"
```

No API keys, provider secrets, tokens, passwords, or authorization values are returned by the API.

## Endpoints

- `GET /api/foundry/mission-control`
  Answers: What decision should we make next?

- `GET /api/foundry/discovery`
  Answers: What did we find?

- `GET /api/foundry/verification`
  Answers: Can we trust it?

- `GET /api/foundry/intelligence`
  Answers: What pattern exists?

- `GET /api/foundry/due-diligence`
  Answers: Should we build software?

- `GET /api/foundry/blueprints`
  Answers: What are we building?

- `GET /api/foundry/schema-examples`
  Returns small example payloads for Lovable mapping.

## Card Shape

Every evidence card follows the three-level decision hierarchy:

```json
{
  "executive_summary": "Production evidence: source has 82% decision confidence.",
  "decision": {
    "authority": "PASS",
    "commercial_relevance": "PASS",
    "traceability": "PASS",
    "independent_sources": "1 / 2",
    "independent_events": "1 / 2",
    "organisations": "1 / 2",
    "current_recommendation": "Use as accepted production evidence, then collect independent corroboration."
  },
  "detail": {
    "raw_evidence": "Evidence quote...",
    "metadata": {
      "provider": "Tavily",
      "original_query": "tenant complaint maintenance no response",
      "retrieved_at": "2026-07-04T18:00:00Z"
    },
    "source_url": "https://example.com/source",
    "entity_mapping": {
      "country": "United States",
      "stakeholder": "Tenant"
    },
    "classification": "complaint",
    "reasoning": "Accepted because source is independent and complaint context is clear."
  }
}
```
