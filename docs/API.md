# signalguard-api

> See [docs/INDEX.md](./INDEX.md) for the full documentation map.

## Overview

The API is a thin HTTP layer over the cstack data and audit packages. Routers
parse input, call into existing packages via per-request DuckDB connections,
and shape the result. There is no domain logic in the API beyond formatting.

## Auth model

Two API key types are recognised, both via the `X-API-Key` header.

- **Dev key**: configured via `SIGNALGUARD_API_DEV_API_KEY` in `.env`. A
  single string. Authorised to call any endpoint for any tenant. Suitable
  for local development and the dashboard's developer mode.
- **Tenant key**: minted with `cstack tenant create-api-key <tenant-id>`.
  Stored as a SHA-256 hex digest in `tenants.json` under the tenant's
  `api_keys` array. Plaintext is printed once at mint time and never
  persisted. A tenant key can only access routes scoped to its owning
  tenant; cross-tenant access returns `403`.

### Issuing a tenant key

```sh
uv run cstack tenant create-api-key tenant-b --label dashboard
# stdout: <random-32-byte-url-safe-string>
# stderr: saved hash for label='dashboard' on tenant tenant-b; not shown again
```

The plaintext is the only output you can hand to a downstream client. Lose
it and you must mint a fresh one; re-running the command produces a new
key, leaving the old hash in place until you remove it.

### Rotation

To rotate, mint a new key, distribute it, then strip the old hash from
`tenants.json` by hand. There is no automatic revoke API in V1; the
threat model assumes the file is the source of truth and rotation is a
deliberate manual operation.

### Why not OAuth or JWT

V2 work. The current model is the smallest thing that supports the dual
local-dev + per-tenant-scoped scenario without standing up an identity
provider. The `Authorization: Bearer <jwt>` route is reserved for the V2
upgrade and does not collide with `X-API-Key`.

## Endpoint catalogue

| Method | Path                                                | Auth                       | Summary                                     |
| ------ | --------------------------------------------------- | -------------------------- | ------------------------------------------- |
| GET    | `/healthz`                                          | none                       | Liveness probe.                             |
| GET    | `/readyz`                                           | none                       | Readiness probe (opens a DB connection).    |
| GET    | `/whoami`                                           | any key                    | Identity of the caller.                     |
| GET    | `/tenants`                                          | dev only                   | List registered tenants.                    |
| GET    | `/tenants/{tenant_id}`                              | dev or matching tenant key | Tenant detail.                              |
| GET    | `/tenants/{tenant_id}/findings`                     | dev or matching tenant key | Filterable, paginated findings.             |
| GET    | `/tenants/{tenant_id}/findings/summary`             | dev or matching tenant key | Counts by category, severity, rule.         |
| GET    | `/tenants/{tenant_id}/findings/{finding_id}`        | dev or matching tenant key | Single finding.                             |
| GET    | `/tenants/{tenant_id}/anomaly-scores`               | dev or matching tenant key | Filterable, paginated scores.               |
| GET    | `/tenants/{tenant_id}/anomaly-scores/feed`          | dev or matching tenant key | Top anomalies above threshold.              |
| GET    | `/tenants/{tenant_id}/anomaly-scores/{signin_id}`   | dev or matching tenant key | Score + linked sign-in + linked finding.    |
| GET    | `/tenants/{tenant_id}/coverage-matrix`              | dev or matching tenant key | Recomputed coverage matrix.                 |
| GET    | `/tenants/{tenant_id}/signins/stats`                | dev or matching tenant key | Tenant-wide sign-in aggregates.             |
| GET    | `/tenants/{tenant_id}/users/{user_id}/signins`      | dev or matching tenant key | Per-user sign-in history.                   |
| POST   | `/tenants/{tenant_id}/audit/run`                    | dev or matching tenant key | Execute audit categories, persist findings. |
| POST   | `/tenants/{tenant_id}/audit/dry-run`                | dev or matching tenant key | Compute findings without persisting.        |
| POST   | `/tenants/{tenant_id}/anomaly/score`                | dev or matching tenant key | Score sign-ins; 503 if no model registered. |
| GET    | `/tenants/{tenant_id}/models`                       | dev or matching tenant key | Registered models with alias state.         |
| GET    | `/tenants/{tenant_id}/models/{model_name}/versions` | dev or matching tenant key | All versions of a model.                    |

## Errors

Every non-2xx response is RFC 7807 JSON with content type
`application/problem+json`:

```json
{
  "type": "https://signalguard.dev/errors/not-found",
  "title": "Not Found",
  "status": 404,
  "detail": "tenant 'foo' not registered",
  "correlation_id": "9b6f5e44-3bd4-4f8a-8c2d-6f8e7d4f9b25",
  "instance": "/tenants/foo"
}
```

`type` is a stable URN-style slug per error category; `correlation_id`
mirrors the `X-Correlation-Id` request header (auto-generated when not
supplied) and appears on every server-side log line; `instance` is the
request path. There is no `errors[]` array; nested validation errors are
serialised into `detail` for now.

## Pagination

List endpoints accept `limit` (default 100, max 500) and `offset`
(default 0) query parameters. Responses use a `Paginated[T]` envelope:

```json
{
  "items": [...],
  "total": 1234,
  "limit": 100,
  "offset": 0,
  "has_more": true
}
```

`total` is the count ignoring limit/offset; `has_more` is server-computed
so clients do not have to compare offsets themselves.

## Versioning

V1 is unversioned at the URL level. Breaking changes will introduce a
`/v2/` prefix; the existing `/tenants/...` routes remain on the V1
contract until a deprecation cycle ends. Additive changes (new optional
fields, new endpoints) do not bump the version.

## Correlation ids and logging

Every request reads or generates an `X-Correlation-Id`. The id is:

- echoed on the response header
- attached to every log record under `correlation_id`
- included in every error body's `correlation_id` field

Use it to grep server logs for the trail of a single request. Sensitive
headers (`Authorization`, `X-API-Key`) are scrubbed by a logging filter
before any record is emitted.

## OpenAPI

The full machine-readable spec is committed at
`apps/signalguard-api/openapi.json`. Regenerate with:

```sh
uv run python -m signalguard_api.regenerate_openapi
```

CI re-runs this on every push and fails on a non-empty diff.
