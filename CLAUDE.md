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
- `apps/signalguard-web/` Next.js 15 dashboard. Server-components-first,
  typed @hey-api client generated from openapi.json, Tailwind 4 with the
  cstack design tokens. Seven screens after 5b (home, signalguard,
  coverage, findings, anomalies, anomaly drill-down, settings tabs).
  Build: `pnpm --filter signalguard-web {dev|build|test}`. Tablet
  responsive at the `md:` breakpoint (768px); component tests via
  Vitest + RTL.
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
- `packages/llm-provider/` Protocol-based provider abstraction with
  Anthropic, OpenAI, and Ollama adapters.
- `packages/llm-narrative/` finding-to-narrative pipeline with
  content-addressed prompt cache and budget tracking. The
  `prompts/` directory inside this package is curated content;
  treat with care during refactors and version prompt changes
  (`finding_narrative_v1.md`, `_v2.md`, ...).
- `packages/llm-eval/` rubric-based LLM-as-judge eval harness with
  pointwise + pairwise scoring and a hand-curated golden set in
  `data/golden_set.json`.
- `docs/` prose, sprint notes, the rules catalogue, the MLOps and
  LLM ops walkthroughs.

Note: model artefacts and the local `mlruns/` directory are gitignored; never
check them in.

- `scripts/` PowerShell app registration and cert rotation scripts.
- `infra/docker/` Docker Compose stack: per-app multi-stage Dockerfiles,
  bootstrap services that seed fixtures + audit + anomaly model into a
  named volume before the api/web pair start. See
  `infra/docker/README.md` for the build/run/reset flow.

## Conventions

- Workspace member naming: `<tool>-<role>`, e.g. `signalguard-api`, `signalguard-ml`,
  `signalguard-web`.
- Shared packages are prefixed `shared-` or named generically when the role is obvious:
  `graph-client`, `schemas`, `shared-config`.

## Design references

- `docs/DESIGN_TOKENS.md` is the single source of truth for visual decisions.
  Always reference token names, never hex literals, in component code.
- `docs/DESIGN_SYSTEM.md` describes layout patterns, component primitives, and
  per-screen blueprints. Read it before building UI work.
- `.design/` (gitignored) holds the source design pack. Sprint 5a Phase 0 may
  reference it but should not rely on it remaining in place.

## Not in scope yet

The following are deferred to dedicated sprints; do not introduce them ad hoc.

- Docker, docker-compose, deployment configurations
- Hosting, runtime, and production infrastructure decisions
- Frontend frameworks and any UI code
- Tool implementations (signalguard lands in Sprint 1; others follow)
