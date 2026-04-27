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
