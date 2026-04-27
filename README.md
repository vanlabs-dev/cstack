# cstack

Tooling for engineers who operate Microsoft 365 tenants programmatically.

Status: early development. Public APIs and repository structure are unstable.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Contributing](docs/CONTRIBUTING.md)
- [Sprint notes](docs/SPRINT_NOTES.md)
- [Backlog](docs/BACKLOG.md)

## Tools

- [ ] **signalguard** (in development): conditional access audit and sign-in anomaly
      detection
  - foundation: complete (fixture-driven extract pipeline working end-to-end)
  - audit logic: planned for Sprint 2
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

The DuckDB file lives at `data/cstack.duckdb`. Raw extracts land under
`data/raw/<tenant_id>/<yyyy-mm-dd>/`.

To register a real tenant, run `scripts/setup-app-reg.ps1` against the target tenant
(see [scripts/README.md](scripts/README.md)) and feed the output into
`uv run cstack tenant add`.
