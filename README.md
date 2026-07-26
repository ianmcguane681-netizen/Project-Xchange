# Project Exchange Local Prototype

Local Python/Streamlit prototype for the Project Exchange internal operating system:

`PX-H001 Head of Functions Operator -> PX-R001 Research Acquisition Operator -> PX-A001 Evidence Verification Operator -> PX-L001 Library Steward Operator`

It also includes `COMP-001 Prompt Engine` for storing, versioning, approving, testing, searching, retiring, and rolling back prompts.

## Review Board Engine Runtime v0.1

The repository includes a headless, deterministic RBE Foundation runtime under
`rbe_runtime/`. It consumes RBE-001 v1.1.0 and RBM-001 v2.0.0 directly, uses
the backend-neutral `ReviewStore` contract with SQLite as its Foundation adapter,
enforces the canonical lifecycle, preserves
evidence and provenance, computes profile-driven outcomes, records separated
human ratification and publication, and exports verifiable JSON/Markdown
bundles.

RBM-001 remains `RELEASE_CANDIDATE`. Runtime outputs are therefore advisory,
non-binding, and always `merge_permitted=false`.

```powershell
python -m rbe_runtime validate-authority
python -m pytest tests/test_rbe_runtime_*.py
```

See `docs/rbe-runtime/README.md` for the developer contract and commands.

## Commercial Pipeline

`commercial/` covers what happens between "the problem is proven" and "the product
is in the market". None of it is market-specific, so it sits outside any single
study.

- **`agent_guard`** — agent output is analysis or a proposal, never evidence. The
  rule holds structurally: `is_evidence` is not a settable field, agent provenance
  is detected even through a serialised dict, and `assert_not_evidence` refuses
  agent output at any position that requires proof. A proposal additionally needs a
  named human reviewer before it can be acted on.
- **`buyer`** — every study source is documentary and none of it shows anyone will
  pay. This lane records buyer conversations as evidence with named provenance and
  recorded consent, and holds the gate to distinct organisations, at least one
  respondent with budget authority, and a verbatim account. One enthusiastic
  conversation does not qualify.
- **`stop_rules`** — a study that can always ask for more evidence will. Given a
  budget and a study's state, returns one deterministic decision: objective met,
  budget exhausted, no progress, externally blocked, or continue. Objective met is
  checked first, so a study that achieved its aim is never reported as overspent.
- **`claims`** — a public claim must trace to approved evidence or it cannot be
  published. Agent-drafted support is recorded as `AGENT_ASSERTED`, unreviewed
  support is distinguished from no support, and evidence flagged as contradicted
  blocks the claim outright.
- **`outcomes`** — records what was predicted against what was observed after
  launch, respecting whether higher or lower is better, and reporting an
  underpowered sample as inconclusive rather than rounding it toward the claim. A
  measured shortfall flags the claim as contradicted and returns to the evidence
  base as `E7_PROTOTYPE` evidence, so the next decision inherits what actually
  happened.

The dependency runs one way: `commercial` may use `rbe_runtime`, never the reverse.

## Golden Study Bridge

`study_bridge/` joins the two audit chains that previously ran side by side. A
Golden Study proves its own integrity per run through a proof bundle and checksum
file; the RBE runtime proves its own through a hash-chained, append-only audit log.
Nothing linked them, so no single verifiable thread ran from a raw source record to
a board decision.

`StudyBundle.load()` verifies a bundle before it is trusted: every file must match
its recorded checksum, nothing may be missing, nothing may be present that the
checksum file does not vouch for, and the manifest must name the study, the run and
the exact commit that produced it. A bundle whose manifest cannot resolve its own
commit is refused rather than silently admitted. The verified bundle reduces to one
deterministic `bundle_root_hash`.

`ingest_study_bundle()` then registers each file as evidence on a review session
through the runtime's ordinary evidence path, carrying study identity as
provenance. The board's audit chain therefore commits to the study contents and the
code that produced them, and the runtime's lifecycle still applies - a study re-run
cannot be added after the evidence lock.

The dependency runs one way only: `study_bridge` imports `rbe_runtime`, never the
reverse, so the runtime stays methodology-neutral. CI enforces this.

```python
from rbe_runtime.service import RBERuntime
from study_bridge import StudyBundle, ingest_study_bundle

bundle = StudyBundle.load("../GS-CF001/proof_bundle")
result = ingest_study_bundle(runtime, review_id, bundle, actor="human-chair")
```

## Provena Solution Validation Engine v1

The repository now includes a separate, local `sv_engine/` package that evaluates whether a proposed solution has earned investment in a bounded prototype. It implements the methodology in `docs/sv_engine_methodology_specification.md` without coupling the decision rules to Streamlit or external AI services.

SV Engine v1 provides:

- typed, versioned solution-validation records and Golden Study handoff contract;
- 12 validation categories and eight mandatory gates;
- deterministic `BUILD PROTOTYPE`, `VALIDATE FURTHER`, and `DO NOT BUILD` verdicts;
- evidence-linked scoring and confidence with no credit for unsupported positive claims;
- current/proposed workflow comparison, customer economics, Provena unit economics, and internal operational complexity;
- downside, base, and upside sensitivity analysis with `BORDERLINE` detection;
- stable business hashes separated from metadata-only changes;
- append-only SQLite audit runs plus JSON and Markdown artifacts;
- synthetic fixtures for tests only, clearly excluded from real Provena findings.

Run a controlled example:

```powershell
python -m sv_engine.cli `
  --input examples\sv_engine\inputs\build_prototype.json `
  --output-dir data\sv_engine_output `
  --db data\sv_engine.db
```

See `docs/sv_engine_v1_implementation.md` for architecture, input contracts, rules, execution, testing, migration notes, and current limitations.

## What Works

- SQLite persistence in `data/project_exchange.db`
- Streamlit UI in `streamlit_app.py`
- JSON import/export for research, audit, library, prompt, and prompt test records
- Sample data in `data/`
- PX-EOS Dashboard with Provena Operator status, queue counts, health, latest activity, and notifications
- Event bus for durable `ResearchCreated`, `AuditApproved`, `LibraryStored`, `PromptCreated`, operator start/finish, and failure events
- PX Job Engine for `Research Scan`, `Audit Scan`, `Library Store`, `Prompt Test`, `Prompt Approval`, `Component Build`, `Operator Update`, and `System Scan`
- Job queues: Pending, Running, Waiting, Completed, Failed, Cancelled
- Structured logs and recoverable failure history
- Error management actions: retry job, resume job, cancel job, restart operator, view stack trace
- System analytics: job counts, average runtime, audit score, research processed, library growth, prompt success, operator utilisation, storage used
- Timeline page with event filtering
- Provena Operator Registry with backend module, testable function, status, input, output, and traceable activity
- Component Registry with purpose, version, tests, dependencies, operators using it, and status
- Permanent Milestone System and Engineering Journal
- Pipeline queues:
  - PX-R001 extracts a complaint signal from source text
  - Pending Audit Queue feeds PX-A001
  - Approved Queue feeds PX-L001
  - PX-L001 stores approved records in the Library
- Operator activity history with timestamps, duration, inputs, outputs, decisions, and errors
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
workers/px_a001_audit/              Evidence Verification Operator backend
workers/px_l001_library/            Library Steward Operator backend
workers/px_r001_research/           Research Acquisition Operator backend
project_exchange/                   Shared SQLite, IDs, and JSON helpers
data/                               Sample input/output data and local DB
tests/                              Basic workflow tests
```

## Notes

This is intentionally not a decorative automation build. Provena Operators are real system functions with backend modules, testable functions, input/output contracts, runtime status, and traceable activity. OpenAI or other model calls can be added behind those functions later.

## Sprint 2 Notes

The app now treats Project Exchange as an operating system rather than separate tools. Shared EOS logic lives in `project_exchange/eos.py`; operator backends report into that layer instead of the UI inventing its own state.

Sprint 3 adds the durable OS primitives future Operators should plug into:

- `events`
- `worker_activity`
- `notifications`
- `milestones`
- `engineering_journal`
- enriched operator/runtime and component registries

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
- operator-to-operator messages in `worker_messages`
- knowledge graph relationships in `knowledge_edges`
- prompt benchmarking and A/B test records in `prompt_benchmarks`
- expanded Library search filters
- root `.env` loading through `python-dotenv`
- provider connection statuses for OpenAI, Tavily, SerpAPI, and NewsAPI without exposing secret values

Sprint 6 adds the intelligence and orchestration layer:

- `PX-H001 Head of Functions Operator` as the command planner and orchestration function
- execution plans in `execution_plans`
- PX-H001-owned jobs with dependencies, parent plan IDs, and job history
- operator memory in `worker_memory`
- routed operator communication through PX-H001 with priority, payload, and status
- persistent PX-A001 reasoning in `audit_reasoning`
- self-improvement recommendations in `system_recommendations`
- a dedicated PX-H001 Streamlit page for memory, recovery scans, plans, and recommendations

Sprint 8 turns the base runtime functions into operational Provena Operators:

- objectives in `objectives`
- recurring/manual schedules in `operating_schedules`
- daily and weekly operating briefs in `operating_briefs`
- operator load monitoring and performance snapshots in `performance_snapshots`
- richer research packages with summaries, recommended actions, history, schedule, and performance data
- audit reasoning with evidence matrix, source quality, missing evidence, bias, duplicate risk, and recommendation
- Library lineage fields for research origin, auditing, operators, source tracking, companies, industries, and opportunities
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
