# Provena Foundry

Provena Foundry is a professional software product governed by a formal Review Board methodology that gates all protected-branch merges, milestone completions, and production deployments.

## Run & Operate

- `pnpm --filter @workspace/api-server run dev` — run the API server (port 5000)
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required env: `DATABASE_URL` — Postgres connection string

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- API: Express 5
- DB: PostgreSQL + Drizzle ORM
- Validation: Zod (`zod/v4`), `drizzle-zod`
- API codegen: Orval (from OpenAPI spec)
- Build: esbuild (CJS bundle)

## Where things live

- `docs/review-board/` — Review Board methodology package (governing doc + 8 reviewer specs)
- `docs/review-board/REVIEW-BOARD-METHODOLOGY.md` — Master governing methodology (RBM-001)
- `docs/review-board/specs/` — Individual reviewer specifications (RBS-001 through RBS-008)
- `docs/review-board/README.md` — Package index, execution sequence, and orchestration contracts

## Architecture decisions

- Review Board methodology is kept entirely separate from GS-P001 governance — no shared documents.
- All Board decisions are deterministic from the finding set; no override by schedule or commercial pressure is permitted.
- Reviewer specifications each include a `Reviewer Prompt Conversion Notes` section as the contract for converting specs into AI reviewer prompts.
- The Sceptical Reviewer (RBS-008) is sequenced in Phase 2 (after all specialist reviews) by design — it reviews the reviews, not the artefact directly.

## Product

Provena Foundry. Application functionality to be defined as the product is built.

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

_Populate as you build — sharp edges, "always run X before Y" rules._

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
