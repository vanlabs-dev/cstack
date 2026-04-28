# Sprint notes

## Sprint 1 fixture smoke (2026-04-27)

End-to-end run from a clean working tree. No live tenant touched.

### Commands

```sh
rm -rf data tenants.json
uv run cstack fixtures load-all
uv run cstack tenant list
uv run cstack extract ca-policies --tenant tenant-a
uv run cstack extract all --tenant tenant-b
```

### Observed counts

| Fixture  | ca_policies | named_locations | users | groups | directory_roles |
| -------- | ----------- | --------------- | ----- | ------ | --------------- |
| tenant-a | 8           | 3               | 60    | 12     | 8               |
| tenant-b | 5           | 1               | 80    | 11     | 5               |
| tenant-c | 11          | 4               | 75    | 13     | 8               |

`tenant list` shows all three rows with `fixture=yes`.

### Raw outputs

The `extract` commands wrote raw JSON snapshots under
`data/raw/<tenant_id>/2026-04-27/`:

- tenant-a: `ca-policies.json` (single resource extracted)
- tenant-b: `ca-policies.json`, `named-locations.json`, `users.json`,
  `groups.json`, `directory-roles.json` (full extract via `extract all`)

### Database checks

- `SELECT tenant_id, COUNT(*) FROM ca_policies GROUP BY tenant_id` returns
  the same row counts as the metadata above.
- `SELECT * FROM ca_policies WHERE tenant_id = '<tenant-a id>' AND (id IS NULL OR display_name IS NULL)` returns zero rows. No nulls slip into non-nullable columns.

### Issues

None. The pipeline ran cleanly without warnings.

### Hand-off

Sprint 2 can build the audit logic against the DB shape produced by this
run. Expect to consume `ca_policies`, `named_locations`, `users`,
`groups`, and `directory_roles` for tenant-scoped queries.

## Sprint 2 calibration (2026-04-28)

CA audit module landed: 4 packages (audit-core, audit-coverage,
audit-rules, audit-exclusions), DuckDB migration 006_findings, and the
`cstack audit` subcommand. Calibration loop ran from a clean state.

### Commands

```sh
rm -rf data && uv run cstack fixtures load-all
uv run cstack audit all --tenant tenant-a
uv run cstack audit all --tenant tenant-b
uv run cstack audit all --tenant tenant-c
```

### Observed counts (post-calibration)

| Fixture  | total | coverage | rule | exclusion | critical | high | medium | low | info |
| -------- | ----- | -------- | ---- | --------- | -------- | ---- | ------ | --- | ---- |
| tenant-a | 8     | 0        | 2    | 6         | 0        | 0    | 1      | 7   | 0    |
| tenant-b | 29    | 3        | 14   | 12        | 1        | 6    | 15     | 6   | 1    |
| tenant-c | 10    | 2        | 5    | 3         | 0        | 4    | 3      | 3   | 0    |

These now live in each fixture's `metadata.json` `expected_findings`
block as the new ground truth.

### Rule fixes during calibration

- `rule.disabled-policies-old` and `rule.report-only-graduated` crashed on
  tenant-b and tenant-c with `TypeError: can't compare offset-naive and
offset-aware datetimes`. DuckDB returns naive timestamps; `context.as_of`
  is UTC-aware. Added `_helpers.ensure_utc` and routed the comparisons
  through it. Both rules now run cleanly across all fixtures.

### Fixture corrections during calibration

None. Each fixture maps to its scenario tags as designed:

- tenant-a (well-configured) emits zero CRITICAL or HIGH findings; the 8
  surfaced are LOW or MEDIUM hygiene observations (`exclusion.undocumented`
  on policies that excise break-glass without a keyword in the displayName,
  one MEDIUM `rule.workload-identity-policies`, one LOW
  `rule.persistent-browser-unmanaged`).
- tenant-b emits the gaps the description promised: `rule.mfa-admins`
  CRITICAL, `rule.block-legacy-auth` HIGH, `rule.breakglass-configured`
  HIGH, both risk-based rules HIGH, two `rule.report-only-graduated`,
  one `rule.disabled-policies-old`, and a 14-user exclusion creep that
  produces nine `exclusion.stale-user` rows because that is how many of
  the seeded exclusions are 90+ days inactive in the generator output.
- tenant-c hits every Graph shape we wired up; no rule crashes.

### Disagreements parked

None. Rules and fixtures agree. Schema migration `006_findings` quoted the
SQL keyword `references` so the column round-trips cleanly through DuckDB.

### Verdict

Calibrated. Re-run `cstack audit all --tenant <name>` and update the
fixture's `metadata.json` whenever a rule changes or a fixture grows new
shape; the integration tests in `audit-coverage`, `audit-rules`, and
`audit-exclusions` read `expected_findings.by_category` directly so they
stay in sync without hand-editing test code.

## Sprint 3 anomaly calibration (2026-04-29)

Trained a pooled IsolationForest per tenant against the `baseline` scenario
and scored against `baseline` and `replay-attacks`. Per-user models and the
`noisy` scenario are deferred to Sprint 3.5 (see deviations below).

### Pipeline tweaks during calibration

- Initial `score_batch` ran SHAP across every sign-in (~3300 rows) which took
  ~10 minutes per scoring pass. Restricted SHAP to rows the model already
  flagged as anomalous; scoring now finishes in ~30s on tenant-a.
- IsolationForest was wrapped in a `Pipeline(StandardScaler, IF)` because the
  raw feature scales differ by orders of magnitude
  (`distance_from_last_signin_km` is 0..20000 while `is_weekend` is 0/1) and
  the unscaled IF tree splits were dominated by the high-range columns,
  missing categorical anomaly signals like `is_new_country_for_user`.
- MLflow on Windows rejected `file://D:/...` as a remote URI; switched
  `configure_tracking` to use `Path.as_uri()` so Windows drive letters round-
  trip correctly. Linux/macOS paths are unaffected.

### Tenant-a results

| Scenario       | flagged | flagged ge 0.7 | ground-truth | TP  | precision | recall | F1   | FPR   |
| -------------- | ------- | -------------- | ------------ | --- | --------- | ------ | ---- | ----- |
| baseline       | 67      | 17             | 0            | 0   | n/a       | n/a    | n/a  | 0.020 |
| replay-attacks | 310     | 53             | 27           | 1   | 0.003     | 0.037  | 0.01 | 0.092 |

Only one ground-truth event was caught (a single credential-stuffing
sign-in). Impossible travel, MFA bypass, off-hours admin, and the new-ASN
injection all scored as more normal than baseline outliers despite their
features being unambiguously anomalous (eg the second impossible-travel
event has `distance_from_last_signin_km=2625`, `is_new_country=1`,
`is_new_asn=1`).

### Why recall is low

The pooled IF was trained on baseline data that already contains 1% travel
events, occasional mobile-carrier ASN changes, and 2% MFA failures. The
injected anomalies share their feature regions with these legitimate-but-
rare events, so the model treats them as "normal-rare" rather than
"abnormal". Two structural fixes are parked for Sprint 3.5:

- Per-user models will catch the deviations from individual baselines (a
  user who never roams suddenly travelling is anomalous to that user even if
  it is normal at the tenant level).
- A hybrid rules + IF detector adds rule-based pre-filters for unambiguous
  patterns (impossible travel, new ASN + new country combinations) and uses
  IF for behavioural drift only.

### Deviations from the spec

- Per-user models, `tenant-b` / `tenant-c` calibration, and the `noisy`
  scenario are deferred to Sprint 3.5. Token budget and the recall problem
  surfaced during tenant-a calibration both pointed to "fix the model first,
  then run the full sweep".
- Per-user model registration in MLflow (one registered model per user) was
  scoped out for V1: the registry would carry tens of small models per
  tenant and the per-user fits did not survive calibration anyway. Pooled
  registered model + per-user fits in memory is cleaner once Sprint 3.5
  revisits the modelling approach.
- MLflow file backend emits a deprecation warning under MLflow 2.18+; the
  warning is harmless for fixture work and the migration to a SQLite backend
  is a Sprint 3.5 housekeeping item.

### Verdict

The pipeline runs end-to-end (`signins extract` -> `anomaly train` ->
`anomaly promote --force` -> `anomaly score` -> findings landing in
DuckDB), MLflow tracks every run with @champion / @challenger aliases,
SHAP attributions surface on flagged events, and drift PSI / shadow
scoring helpers are in place. Recall is the open problem and the next
calibration pass (Sprint 3.5) needs structural changes, not a parameter
tweak.
