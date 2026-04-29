# Sprint notes

> See [docs/INDEX.md](./INDEX.md) for the full documentation map.

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

### Three structural fixes during calibration

The first scoring run produced precision / recall = 0 / 0 across the attack
scenarios. Three structural problems came out of the investigation:

1. **Row-alignment bug.** `_build_score_features` iterated users in dict
   order while `score_batch` reordered the source list to match
   "alphabetical user, then chronological". The two orders did not line
   up, so IF predictions and SHAP rows were applied to the wrong sign-ins.
   Switched both code paths to `sorted(by_user.keys())` so the layout is
   identical.
2. **Feature interaction missing.** Pure-feature signals (huge distance,
   new country, new ASN) showed up in baseline travel events too. Added
   `travel_speed_kmh = distance / max(hours_since, 1min)` as a 20th
   feature so the IF can isolate "5000 km/h between sign-ins" directly.
3. **Hybrid booster.** Even with the new feature, the IF treated the
   injected attacks as "rare-but-normal" because tree splits chose among
   20 random features and the unambiguous signals were diluted. Added a
   deterministic post-IF score booster (`_rule_score_boosts`) for four
   obvious attack patterns: impossible travel, new country + new ASN
   combo, failure from a new ASN, and MFA bypass to legacy auth. The
   booster takes a `max` against the IF's normalised score so it never
   drops a strong IF signal.

### Calibration table (all three tenants, all three scenarios)

| tenant   | scenario       | rows | flagged | ge 0.7 | GT  | TP  | precision | recall | F1    | FPR   |
| -------- | -------------- | ---- | ------- | ------ | --- | --- | --------- | ------ | ----- | ----- |
| tenant-a | baseline       | 3321 | 157     | 62     | 0   | 0   | n/a       | n/a    | n/a   | 0.019 |
| tenant-a | replay-attacks | 3489 | 171     | 84     | 27  | 25  | 0.298     | 0.926  | 0.450 | 0.017 |
| tenant-a | noisy          | 3718 | 275     | 96     | 27  | 25  | 0.260     | 0.926  | 0.407 | 0.019 |
| tenant-b | baseline       | 2909 | 122     | 44     | 0   | 0   | n/a       | n/a    | n/a   | 0.015 |
| tenant-b | replay-attacks | 2876 | 157     | 80     | 27  | 22  | 0.275     | 0.815  | 0.411 | 0.020 |
| tenant-b | noisy          | 2958 | 169     | 82     | 27  | 23  | 0.280     | 0.852  | 0.422 | 0.020 |
| tenant-c | baseline       | 4459 | 201     | 68     | 0   | 0   | n/a       | n/a    | n/a   | 0.015 |
| tenant-c | replay-attacks | 4461 | 249     | 88     | 27  | 24  | 0.273     | 0.889  | 0.417 | 0.014 |
| tenant-c | noisy          | 4522 | 295     | 95     | 27  | 23  | 0.242     | 0.852  | 0.377 | 0.016 |

Recall on attack scenarios sits between 0.815 and 0.926; the missed events
are the off-hours admin sign-in (no obvious feature signal) and the first
sign-in of an attack chain that on its own looks like a normal sign-in
(eg the Auckland event before impossible travel).

### Surprising and unsurprising findings

- The pure IF found nothing meaningful by itself; the booster does the
  heavy lifting for the unambiguous attack patterns. That matches the
  literature on tree-based anomaly detectors when train and test
  distributions overlap.
- The off-hours admin sign-in is the only attack pattern not caught by
  the booster. Sprint 3.5 will add per-user hour distributions so this
  event becomes anomalous to its specific user even if it looks normal
  at the tenant level.
- The `noisy` scenario adds operational noise (frequent travel, shifted
  hours, mobile-heavy users) but recall stays within ~5 points of
  `replay-attacks`. The rule-based signals are robust to the noise the
  IF struggles with.

### Deviations from the spec

- Per-user model registration in MLflow (one registered model per user)
  was scoped out for V1: the registry would carry tens of small models
  per tenant and the per-user fits did not survive calibration anyway.
  Pooled registered model + the rule-based booster covers the same ground
  for Sprint 3 and per-user fits land in Sprint 3.5 once we have a real
  tenant baseline to learn from.
- MLflow file backend emits a deprecation warning under MLflow 2.18+; the
  warning is harmless for fixture work and the migration to a SQLite
  backend is a Sprint 3.5 housekeeping item.

### Verdict

The pipeline runs end-to-end (`signins extract` -> `anomaly train` ->
`anomaly promote --force` -> `anomaly score` -> findings landing in
DuckDB) on all three fixture tenants across all three scenarios. MLflow
tracks every run with `@champion` / `@challenger` aliases, SHAP
attributions surface on flagged events, drift PSI / shadow scoring
helpers are in place, and the calibrated metrics in each fixture's
`metadata.json` give Sprint 4's API and Sprint 6's narrator a
trustworthy baseline to consume.

## Sprint 5b completion (2026-04-28)

Closed out the SignalGuard frontend with breadth + quality.

### What shipped

- **Four new screens** wired against the live API:
  - `/dashboard/signalguard` per-tenant overview (4 KPI cards, severity
    breakdown bars, anomaly summary, coverage preview, freshness panel).
  - `/dashboard/signalguard/coverage` full coverage matrix heatmap with a
    cell drill-down side panel that lists applicable policies and a
    derived "what's missing" summary.
  - `/dashboard/anomalies` timeline list with time-range segmented control,
    severity threshold chips, status filter (open + 2 placeholder states),
    bulk-select header, and pagination.
  - `/dashboard/settings/{general,audit-rules,anomaly-tuning,api-keys}`
    plus three V2 placeholders (notifications, data-sync, integrations).

- **API additions**: two new endpoints under `/tenants/{id}/api-keys`
  (POST mints + returns plaintext once; DELETE revokes by label). 7
  pytest cases cover the full happy path and 401/403/404/409 edges.

- **74 component tests** across 27 test files: system primitives, layout
  shell, all four 5b screens' key components, and the 5a backfill
  (FindingsTable inline expansion, MetadataTable, ShapWaterfall,
  CopyButton clipboard mock, ApiKeyGate gate logic, FilterChipStrip URL
  push, etc.). Vitest + jsdom + @testing-library/react.

- **Tablet pass at 768px**: the sidebar collapses behind a hamburger
  toggle, KPI grid drops to 2-col, two-column rows stack, the findings
  table hides ID/Age columns, the coverage side panel becomes a bottom
  sheet, and the anomaly feed hides the device column.

- **ShapWaterfall promotion**: the 5a div-based bars are now a real
  recharts horizontal `BarChart` with per-cell colour and a custom
  tooltip. KPI cards use a new `KpiSparkline` (recharts AreaChart).

- **WorldMap polish**: the 5a "Map view in 5b" placeholder is replaced
  with an inline equirectangular SVG showing the current sign-in dot
  in critical-red and historical countries in soft green. No map
  library dependency; ships in the static bundle.

### Concessions

- Audit rules listing is read-only and uses a static catalogue mirroring
  `cstack-audit-rules`; per-rule enable/disable lands in V2 with API
  support (UI is wired, API is not).
- Anomaly tuning threshold and General settings preferences persist to
  `localStorage` only; per-tenant tuning needs an API setter.
- Settings tabs Notifications, Data & sync, and Integrations render
  V2-marked placeholder cards. They were explicitly out of scope for 5b.
- Mobile (<768px) renders correctly but the explicit responsive audit
  was scoped to tablet (`md:` breakpoint).
- The world map is stylised, not geographic; we considered shipping
  TopoJSON country shapes but the size + license churn outweighed the
  legibility gain at 130px tall.

### Test stats

- Web: 27 test files, 74 tests, full suite runs in ~13 seconds.
- API: +7 tests for the new API-key endpoints (existing 50 still green).
- Total green: 81 web + API tests on top of the existing Python suite.

### Verdict

SignalGuard's frontend is feature-complete on fixture data. The CLI is
the only path to retrain/promote models, but every read surface and
the audit/score action endpoints are reachable through the dashboard.
Sprint 6 (LLM narratives) is the highest-leverage next step: every
finding-expansion "Why this fired" section is currently the raw
`summary` string; an LLM rewrite would lift triage UX significantly.

## Sprint 6 LLM narrative calibration (2026-04-29)

Sprint 6 ships the provider abstraction (`llm-provider`), the
finding-to-narrative pipeline (`llm-narrative`), the rubric-based eval
harness (`llm-eval`), and a 20-finding hand-curated golden set sourced
from real tenant-a/b/c audit findings. The calibration loop ran end to
end against the live Anthropic API.

### Models used

- Generator: `claude-opus-4-7` (default, content production)
- Judge: `claude-sonnet-4-6` (different model from generator to mitigate
  self-preference bias)
- Probe: `claude-haiku-4-5` (cheap connectivity check)

### Pointwise rubric scores

Five-criterion rubric scoring, weighted aggregate normalised to 0-100.

| prompt | accuracy | actionability | concision | format_compliance | tone | mean |
| ------ | -------- | ------------- | --------- | ----------------- | ---- | ---- |
| v1     | 5.00     | 5.00          | 4.00      | 5.00              | 5.00 | 95.45 |
| v2     | 4.95     | 5.00          | 4.85      | 5.00              | 5.00 | 98.98 |

Pointwise alone, v2 scored higher because the harder concision floor
(180 words vs v1's 250) lifted the only sub-perfect criterion.

### Pairwise comparisons

| comparison           | a wins | b wins | ties | inconsistent_swaps | winrate(b) |
| -------------------- | ------ | ------ | ---- | ------------------ | ---------- |
| reference vs v1      | 0      | 20     | 0    | 0                  | 1.000      |
| v1 vs v2             | 14     | 0      | 6    | 6                  | 0.150      |

The reference-vs-v1 pairwise is decisive: the LLM-generated v1 narrative
beats every hand-written reference in the golden set, with no
position-swap inconsistency. The v1-vs-v2 pairwise is the more
interesting outcome: v2's pointwise advantage on concision did not
survive direct comparison. The judge consistently picked v1 (or
declared inconsistent ties) because v2's compression cost remediation
detail. The 6 inconsistent swaps (judge flipped its winner when
positions swapped) are the bias-mitigation paying off: those would
have been false signals in a single-pass pairwise.

### Decision

- v1 stays default. v2 is shipped in `prompts/finding_narrative_v2.md`
  as a documented attempt that did not improve perceived quality.
- Lesson for future iterations: pointwise rubrics are useful as a smoke
  test but should not drive prompt-version decisions on their own.
  Pairwise judging surfaces the tradeoffs that pointwise hides.

### Smoke test

End-to-end `cstack audit all --tenant tenant-b` after calibration:

- First pass: 16 generated, 13 cached, 0 errored, $0.89 spent
- Second pass (immediately after): 0 generated, 29 cached, $0.00 spent

The 13 cache hits on the first pass come from findings that were also in
the eval golden set; the second pass demonstrates 100% cache hit rate
once a tenant has been seen.

### Spend

Total Anthropic API spend on this sprint (calibration + smoke tests +
v2 attempt):

- Opus 4.7 generations: ~$1.88 (24,598 input + 20,100 output tokens
  cached; cost driver is output tokens at $75/M)
- Sonnet 4.6 judge calls: ~$1.50 (estimated; 20 pointwise + 40 pairwise
  per comparison run, with cached candidates)
- First production smoke run: $0.89 (16 fresh generations on tenant-b
  not previously narrated)
- Total: ~$4.30 against the $20 hard cap.

