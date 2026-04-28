# CLAUDE.md

## Project

cstack is an open-source monorepo of tools that help engineers operate Microsoft 365
tenants programmatically (Microsoft Graph plus ML where useful). The first tool is
signalguard, a conditional access audit and sign-in anomaly detector. Other tools
follow in their own sprints.

## Hard rules

These rules apply to every file Claude (or any contributor) creates or edits.

- No em dashes anywhere (U+2014). Not in code, not in comments, not in docs, not in
  strings, not in commit messages. Use a comma, period, semicolon, parentheses, or
  restructure the sentence.
- Comments explain why, not what. No filler comments. Only comment when the reason for
  the code is non-obvious. Self-documenting code is the default.
- No AI tells in any prose. No "Let's", no "We'll", no "Here we", no "I've created", no
  excited tone, no emoji unless explicitly requested, no marketing language, no
  "comprehensive", "robust", or "powerful" adjectives, no "feel free to". Sound like a
  senior developer wrote a tight internal doc.
- Sentence case for all headings, not Title Case. Match modern OSS style.
- Lines under 100 characters for code, under 120 for prose docs.
- Atomic, frequent commits using conventional commits. Lowercase subject, no trailing
  period, no em dashes. Format: `type(scope): subject`. Allowed types: `feat`, `fix`,
  `chore`, `docs`, `build`, `ci`, `refactor`, `test`, `style`. Subject is imperative
  mood. Scope is optional.
- Do not invent features. Build only what the active sprint specifies. Park missing
  items in `docs/BACKLOG.md`.

## Pointers

- Architecture: `docs/ARCHITECTURE.md`
- Contribution flow: `docs/CONTRIBUTING.md`
- Parked work: `docs/BACKLOG.md`

## Repo layout

- `apps/cstack-cli/` Click CLI exposing tenant, extract, fixtures, audit, signins,
  and anomaly subcommands.
- `apps/signalguard-api/` FastAPI HTTP surface over the same packages.
  Read endpoints, two action endpoints, OpenAPI 3.1, dual-key auth.
- `packages/schemas/` pydantic models for tenants, CA policies, named locations,
  directory objects.
- `packages/storage/` DuckDB connection, migrations, and per-resource upsert helpers,
  plus the `findings` table.
- `packages/graph-client/` typed `msgraph-sdk` wrapper with certificate auth and
  paginated fetchers.
- `packages/fixtures/` synthetic Graph corpus plus a loader that hydrates DuckDB the
  same way live extraction would; `metadata.json` carries calibrated audit expectations.
- `packages/audit-core/` shared finding model, severity, and finding storage.
- `packages/audit-coverage/` user/app segment matrix and weak-cell finding generator.
- `packages/audit-rules/` rule registry and 15 best-practice CA evaluators.
- `packages/audit-exclusions/` exclusion hygiene analyser.
- `packages/ml-features/` feature engineering pipeline for sign-in events.
- `packages/ml-mlops/` MLflow tracking, registry aliases, drift PSI, shadow scoring.
- `packages/ml-anomaly/` per-tenant Isolation Forest training + SHAP scoring.
- `docs/` prose, sprint notes, the rules catalogue, and the MLOps walkthrough.

Note: model artefacts and the local `mlruns/` directory are gitignored; never
check them in.

- `scripts/` PowerShell app registration and cert rotation scripts.
- `infra/` deployment artifacts (TBD).

## Conventions

- Workspace member naming: `<tool>-<role>`, e.g. `signalguard-api`, `signalguard-ml`,
  `signalguard-web`.
- Shared packages are prefixed `shared-` or named generically when the role is obvious:
  `graph-client`, `schemas`, `shared-config`.

## Not in scope yet

The following are deferred to dedicated sprints; do not introduce them ad hoc.

- Docker, docker-compose, deployment configurations
- Hosting, runtime, and production infrastructure decisions
- Frontend frameworks and any UI code
- Tool implementations (signalguard lands in Sprint 1; others follow)
