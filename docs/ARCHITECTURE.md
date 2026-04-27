# Architecture

## Overview

cstack is a polyglot monorepo for building Microsoft 365 operations tooling. Tools share
a common Graph client, schema definitions, and lint and format infrastructure; each tool
runs as an independent service or library.

## Repo layout

- `apps/cstack-cli/` Click-based CLI exposing tenant, extract, and fixtures subcommands.
- `packages/schemas/` Pydantic v2 models for tenants, conditional access policies,
  named locations, and directory objects.
- `packages/storage/` DuckDB connection management, SQL migrations, raw and normalised
  layer helpers.
- `packages/graph-client/` Typed wrapper around `msgraph-sdk` with certificate auth and
  pagination.
- `packages/fixtures/` Synthetic Graph corpus (three tenants) plus a loader that
  hydrates DuckDB exactly as the live extractor would.
- `docs/` prose and sprint notes.
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
          \\                              /
           \\                            /
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
                  (Sprint 2 audit logic)
```

Both code paths share the same downstream tables. Sprint 2's audit rules consume
`ca_policies` plus the directory tables via tenant-scoped queries.

## Deployment model

TBD. Sprint 1 ships a local CLI that operates against a DuckDB file. Container,
runtime, and hosting decisions are deferred to a deployment sprint.
