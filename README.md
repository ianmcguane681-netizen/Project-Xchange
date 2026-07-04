# Project Exchange Local Prototype

Local Python/Streamlit prototype for the Project Exchange internal operating system:

`PX-H001 Head of Functions -> PX-R001 Market Research Scanner -> PX-A001 Audit Worker -> PX-L001 Library Manager`

It also includes `COMP-001 Prompt Engine` for storing, versioning, approving, testing, searching, retiring, and rolling back prompts.

## What Works

- SQLite persistence in `data/project_exchange.db`
- Streamlit UI in `streamlit_app.py`
- JSON import/export for research, audit, library, prompt, and prompt test records
- Sample data in `data/`
- PX-EOS Dashboard with worker status, queue counts, health, latest activity, and notifications
- Event bus for durable `ResearchCreated`, `AuditApproved`, `LibraryStored`, `PromptCreated`, `WorkerStarted`, `WorkerFinished`, and failure events
- PX Job Engine for `Research Scan`, `Audit Scan`, `Library Store`, `Prompt Test`, `Prompt Approval`, `Component Build`, `Worker Update`, and `System Scan`
- Job queues: Pending, Running, Waiting, Completed, Failed, Cancelled
- Structured logs and recoverable failure history
- Error management actions: retry job, resume job, cancel job, restart worker, view stack trace
- System analytics: job counts, average runtime, audit score, research processed, library growth, prompt success, worker utilisation, storage used
- Timeline page with event filtering
- Worker Registry with runtime, success rate, dependencies, components, and prompt version
- Component Registry with purpose, version, tests, dependencies, workers using it, and status
- Permanent Milestone System and Engineering Journal
- Pipeline queues:
  - PX-R001 extracts a complaint signal from source text
  - Pending Audit Queue feeds PX-A001
  - Approved Queue feeds PX-L001
  - PX-L001 stores approved records in the Library
- Worker activity history with timestamps, duration, inputs, outputs, decisions, and errors
- Notifications for research packs, audits, library updates, prompt approvals, and failed prompt tests
- Library search, categories, tags, versions, audit history, and changelog
- Research input from pasted text, pasted URL, TXT, CSV, and PDF upload
- Basic tests with `pytest`

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run The App

```powershell
streamlit run streamlit_app.py
```

## Run The Foundry API

```powershell
python foundry_api.py
```

The read-only Lovable integration API serves Provena state from SQLite at `http://localhost:8000/api/foundry/*`.
See `docs/foundry_api.md` for the JSON contract.

## Run Tests

```powershell
pytest
```

## Repository Map

```text
components/comp_001_prompt_engine/  Prompt storage, versioning, approval, tests
workers/px_a001_audit/              Audit and verification worker
workers/px_l001_library/            Library manager worker
workers/px_r001_research/           Market research scanner worker
project_exchange/                   Shared SQLite, IDs, and JSON helpers
data/                               Sample input/output data and local DB
tests/                              Basic workflow tests
```

## Notes

This is intentionally not an AI/API-driven build yet. The first version proves the internal operating workflow locally with deterministic rules. OpenAI or other model calls can be added behind the same worker interfaces later.

## Sprint 2 Notes

The app now treats Project Exchange as an operating system rather than separate tools. Shared EOS logic lives in `project_exchange/eos.py`; worker modules report into that layer instead of the UI inventing its own state.

Sprint 3 adds the durable OS primitives future Workers should plug into:

- `events`
- `worker_activity`
- `notifications`
- `milestones`
- `engineering_journal`
- enriched `workers` and `components` registries

Sprint 4 adds the autonomous execution layer:

- `jobs`
- `system_logs`
- `failure_history`
- `project_exchange/providers.py` placeholder interfaces for future external providers
- synchronous local orchestration through `project_exchange/eos.py`

Sprint 5 adds the real-world integration layer:

- independent research providers in `project_exchange/research_engine.py`
- multi-provider research packages stored in `research_packages`
- provider run history in `provider_runs`
- provider-neutral LLM abstraction in `project_exchange/llm.py`
- PX Command Console in the Streamlit app
- settings storage in `settings`
- worker-to-worker messages in `worker_messages`
- knowledge graph relationships in `knowledge_edges`
- prompt benchmarking and A/B test records in `prompt_benchmarks`
- expanded Library search filters
- root `.env` loading through `python-dotenv`
- provider connection statuses for OpenAI, Tavily, SerpAPI, and NewsAPI without exposing secret values

Sprint 6 adds the intelligence and orchestration layer:

- `PX-H001 Head of Functions` as the command planner and orchestration worker
- execution plans in `execution_plans`
- PX-H001-owned jobs with dependencies, parent plan IDs, and job history
- worker memory in `worker_memory`
- routed worker communication through PX-H001 with priority, payload, and status
- persistent PX-A001 reasoning in `audit_reasoning`
- self-improvement recommendations in `system_recommendations`
- a dedicated PX-H001 Streamlit page for memory, recovery scans, plans, and recommendations

Sprint 8 turns the five base workers into operational workers:

- objectives in `objectives`
- recurring/manual schedules in `operating_schedules`
- daily and weekly operating briefs in `operating_briefs`
- worker load monitoring and performance snapshots in `performance_snapshots`
- richer research packages with summaries, recommended actions, history, schedule, and performance data
- audit reasoning with evidence matrix, source quality, missing evidence, bias, duplicate risk, and recommendation
- Library lineage fields for research origin, auditing, workers, source tracking, companies, industries, and opportunities
- prompt usage records, token estimates, response quality, success tracking, and best-prompt selection

Golden Study 001 adds the verified opportunity database workflow for Global Property Management:

- default `GS-001` study in `studies`
- raw evidence signals in `study_signals`
- repeated complaint patterns in `study_findings`
- auditable finding scores and OCI in `finding_audits`
- approved opportunity records in `opportunity_records`
- traceability from Opportunity -> Audit -> Finding -> Signals -> Sources
- executive study briefs in `study_briefs`
- Golden Study 001 Streamlit tab for study control, signals, findings, audits, opportunities, traceability, and coverage

The database migrates existing local SQLite files on startup, so old Sprint 1 data can remain in `data/project_exchange.db`.

## Provider Keys

Create or update `.env` in the project root with any of these names:

```text
OPENAI_API_KEY=...
TAVILY_API_KEY=...
SERPAPI_API_KEY=...
NEWSAPI_API_KEY=...
```

The Provider Settings page only shows `connected`, `disconnected`, or `invalid`. It never displays key values.
