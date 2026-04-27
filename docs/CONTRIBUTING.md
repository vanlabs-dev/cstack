# Contributing

## Prerequisites

- Python 3.12 (uv downloads the interpreter on first sync)
- Node 22 LTS (manage with volta or fnm)
- pnpm 9 or newer
- Git 2.40 or newer

## Bootstrap

```sh
uv sync
pnpm install
```

## Lint and format

```sh
uv run ruff check .
uv run ruff format .
pnpm lint
pnpm format
```

CI runs the `--check` variants of both formatters.

## Commit messages

Conventional commits, lowercase subject, no trailing period, no em dashes. Allowed types:
`feat`, `fix`, `chore`, `docs`, `build`, `ci`, `refactor`, `test`, `style`.

```
feat(signalguard): add conditional access policy diff
fix(graph-client): handle 429 retry backoff
```

The `commit-msg` hook enforces these rules locally; CI re-checks on push.

## Branches

`type/short-description`, e.g. `feat/signalguard-ingest`, `fix/auth-token-refresh`.

## Pull requests

Small, single concern per PR. All checks green before review. Update docs when behavior
changes.
