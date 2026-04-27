# cstack

Tooling for engineers who operate Microsoft 365 tenants programmatically.

Status: early development. Public APIs and repository structure are unstable.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Rules catalogue](docs/RULES.md)
- [Contributing](docs/CONTRIBUTING.md)
- [Sprint notes](docs/SPRINT_NOTES.md)
- [Backlog](docs/BACKLOG.md)

## Tools

- [ ] **signalguard** (in development): conditional access audit and sign-in anomaly
      detection
  - foundation: complete (fixture-driven extract pipeline working end-to-end)
  - CA audit (coverage matrix, 15 rules, exclusion hygiene): complete (against fixtures)
  - sign-in anomaly detection: planned for Sprint 3

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
