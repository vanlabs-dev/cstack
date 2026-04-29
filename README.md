# cstack

Multi-tenant Microsoft 365 operations toolkit for MSP engineers. Self-hosted,
ML-augmented, open source.

cstack treats a fleet of M365 tenants the way an SRE treats a fleet of services:
audit them with rules, score their traffic with per-tenant ML models, and surface
findings with engineer-grade narratives instead of vendor portal screenshots.

<!-- screenshot pending: hero-overview.png -->

## What it does

The first tool in the toolkit, **SignalGuard**, ships two halves.

The CA audit half evaluates every tenant against a 15-rule catalogue (block legacy
auth, MFA on admins, risk-based sign-in, break-glass exclusions, and others), plus
a coverage-matrix layer that flags weak (user-segment x app-segment) cells, plus
an exclusion-hygiene analyser that catches stale, orphaned, or undocumented CA
policy exclusions. Every finding is deduplicated by content hash and persisted
to DuckDB.

The anomaly half watches Entra sign-in events. A pooled Isolation Forest per
tenant flags rows that look unlike a user's normal pattern, and SHAP attributions
explain the top three contributing features on every flagged row. MLflow tracks
every training run; a champion/challenger alias system gates promotion. The
detector targets SMB-tier tenants without Entra ID P2 licensing, where Microsoft's
Identity Protection is unavailable.

Every finding (audit or anomaly) gets a four-section LLM narrative explaining
why it fired, what it means, how to remediate, and when it might be a false
positive. Narratives are content-addressed cached so two tenants with the same
finding share a single generation. The provider layer abstracts Anthropic,
OpenAI, and local Ollama behind one Protocol; tests register fakes via the same
factory.

## Status

V0.6, fixture-driven. Six sprints complete. Live tenant integration is Sprint 7,
paused pending tenant access. Today the codebase ships:

- 266 Python tests across 8 packages and 2 apps
- 78 web tests across 28 files (Vitest + RTL, jsdom)
- 19 HTTP endpoints (15 read, 4 action), OpenAPI 3.1 contract committed
- 7 dashboard screens (Next.js 15 + Tailwind 4), tablet responsive at 768px
- 20-example hand-curated golden set + rubric-based LLM-as-judge eval harness
- $4.30 of real Anthropic API spend during Sprint 6 calibration

Everything runs against three synthetic fixture tenants. None of it has touched
a production Microsoft 365 tenant yet.

## Tools

The cstack toolkit currently ships one tool with more planned.

- **SignalGuard** identity security: CA audit + per-tenant behavioural sign-in
  anomaly detection with explainable ML scoring and LLM-narrated findings.
  Complete (against fixtures).
- *Future:* LicenseLens, Driftwatch, ChangeRadar, CompliancePulse. Planned for
  V1.

## Architecture at a glance

```
                   +----------------------- cstack monorepo -----------------------+
                   |                                                              |
fixtures load-all  |   +-- packages/ ----------------------------------+          |
or live extract -->|   | schemas, storage, graph-client, fixtures      |          |
                   |   | audit-{core,coverage,rules,exclusions}        |          |
                   |   | ml-{features,mlops,anomaly}                   |          |
                   |   | llm-{provider,narrative,eval}                 |          |
                   |   +----------------------+------------------------+          |
                   |                          |                                   |
                   |                          v                                   |
                   |   +--- DuckDB ---+   +--- mlruns ---+                        |
                   |   | tenants,     |   | per-tenant   |                        |
                   |   | ca_policies, |   | IF + SHAP    |                        |
                   |   | findings,    |   | @champion /  |                        |
                   |   | signins,     |   | @challenger  |                        |
                   |   | anomaly_     |   +--------------+                        |
                   |   | scores,      |                                           |
                   |   | narrative_   |                                           |
                   |   | cache        |                                           |
                   |   +------+-------+                                           |
                   |          |                                                   |
                   |          v                                                   |
                   |   +------+-----------------+   +----- Anthropic / OpenAI /   |
                   |   | apps/signalguard-api   |--+      Ollama (LLM provider)   |
                   |   | (FastAPI, X-API-Key)   |                                 |
                   |   +------+-----------------+                                 |
                   |          |                                                   |
                   |          v                                                   |
                   |   +------+-----------------+                                 |
                   |   | apps/signalguard-web   |                                 |
                   |   | (Next.js 15 + Tailwind)|                                 |
                   |   +------------------------+                                 |
                   |                                                              |
                   +--------------------------------------------------------------+
```

For the deeper data flow including LLM cache lookup and bias mitigation, see
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Screenshots

Eight screens captured against fixture tenants. Full reference with captions:
[docs/SCREENSHOTS.md](docs/SCREENSHOTS.md).

<!-- screenshot pending: home-overview.png -->
<!-- screenshot pending: findings-expanded.png -->
<!-- screenshot pending: coverage-matrix.png -->
<!-- screenshot pending: anomaly-drilldown.png -->

## How it's built

- **Python 3.12** via uv workspaces. 8 internal packages, 2 apps (CLI + API).
- **Next.js 15 + Tailwind 4** for the dashboard. Server Components first, TanStack
  Query for client interactions, typed `@hey-api` client generated from
  OpenAPI 3.1.
- **FastAPI + DuckDB** for the backend. Per-request DuckDB connections, RFC 7807
  problem-details on every error, correlation ids on every request and log line.
- **scikit-learn + SHAP + MLflow** for the anomaly detector. Pipeline of
  StandardScaler + IsolationForest, SHAP only on flagged rows for runtime budget,
  MLflow registry aliases for promotion gating.
- **Provider-agnostic LLM layer** with adapters for Anthropic Claude, OpenAI, and
  Ollama behind a single Protocol. Content-addressed prompt cache, budget caps,
  pointwise + pairwise eval harness with position-swap bias mitigation.

The full stack rationale lives in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Running locally

Prerequisites: Python 3.12, Node 22 LTS, uv, pnpm.

```sh
uv sync
pnpm install

uv run cstack fixtures load-all
uv run cstack audit all --tenant tenant-b --no-narratives

echo 'SIGNALGUARD_API_DEV_API_KEY=dev-secret' >> .env
uv run signalguard-api --port 8000

# In a second shell.
pnpm --filter signalguard-web dev
# Visit http://localhost:3000/dashboard, enter "dev-secret".
```

Optional: drop `--no-narratives` and add `ANTHROPIC_API_KEY=sk-ant-...` to `.env`
to generate LLM narratives during the audit. Default budget is $1 per run.

To run the anomaly detector end-to-end against fixtures:

```sh
uv run cstack signins extract --tenant tenant-a --scenario baseline
uv run cstack anomaly train --tenant tenant-a --lookback-days 365
uv run cstack anomaly promote --tenant tenant-a --force
uv run cstack signins extract --tenant tenant-a --scenario replay-attacks
uv run cstack anomaly score --tenant tenant-a
uv run cstack anomaly alerts --tenant tenant-a --n 20
```

The CLI is a thin layer over the same packages the API uses; see
[apps/cstack-cli/](apps/cstack-cli/) for the full subcommand catalogue.

## Documentation

Start at [docs/INDEX.md](docs/INDEX.md). The major docs:

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) system design, repo layout, data flow
- [API.md](docs/API.md) REST API, auth model, error format, OpenAPI pointer
- [MLOPS.md](docs/MLOPS.md) anomaly detection lifecycle, calibration results
- [LLM_OPS.md](docs/LLM_OPS.md) narrative generation and eval harness
- [DESIGN_TOKENS.md](docs/DESIGN_TOKENS.md) visual decisions, single source of truth
- [DESIGN_SYSTEM.md](docs/DESIGN_SYSTEM.md) component patterns, screen blueprints
- [RULES.md](docs/RULES.md) CA audit rule catalogue
- [SCREENSHOTS.md](docs/SCREENSHOTS.md) UI reference
- [CONTRIBUTING.md](docs/CONTRIBUTING.md) local dev, conventions
- [SPRINT_NOTES.md](docs/SPRINT_NOTES.md) per-sprint calibration outcomes
- [BACKLOG.md](docs/BACKLOG.md) parked work

## Engineering decisions worth calling out

- **Per-tenant pooled IF with planned cold-start fallback** for sub-P2 tenants.
  Per-user models would be more sensitive but cold-start a new user every join.
  Sprint 3.5 will layer per-user models with a pooled fallback for users below
  the sample threshold.
- **Content-addressed prompt cache** for cross-tenant narrative reuse. Cache
  key is `SHA-256(rule_id, canonicalised(evidence), prompt_version, model)`,
  excluding tenant id; identical findings across tenants share one generation.
- **Custom LLM provider abstraction (not LiteLLM).** One Protocol, three
  adapters, ~250 lines. LiteLLM ships its own opinions about retries and
  observability that conflict with ours; owning the abstraction means we can
  ship adapter-level fixes immediately (Claude 4.7 deprecating `temperature`
  mid-sprint was a real test of this).
- **Pairwise LLM-as-judge eval harness with bias mitigation.** Different judge
  model from generator (sonnet judges opus output), position-swap on every
  pairwise comparison with the result downgraded to tie when the judge flips
  on swap, low-temperature judging. Pointwise scoring alone misled us in
  Sprint 6 calibration; the pairwise check caught it.
- **OpenAPI-first contract.** The web client is generated from
  `apps/signalguard-api/openapi.json` and CI fails on drift. The web app cannot
  ship a request shape the backend does not support.

## License

[MIT](LICENSE).

## Contributing

cstack is a personal portfolio project that welcomes external contribution. See
[docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for the local dev workflow,
conventional-commit rules, and the project's hard rules on code style and tone.
