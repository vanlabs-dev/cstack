# signalguard-api

FastAPI HTTP surface over the cstack signalguard data and audit packages. The
API is a thin reading layer plus two action endpoints; all business logic
lives in the `cstack-*` workspace packages.

## Running locally

```sh
# 1. Install workspace dependencies (Python 3.12 + uv).
uv sync --all-packages

# 2. Hydrate fixture tenants so the API has data to read.
uv run cstack fixtures load-all

# 3. Set a dev API key in .env (any string is fine).
echo 'SIGNALGUARD_API_DEV_API_KEY=dev-secret' >> .env

# 4. Start the server.
uv run signalguard-api --port 8000

# 5. OpenAPI docs render at http://localhost:8000/docs
```

The server reads `data/cstack.duckdb` and `tenants.json` from the current
working directory by default. Override via `SIGNALGUARD_API_DB_PATH` and
`SIGNALGUARD_API_TENANTS_FILE`.

## Auth model

The API accepts an `X-API-Key` header. Two key types are recognised:

- **Dev key** (`SIGNALGUARD_API_DEV_API_KEY`): a single string in `.env`.
  Authorised to call any endpoint for any tenant. Use this for local
  development, smoke tests, and the dashboard's developer mode.
- **Tenant key**: minted via `cstack tenant create-api-key <id>`. Stored as a
  SHA-256 hash in `tenants.json`, scoped to a single tenant. Plaintext keys
  are printed once at creation and never persisted.

Tenant-scoped keys can only read or trigger actions on their owning tenant;
a request to another tenant returns `403`. The dev-only `GET /tenants` route
rejects tenant keys with `403`.

```sh
# mint a key for a fixture tenant
uv run cstack tenant create-api-key tenant-b --label dashboard
# -> prints the plaintext key on stdout, the hash is appended to tenants.json
```

## Curl examples

All examples assume `KEY=dev-secret` and the server is on port 8000.

```sh
# liveness + readiness
curl http://localhost:8000/healthz
curl http://localhost:8000/readyz

# resolve the caller (useful for verifying a freshly minted key)
curl -H "X-API-Key: $KEY" http://localhost:8000/whoami

# list registered tenants (dev only)
curl -H "X-API-Key: $KEY" http://localhost:8000/tenants

# findings for a tenant, filtered to HIGH+
curl -H "X-API-Key: $KEY" \
  "http://localhost:8000/tenants/00000000-bbbb-2222-2222-222222222222/findings?min_severity=HIGH"

# trigger an audit run
curl -X POST -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"categories": ["coverage", "rules", "exclusions"]}' \
  http://localhost:8000/tenants/00000000-bbbb-2222-2222-222222222222/audit/run

# anomaly feed (top 50 above threshold)
curl -H "X-API-Key: $KEY" \
  "http://localhost:8000/tenants/00000000-aaaa-1111-1111-111111111111/anomaly-scores/feed?n=50&min_score=0.7"

# coverage matrix
curl -H "X-API-Key: $KEY" \
  http://localhost:8000/tenants/00000000-bbbb-2222-2222-222222222222/coverage-matrix

# registered models for a tenant
curl -H "X-API-Key: $KEY" \
  http://localhost:8000/tenants/00000000-aaaa-1111-1111-111111111111/models
```

## OpenAPI

The full spec is committed at `apps/signalguard-api/openapi.json` and served
live at `/docs` and `/redoc`. CI regenerates the spec on every push and
fails if it drifts from the committed copy. Regenerate locally with:

```sh
uv run python -m signalguard_api.regenerate_openapi
```

## Errors

All non-2xx responses use the RFC 7807 problem-detail shape:

```json
{
  "type": "https://signalguard.dev/errors/not-found",
  "title": "Not Found",
  "status": 404,
  "detail": "tenant 'foo' not registered",
  "correlation_id": "abc-123-...",
  "instance": "/tenants/foo"
}
```

The `correlation_id` mirrors the `X-Correlation-Id` request header (or a
generated UUID4 when absent) and appears on every log line server-side.
