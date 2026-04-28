# Architecture

## Overview

cstack is a polyglot monorepo for building Microsoft 365 operations tooling. Tools share
a common Graph client, schema definitions, and lint and format infrastructure; each tool
runs as an independent service or library.

## Repo layout

- `apps/cstack-cli/` Click-based CLI exposing tenant, extract, fixtures, audit,
  signins, and anomaly subcommands.
- `apps/signalguard-api/` FastAPI HTTP surface over the same packages the CLI
  consumes. Read endpoints (tenants, findings, anomaly scores, coverage,
  sign-ins, models) plus two action endpoints (audit run, anomaly score).
- `apps/signalguard-web/` Next.js 15 dashboard that consumes the API via a
  typed client generated from `apps/signalguard-api/openapi.json`. Three
  core screens in 5a (home, findings list with inline expansion, sign-in
  anomaly drill-down); five more screens land in 5b. Design tokens live in
  `docs/DESIGN_TOKENS.md`; component patterns in `docs/DESIGN_SYSTEM.md`.
- `packages/schemas/` Pydantic v2 models for tenants, conditional access policies,
  named locations, and directory objects.
- `packages/storage/` DuckDB connection management, SQL migrations, raw and normalised
  layer helpers, plus the `findings` table.
- `packages/graph-client/` Typed wrapper around `msgraph-sdk` with certificate auth and
  pagination.
- `packages/fixtures/` Synthetic Graph corpus (three tenants) plus a loader that
  hydrates DuckDB exactly as the live extractor would. `metadata.json` carries the
  calibrated audit expectations the integration tests assert against.
- `packages/audit-core/` Shared finding model, severity ordering, finding storage.
- `packages/audit-coverage/` Coverage matrix: user segments, app segments, weak-cell
  finding generation.
- `packages/audit-rules/` Rule registry and 15 best-practice CA evaluators. Each rule
  is a pure function plus its metadata; the package `__init__` populates a global
  `RULE_REGISTRY` on import.
- `packages/audit-exclusions/` Exclusion hygiene analyser (stale, orphan,
  admin-MFA-bypass, creep, undocumented).
- `packages/ml-features/` Feature engineering pipeline for sign-in events:
  `UserHistory` rolling state, per-feature extractors, and the canonical
  `FEATURE_COLUMNS` contract.
- `packages/ml-mlops/` MLflow tracking helpers, registry alias API
  (`@champion`/`@challenger`), drift PSI, and shadow-scoring framework.
- `packages/ml-anomaly/` Per-tenant pooled IsolationForest training,
  scoring with SHAP attributions, anomaly Finding generation, promotion
  gating.
- `docs/` prose, sprint notes, the rules catalogue, and the MLOps
  walkthrough.
- `scripts/` PowerShell app registration and certificate rotation scripts (run by
  tenant admins, not invoked from cstack itself).
- `infra/` deployment artifacts (TBD).

## Runtime stack

Python 3.12 via uv workspace on the audit, ingest, and storage side. Node 22 LTS via
pnpm workspace reserved for future API and frontend work. Both lockfiles are committed.
DuckDB persists tenant data to a single file (`data/cstack.duckdb` by default).

## Data flow

```
fixtures load-all                   live extract
        |                                |
        v                                v
+-------------------+         +---------------------+
| bundled corpus    |         | Microsoft Graph     |
| packages/fixtures |         | (cert-auth)         |
+---------+---------+         +----------+----------+
          \                              /
           \                            /
            v                          v
         +-------- raw_ingestions --------+
         | data/raw/<tenant>/<date>/*.json|
         +----------------+---------------+
                          |
                          v
         +----------- normalised tables -----------+
         | tenants, ca_policies, named_locations,  |
         | users, groups, directory_roles,         |
         | role_assignments                        |
         +-----------------+------------------------+
                           |
                           v
            +--------------------------------+
            |   load_context_from_db         |
            |   (audit-rules.context)        |
            +---------------+----------------+
                            |
              +-------------+-------------+
              v             v             v
         +---------+   +---------+   +-------------+
         | audit-  |   | audit-  |   |  audit-     |
         | coverage|   |  rules  |   |  exclusions |
         +----+----+   +----+----+   +------+------+
              \             |               /
               \            |              /
                v           v             v
              +------ findings table ------+
              | (immutable rows; dedupe by |
              |  Finding.compute_id)       |
              +-----------+----------------+
                          |
                          v
                (Sprint 6 LLM narration)
```

Both code paths share the same downstream tables. The audit modules read an
`AuditContext` (policies + directory + locations + as_of) and emit `Finding`
records the storage layer dedupes by id.

## API service

```
HTTP client (curl, dashboard, scripts)
        |
        v
+--------------------------+
| signalguard-api          |
| - X-API-Key auth         |
| - per-request DuckDB     |
| - asyncio.to_thread for  |
|   blocking storage calls |
+-----------+--------------+
            |
            v
   data/cstack.duckdb        mlruns/  (MLflow file backend)
            |                    |
            v                    v
+----------- existing cstack-* packages -----------+
| audit-core   audit-coverage   audit-rules        |
| audit-exclusions  ml-anomaly  ml-mlops  storage  |
+--------------------------------------------------+
```

The API never duplicates business logic; routers parse input, dispatch into
the package functions the CLI already calls, and shape the response.

## Web dashboard

```
Browser
  |
  v
+---------------------------+
| signalguard-web (Next 15) |
| - Server Components hit   |
|   the API via the typed   |
|   @hey-api client         |
| - Client Components for   |
|   filter chips, tables,   |
|   and recharts            |
| - X-API-Key cookie shared |
|   between server + client |
+-------------+-------------+
              |
              v
         FastAPI :8000  ->  DuckDB
```

The committed design reference is `docs/DESIGN_TOKENS.md` plus
`docs/DESIGN_SYSTEM.md`. The `.design/` source folder is gitignored and is
not required for the build.

## Adding a new rule

1. Drop a module under `packages/audit-rules/src/cstack_audit_rules/rules/`.
2. Define a `RuleMetadata` constant and a pure `_evaluate(context)` function.
3. Bind both into a module-level `RULE` and call `register_rule(RULE)`.
4. Add the import to `rules/__init__.py` so the registry picks it up.
5. Add a unit test under `packages/audit-rules/tests/rules/`.
6. Re-run `cstack audit all --tenant <fixture>` and update each fixture's
   `metadata.json` `expected_findings` block; the integration tests pull
   counts from there.

## Deployment model

TBD. Sprint 2 ships a local CLI that operates against a DuckDB file. Container,
runtime, and hosting decisions are deferred to a deployment sprint.
