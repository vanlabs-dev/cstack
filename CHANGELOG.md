# Changelog

All notable changes to cstack are documented in this file. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning is SemVer pre-release until V1, which is gated on live-tenant
validation.

## [Unreleased]

### Sprint 3.5b: Restore Sprint 3 calibration as default; gate per-user behind flags

- **`CSTACK_ML_TRAINING_TOPOLOGY`** (default `pooled`) selects between
  Sprint 3's pooled IF and Sprint 3.5's per-user-with-cold-start
  topology. Both emit the same `PerUserBundle` shape so scoring code
  is topology-agnostic. `--topology` CLI flag overrides per-invocation.
- **`CSTACK_ML_OFF_HOURS_ADMIN_ENABLED`** (default off) gates the
  off-hours-admin rule. The four Sprint 3 hybrid rules keep firing.
- **Restored calibration** at HEAD: recall 0.889-0.926 on every
  attack scenario (above the 0.80 floor everywhere, including
  tenant-c noisy that Sprint 3.5 dropped to 0.741). Precision
  0.245-0.275, F1 0.382-0.424. Numbers track Sprint 3 metadata
  closely; small deltas reflect sklearn/numpy version drift.
- **Gate verified**: `tenant-a/replay-attacks` with both flags
  activated reproduces Sprint 3.5 metrics exactly
  (P/R/F1/FPR = 0.209/0.852/0.336/0.025).
- **MLflow run topology tag** records which topology produced each
  registered model version.

### Sprint 3.5: Per-user anomaly tier + off-hours admin (gated by 3.5b)

- **Per-user IsolationForest bundle** opt-in via
  `CSTACK_ML_TRAINING_TOPOLOGY=per_user`. One fitted pipeline per
  user with at least 30 sign-ins, cold-start pooled fallback for the
  long tail, all packaged as a single `model.joblib` registered under
  `signalguard-anomaly-{tenant_id}` (no more `-pooled-` suffix).
- **`AnomalyScore.model_tier`** field plus migration 11 surfaces
  which tier (`per_user` / `cold_start_pooled` / `rule_only`) scored
  each row.
- **Off-hours-admin rule** opt-in via
  `CSTACK_ML_OFF_HOURS_ADMIN_ENABLED=true`. Fires on tier-0 admin
  sign-ins that the user's per-user time-only model rates in their
  own training-distribution top decile (cold-start admins fall back
  to a UTC 22:00-06:00 night band).
- **`anomaly train --skip-if-registered`** for fast Compose warm-ups
  when a champion already exists.
- **MLflow `artifact_location`** resolved at `configure_tracking`
  time from explicit arg / `MLFLOW_ARTIFACT_ROOT` env / sqlite
  sibling. Removes the `working_dir: /data` Compose hack; bootstrap
  services keep cwd at `/app` regardless.

## [0.6.0-alpha.1] - 2026-04-30

First tagged baseline. Six sprints of work plus a polish and
containerisation pass: the full SignalGuard tool runs against synthetic
fixtures, and the Docker Compose stack brings the whole environment up
in one command.

### Sprint 0 to 1: Foundation

- Monorepo with uv + pnpm workspaces.
- Pydantic v2 schemas for tenants, conditional access policies,
  sign-ins, named locations, directory objects.
- DuckDB storage layer with content-hashed dedup.
- msgraph-sdk wrapped graph client (certificate auth).
- Three calibrated synthetic fixture tenants (tenant-a/b/c).

### Sprint 2: CA audit

- 15-rule registry covering MFA, legacy auth, risk-based,
  break-glass, device compliance, guest restrictions, workload
  identity, and policy hygiene categories.
- Coverage matrix computation across 5 user segments x 5 app
  segments.
- Exclusion hygiene analyser (stale, orphan, admin-MFA-bypass,
  creep, undocumented).

### Sprint 3: Anomaly detection

- Per-tenant pooled IsolationForest with rule-based score booster.
- SHAP top-3 attributions on every flagged sign-in.
- MLflow model registry with `champion` and `challenger` aliases.
- PSI drift monitoring and shadow scoring framework.
- Calibrated against three scenarios (baseline, replay-attacks,
  noisy) on all three fixture tenants. Recall 0.81 to 0.93 on
  attacks; precision 0.24 to 0.30.

### Sprint 4: API

- 19 endpoints across health, whoami, tenants, findings, anomaly,
  coverage, signins, audit, models, narratives.
- Dual auth model: dev key + per-tenant API keys (SHA-256 hashed in
  tenants.json).
- RFC 7807 problem-detail error format on every non-2xx.
- Correlation-id middleware threaded through to every log line.
- OpenAPI 3.1 with CI-enforced contract drift detection.

### Sprint 5a to 5b: Frontend

- Next.js 15 + Tailwind 4 dashboard. Server Components first,
  TanStack Query for client interactions.
- Seven shipped screens: home, signalguard overview, coverage
  matrix, findings, anomaly feed, anomaly drill-down, settings tabs.
- 78 component tests (Vitest + RTL + jsdom) across 28 files.
- Tablet responsive at 768px; phone breakpoints parked.
- Typed client (via `hey-api/openapi-ts`) generated from openapi.json with CI drift
  detection.

### Sprint 6: LLM narrative layer

- Provider-agnostic abstraction (Anthropic, OpenAI, Ollama) behind a
  single Protocol. Three adapters; tests register fakes via the same
  factory.
- Content-addressed prompt cache for cross-tenant narrative reuse.
- Rubric-based eval harness with pointwise + pairwise scoring,
  position-swap bias mitigation, and a 20-example hand-curated
  golden set sourced from real fixture findings.
- Live calibration against the Anthropic API: prompt v1 stayed
  default after pairwise judge picked it 14-0-6 over v2 despite v2's
  higher pointwise score (the documented "pointwise can mislead"
  outcome).

### Sprint 6.5: Polish

- README rewrite as portfolio-grade entry point.
- docs/INDEX.md, cross-linking across all major docs.
- Eight UI screenshots committed (six captured; two pending).
- Public-package docstring backfill, terminology consistency, dead
  code removal, SECURITY.md.

### Sprint 6.6: Containerisation (this release)

- Multi-stage Dockerfiles for `signalguard-api` (uv-based, 2.1 GB)
  and `signalguard-web` (Next.js standalone, 434 MB). Both run as
  non-root cstack:cstack uid 1001.
- Docker Compose stack at `infra/docker/compose.yaml` with
  bootstrap services (fixtures load, audit run, anomaly train +
  promote + score) chained via `service_completed_successfully`.
- MLflow tracking backend defaults to SQLite for multi-process
  safety under bind mounts. File:// remains available for tests.
- Next.js standalone output gated on `BUILD_STANDALONE=true` so
  Linux container builds use it while Windows local builds keep the
  default-off behaviour.
- Verified end-to-end against all three fixture tenants. Cold-up
  ~90s; warm-up ~110s (anomaly bootstrap retrains every up; tracked
  in BACKLOG).

### Known limitations

- No live-tenant validation; everything runs against synthetic
  fixtures. Sprint 7 closes that gap.
- Anomaly precision 0.24 to 0.30, recall 0.81 to 0.93. Sprint 3.5's
  per-user IF lift targets the precision number.
- Pooled IF only; per-user models are next sprint.
- Mobile breakpoints below 768px are functionally rendered but not
  visually audited.
- LLM narratives default off in the Compose stack to avoid spending
  on every up; flip `CSTACK_LLM_NARRATIVE_ENABLED=true` to opt in.

[0.6.0-alpha.1]: https://github.com/codeblue/cstack/releases/tag/v0.6.0-alpha.1
