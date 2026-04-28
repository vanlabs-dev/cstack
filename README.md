# cstack

Tooling for engineers who operate Microsoft 365 tenants programmatically.

Status: early development. Public APIs and repository structure are unstable.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [API reference](docs/API.md)
- [MLOps walkthrough](docs/MLOPS.md)
- [Rules catalogue](docs/RULES.md)
- [Contributing](docs/CONTRIBUTING.md)
- [Sprint notes](docs/SPRINT_NOTES.md)
- [Backlog](docs/BACKLOG.md)

## Tools

- [ ] **signalguard** (in development): conditional access audit and sign-in anomaly
      detection
  - foundation: complete (fixture-driven extract pipeline working end-to-end)
  - CA audit (coverage matrix, 15 rules, exclusion hygiene): complete (against fixtures)
  - sign-in anomaly detection (Isolation Forest + SHAP + MLflow): pipeline complete
    (against fixtures); recall calibration ongoing, see [MLOPS.md](docs/MLOPS.md)
  - HTTP API (read + action endpoints, OpenAPI 3.1): complete; see
    [apps/signalguard-api/README.md](apps/signalguard-api/README.md)
  - web dashboard (3 core screens against fixture data): 5a complete; see
    [apps/signalguard-web/README.md](apps/signalguard-web/README.md)

## Running locally

cstack works without a real tenant via a synthetic fixture corpus. Three sample
tenants exercise the same code path the live extractor uses.

```sh
# 1. Install dependencies (Python 3.12 + Node 22 LTS).
uv sync
pnpm install

# 2. Load the bundled fixtures into DuckDB.
uv run cstack fixtures load-all

# 3. Inspect what is registered.
uv run cstack tenant list

# 4. Extract a fixture tenant end-to-end (writes raw JSON + normalised rows).
uv run cstack extract ca-policies --tenant tenant-a
uv run cstack extract all --tenant tenant-b
```

### Running anomaly detection

```sh
uv run cstack signins extract --tenant tenant-a --scenario baseline
uv run cstack anomaly train --tenant tenant-a --lookback-days 365
uv run cstack anomaly promote --tenant tenant-a --force
uv run cstack signins extract --tenant tenant-a --scenario replay-attacks
uv run cstack anomaly score --tenant tenant-a
uv run cstack anomaly alerts --tenant tenant-a --n 20
uv run cstack anomaly mlflow-ui
```

The model is a pooled per-tenant Isolation Forest with SHAP top-3 attributions
on every flagged sign-in. MLflow tracks every run; aliases `@champion` and
`@challenger` gate promotion. See [MLOPS.md](docs/MLOPS.md) for the full
lifecycle.

### Starting the API

```sh
echo 'SIGNALGUARD_API_DEV_API_KEY=dev-secret' >> .env
uv run signalguard-api --port 8000
# OpenAPI UI: http://localhost:8000/docs
```

See [apps/signalguard-api/README.md](apps/signalguard-api/README.md) for the
auth model and curl examples.

### Starting the web dashboard

```sh
# After the API is running on :8000.
pnpm --filter signalguard-web dev
# Visit http://localhost:3000/dashboard, enter the dev API key.
```

See [apps/signalguard-web/README.md](apps/signalguard-web/README.md) for the
route catalogue and dev workflow.

### Running an audit

```sh
uv run cstack fixtures load-all
uv run cstack audit all --tenant tenant-b
uv run cstack audit findings --tenant tenant-b --min-severity HIGH
uv run cstack audit list-rules
```

`audit all` runs the coverage matrix, all registered best-practice rules, and the
exclusion hygiene analyser, persisting findings to the `findings` table. Subsequent
runs are deduplicated by `Finding.compute_id`. `audit findings --json` produces
machine-readable output for downstream tooling.

The DuckDB file lives at `data/cstack.duckdb`. Raw extracts land under
`data/raw/<tenant_id>/<yyyy-mm-dd>/`.

To register a real tenant, run `scripts/setup-app-reg.ps1` against the target tenant
(see [scripts/README.md](scripts/README.md)) and feed the output into
`uv run cstack tenant add`.
