# cstack docker stack

> See [docs/INDEX.md](../../docs/INDEX.md) for the full documentation map.

The fastest way to run cstack locally. One `docker compose up` brings up
the API, the dashboard, and a populated DuckDB seeded from the bundled
fixture tenants.

## What runs

Six services, three of them one-shot bootstrap, one long-running
support container, and the api/web pair.

- `cstack-fixtures` loads tenant-a, tenant-b, tenant-c fixtures into
  `/data/cstack.duckdb`.
- `cstack-audit` runs the full audit (coverage, rules, exclusions) on
  every tenant with narratives disabled.
- `cstack-anomaly-bootstrap` extracts replay-attack sign-ins for
  tenant-a, trains the IF model, promotes it, and scores the corpus.
- `cstack-api` (FastAPI) on port 8000.
- `cstack-web` (Next.js standalone) on port 3000.
- `cstack-geoipupdate` (long-running) refreshes the MaxMind
  GeoLite2-ASN database weekly. Optional; needs `MAXMIND_ACCOUNT_ID`
  and `MAXMIND_LICENSE_KEY` set or the container exits early. See
  the GeoIP database section below.

The bootstrap services run sequentially via `depends_on:
service_completed_successfully` and the api waits for them via
`service_healthy`. First up takes about 60 to 90 seconds; subsequent
ups skip most work because the volume already has data.

## Build and run

From the repo root:

```sh
docker compose -f infra/docker/compose.yaml build
docker compose -f infra/docker/compose.yaml up
```

Then visit `http://localhost:3000`. When the API key gate prompts, enter
the value of `SIGNALGUARD_API_DEV_API_KEY` (default `dev-secret`).

## Fixtures-only override

To skip the anomaly bootstrap (saves ~30 seconds; useful when you only
need the audit findings to render):

```sh
docker compose \
  -f infra/docker/compose.yaml \
  -f infra/docker/compose.fixtures-only.yaml \
  up
```

## Reset

To wipe the DuckDB and MLflow state and start over:

```sh
docker compose -f infra/docker/compose.yaml down -v
```

`-v` removes the `cstack-data` named volume; without it the next `up`
reuses the existing data.

## Configuration

Copy `.env.example` to `.env` (in this directory or the repo root) and
edit. The key knobs:

| variable                       | default      | purpose                                         |
| ------------------------------ | ------------ | ----------------------------------------------- |
| `SIGNALGUARD_API_DEV_API_KEY`  | `dev-secret` | The dashboard API key gate accepts this value.  |
| `ANTHROPIC_API_KEY`            | (unset)      | LLM provider key for narratives.                |
| `OPENAI_API_KEY`               | (unset)      | Alternative LLM provider.                       |
| `CSTACK_LLM_NARRATIVE_ENABLED` | `false`      | Flip true to generate narratives during audits. |
| `MAXMIND_ACCOUNT_ID`           | (unset)      | GeoLite2 account id; geoipupdate runs when set. |
| `MAXMIND_LICENSE_KEY`          | (unset)      | GeoLite2 license key (paired with account id).  |

LLM keys are passthrough only; never bake them into the image. Build args
are reserved for non-sensitive values.

## Troubleshooting

- **Port conflict on 8000 or 3000**: stop the conflicting container with
  `docker stop <id>` or change the host port mapping in `compose.yaml`.
- **Stale image after a code change**: rebuild with
  `docker compose -f infra/docker/compose.yaml build --no-cache <service>`
  (or just `build` to rebuild only what changed).
- **Bootstrap services hang**: inspect with
  `docker compose -f infra/docker/compose.yaml logs <service-name>`.
  Any non-zero exit from a bootstrap service blocks the api from
  starting via `service_completed_successfully`.
- **API connectivity from web**: the web container's
  `NEXT_PUBLIC_API_BASE_URL` is `http://localhost:8000`. The browser
  reaches the API via the host port mapping; server components run
  inside the container and could reach `http://api:8000`. Both work
  because the host port and the in-network port are both 8000.
- **DuckDB write conflicts**: only one process can write at a time.
  Stopping `cstack-api` and running a CLI command via
  `docker run --rm --volumes-from cstack-api cstack-api:dev python -m cstack_cli.main ...`
  is the safest pattern; do not run a CLI subcommand while the api is up.

## GeoIP database

ASN feature extraction uses a MaxMind GeoLite2-ASN database when the
geoipupdate container has populated one. Setup, in three short steps:

1. Sign up free at <https://www.maxmind.com/en/geolite2/signup>. The
   form asks for name, email, and intended use (state "personal /
   non-production analytics"). MaxMind issues an Account ID and a
   License Key.
2. Set `MAXMIND_ACCOUNT_ID` and `MAXMIND_LICENSE_KEY` in your `.env`
   file (see `.env.example`). They are read at compose-up time.
3. `docker compose up`. The geoipupdate container runs once on
   start, downloads `GeoLite2-ASN.mmdb` to the `cstack-geoip`
   volume, and refreshes weekly thereafter.

When the env vars are unset the geoipupdate container exits cleanly
and the rest of the stack still runs. The ASN lookup module
(`packages/ml-features/src/cstack_ml_features/asn.py`) falls back to
a deterministic prefix table that resolves the synthesizer's
TEST-NET addresses, so fixture-only flows keep producing the same
ASN feature values.

Sprint 7 (live tenant integration) is when real ASN numbers start
mattering for anomaly detection on real Graph traffic; until then the
GeoIP setup is optional.

## Bootstrap idempotency

| service           | re-run behaviour                                                                            |
| ----------------- | ------------------------------------------------------------------------------------------- |
| fixtures          | upsert; safe to re-run, fast                                                                |
| audit             | dedupe by `Finding.compute_id`; rerun produces zero new rows                                |
| anomaly-bootstrap | sentinel + `--skip-if-registered`; warm `down && up` exits in <200ms (Sprint 6.7)           |
| api               | start fresh each up                                                                         |
| web               | start fresh each up                                                                         |
| geoipupdate       | runs at start when MaxMind env vars set; refreshes weekly; exits early when env vars absent |
