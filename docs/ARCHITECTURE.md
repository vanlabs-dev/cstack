# Architecture

## Overview

cstack is a polyglot monorepo for building Microsoft 365 operations tooling. Tools share
a common Graph client, schema definitions, and lint and format infrastructure; each tool
runs as an independent service or library.

## Repo layout

- `apps/` runnable services and entry points
- `packages/` libraries shared across tools (Graph client, schemas, utilities)
- `docs/` prose
- `scripts/` operational scripts
- `infra/` deployment artifacts (TBD)

## Runtime stack

Python 3.12 on the audit, ingest, and ML side, managed as a uv workspace. Node 22 LTS on
the API and frontend side, managed as a pnpm workspace. Both lockfiles are committed.

## Data flow

Each tool reads signals from Microsoft Graph and adjacent tenant APIs, normalizes them
into shared schemas, and persists output to per-tool stores. Cross-tool sharing flows
through the schema package, not direct coupling.

## Deployment model

TBD. Sprint 0 ships local tooling only. Container, runtime, and hosting decisions are
deferred to a deployment sprint.
