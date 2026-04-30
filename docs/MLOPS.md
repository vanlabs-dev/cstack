# MLOps walkthrough: SignalGuard sign-in anomaly detection

> See [docs/INDEX.md](./INDEX.md) for the full documentation map.

## Overview

cstack SignalGuard ships two halves: a deterministic CA audit engine
(Sprint 2) and a behavioural sign-in anomaly detector (Sprint 3, this
document). The anomaly half watches Microsoft 365 Entra sign-in events
per tenant, flags rows that look unlike a user's normal pattern, and
writes findings into the same `findings` table the audit module
populates so a single LLM narrator (Sprint 6) can describe both. This
document is the MLOps view of how that detector trains, promotes,
scores, monitors, and rolls back inside cstack.

## System architecture

```
+----------------------+        +-----------------------+
| signins extract      |        | live Graph (Sprint 7) |
| (fixture or Graph)   |        +-----------+-----------+
+----------+-----------+                    |
           v                                v
+--------------------- raw + normalised signins ---------------------+
|  raw_payload JSON  |  signins (one row per Graph signIn entity)    |
+----------+----------------------------------------------+----------+
           |
           v
+-----------------------------+
| ml-features.pipeline        |   FEATURE_COLUMNS (alphabetical)
| - extractors per feature    |   FeatureSet pydantic contract
| - history.UserHistory       |   change either => new model version
+--------------+--------------+
               |
               v
+--------------+----------------+      mlflow tracking + registry
| ml-anomaly.training           |----> signalguard-anomaly-<tenant>
| PerUserBundle(                |      one model.joblib artefact per
|  per-user IFs +               |      version, @challenger -> @champion
|  cold-start pooled IF +       |      via aliases
|  per-user time anchors)       |
+--------------+----------------+
               |
        +------+------+
        v             v
+--------------+   +-----------------+
| scoring      |   | promotion gate  |
| (SHAP top-3) |   | shadow + PSI    |
+------+-------+   +--------+--------+
       |                    |
       v                    v
+----- anomaly_scores ------+----------+
| (signin x model x version, immutable)|
+--------------+-----------------------+
               |
               v
+--------------+---------------+        Sprint 6 LLM narrator
| findings (category=anomaly)  |------> Sprint 5 frontend
+------------------------------+
```

The whole pipeline is a five-package vertical slice:
`ml-features` -> `ml-anomaly` -> `ml-mlops`, with `cstack-audit-core`
owning the shared Finding type and the storage layer holding the DuckDB
schemas. Each package has a single dependency direction; nothing
circular, nothing cross-coupled.

## Modelling approach

V1 trained one pooled Isolation Forest per tenant on the last
`lookback_days` of sign-ins. Sprint 3.5 replaced this with a tenant
**bundle**: one fitted `Pipeline` per user with at least
`min_samples` (default 30) sign-ins, plus one shared cold-start pooled
pipeline that handles users below the threshold. The bundle is the
unit of MLflow registration: one registered model per tenant
(`signalguard-anomaly-{tenant_id}`), one `model.joblib` artefact per
version. Per-user pipelines are _not_ registered separately; that
would multiply registry entries by N users with no operational
benefit.

Why Isolation Forest and not the alternatives:

- **One-class SVM**: kernel choice matters and quadratic-in-N training is
  rough on a 60-day, multi-thousand-event window. IF is linear in N.
- **Autoencoder**: would learn richer representations but adds PyTorch /
  Keras to the stack and complicates explainability. Sprint 3.5 will
  revisit if IF cannot be calibrated.
- **Supervised**: we do not have labelled anomalies in volume on a real
  tenant. Synthetic injections approximate labels, but training a
  classifier on injected data risks overfitting to the synthetic
  distribution.

The model is wrapped in a `sklearn.pipeline.Pipeline` so a `StandardScaler`
sits in front of the `IsolationForest`. Without scaling the
`distance_from_last_signin_km` feature dominates tree splits because its
range (0..20000) overwhelms 0/1 categorical signals like
`is_new_country_for_user`.

## Feature engineering

Nineteen features in `cstack_ml_features.pipeline.FEATURE_COLUMNS`,
alphabetical so the column order is stable across model versions:

| feature                           | rationale                                             |
| --------------------------------- | ----------------------------------------------------- |
| asn_entropy_30d                   | how varied the user's network footprint already is    |
| country_entropy_30d               | same, geographic                                      |
| day_of_week                       | weekday vs weekend pattern shift                      |
| distance_from_last_signin_km      | impossible-travel signal (great-circle haversine)     |
| failure_reason_category           | lumps Graph error reasons into a small bucket         |
| hour_of_day_cos / hour_of_day_sin | cyclical encoding so 23:00 is close to 00:00          |
| hours_since_last_signin           | clamped to 720h; identifies long absences             |
| is_business_hours_local           | 8am-6pm marker                                        |
| is_failure                        | non-zero error_code                                   |
| is_legacy_auth                    | client_app_used in legacy bucket                      |
| is_new_asn_for_user               | first time we have seen this ASN for this user        |
| is_new_browser_for_user           | new browser fingerprint                               |
| is_new_country_for_user           | first time we have seen this country for this user    |
| is_new_device_for_user            | new deviceId                                          |
| is_new_os_for_user                | new operatingSystem                                   |
| is_weekend                        | day-of-week >= 5                                      |
| mfa_satisfied                     | authenticationRequirement = multiFactorAuthentication |
| risk_level_during_signin_numeric  | none/low/medium/high mapped to 0..3                   |

`UserHistory` (in `ml-features.history`) carries the rolling state each
extractor needs, populated from sign-ins strictly before the row's
`createdDateTime`. The strict ordering matters: features must not leak
information about the row they describe.

ASN lookup is a stub (`ml_features.asn_stub.lookup_asn`) that mirrors the
synthesizer's IP-prefix layout. Sprint 7 swaps this for a real
GeoIP/ASN database once we run against a live tenant; the function
signature stays the same.

## Training lifecycle

`cstack anomaly train --tenant <id>` does five things:

1. Pulls the lookback window of sign-ins from `signins` table.
2. Groups by `user_id`. For each user with at least `min_samples`
   sign-ins (default 30) the trainer fits a dedicated
   `Pipeline(StandardScaler, IsolationForest(n=200, random_state=42))`
   plus a smaller time-only pipeline (4 features) used by the
   off-hours-admin rule. Users below the threshold contribute their
   sign-ins to a single shared **cold-start pooled** pipeline.
3. Computes the user-specific time anomaly p90 from the time-only
   pipeline's training-set scores so the off-hours-admin rule has a
   stable per-user threshold at score time.
4. Bundles the per-user pipelines, the cold-start pooled pipeline,
   feature column order, time anchors, and training metadata into a
   `PerUserBundle` and writes it via joblib.
5. Logs the run to MLflow with parameters, metrics, and the bundle as
   a single `model.joblib` artefact, then registers it under
   `signalguard-anomaly-<tenant_id>` and assigns the `@challenger`
   alias.

`random_state=42` is the convention everywhere in the package. Tests
assert reproducibility by re-fitting and comparing scaler means /
percentile thresholds across runs.

`--skip-if-registered` short-circuits training when an `@champion`
already points at a version of the tenant model. The Compose warm-up
bootstrap uses this to avoid accumulating dead registry versions on
restart.

The MLflow tracking URI resolves in three steps. An explicit
`tracking_uri=` argument always wins (tests inject deterministic per-test
paths via this). Otherwise the `MLFLOW_TRACKING_URI` env var is used
(containers and CI set this). Otherwise the helper falls back to
`sqlite:///./mlruns/mlflow.sqlite`. SQLite is the production default
because it is multi-process safe and behaves correctly under the Compose
bind mounts that Sprint 6.6 introduced; the older `file://./mlruns`
scheme remains available by passing it explicitly and is what the
test suite uses for per-test isolation.

## Promotion gating

Two registered-model aliases control which version scores production
traffic:

- `@champion` is the version `score_batch` and the CLI `score` command
  use.
- `@challenger` is the most recently trained version.

`cstack anomaly evaluate-promotion --tenant <id>` runs shadow scoring
of the challenger against the champion on the last seven days of
sign-ins. The output (`ShadowComparison`) reports champion vs challenger
anomaly counts, agreement percentage, and the alert-volume delta. The
gating policy in `should_promote` blocks promotion when:

- fewer than 100 rows are available for comparison (statistical
  significance), or
- the alert-volume delta exceeds 20% in either direction (operational
  shock to the on-call rotation).

`cstack anomaly promote --tenant <id>` runs the gate; `--force` bypasses
it for the first-ever model on a fresh tenant where there is no
champion to compare against.

## Drift monitoring

`cstack anomaly monitor --tenant <id>` computes per-feature
Population Stability Index (PSI) between the training-window features
and the recent (last seven days) features. Industry-standard thresholds:

- PSI < 0.1: no drift
- 0.1 <= PSI < 0.2: monitor
- PSI >= 0.2: significant drift, retrain candidate

The CLI prints the PSI per feature and a summary of those over the
significant threshold. PSI does not by itself trigger a retrain; it
flags features for the on-call engineer to investigate. Retraining is
manual today, automated weekly by Sprint 4 once the FastAPI scheduler
lands.

## Explainability

SHAP attributions surface in two places:

- Each `AnomalyScore` row carries the top three SHAP contributions in
  `shap_top_features`.
- Each anomaly Finding's `evidence` dict carries the same contributions
  for the LLM narrator (Sprint 6) to render.

We use `shap.Explainer(model.score_samples, background_data)` rather
than `shap.TreeExplainer`. The community consensus is that
`TreeExplainer` has known footguns with IsolationForest because IF leaf
weighting is not the same as random forest leaf weighting, and the
permutation-based Explainer over the prediction function gives stable
attributions.

SHAP runs only on rows the model has flagged as anomalous. Running it on
every row took ~10 minutes for a 3300-row score pass; restricting it to
the ~1-5% flagged rows keeps scoring under 30 seconds.

Direction labels (`pushes_anomalous` vs `pushes_normal`) on each
contribution mean consumers do not need to interpret SHAP signs against
the IF score-direction convention.

## Two-topology training

Sprint 3 trained one pooled model per tenant. Sprint 3.5 added a
per-user topology with a cold-start pooled fallback. Sprint 3.5b
gated the per-user topology behind a feature flag because synthetic
calibration showed it regressed precision uniformly (the synthesizer's
deterministic profiles lack real per-user behavioural variance).

`CSTACK_ML_TRAINING_TOPOLOGY` selects the active path:

- **`pooled`** (default): one IsolationForest fitted on all tenant
  signins. Sprint 3 behaviour. Calibration metrics in
  `metadata.json` reflect this default.
- **`per_user`** (opt-in): per-user IF for users with at least
  `min_samples` sign-ins, plus a cold-start pooled fallback for the
  long tail. Sprint 3.5 behaviour.

Both topologies emit a `PerUserBundle` artefact with the same shape
so scoring code is topology-agnostic. In `pooled` mode
`per_user_models` is empty and the single fit is assigned to
`cold_start_pooled`; every signin routes through cold-start at score
time.

`--topology` on `cstack anomaly train` overrides the env var per
invocation. The MLflow run carries a `topology` tag so eval history
records which topology produced each version.

### Per-user modelling tier

When the active topology is `per_user`, the bundle routes each row
through one of three tiers at score time:

- **`per_user`** when the row's `user_id` has a dedicated pipeline.
  Catches user-individual patterns the pooled model could not isolate
  (a user who never roams looks anomalous when they suddenly travel,
  even when some other user in the tenant travels frequently).
- **`cold_start_pooled`** when the user is below the `min_samples`
  threshold. The shared pooled pipeline is fitted on the union of
  all cold-start users' sign-ins.
- **`rule_only`** when the user has neither a per-user model nor a
  cold-start pooled fallback (rare; happens when training found no
  cold-start users at all and a never-seen user shows up at score
  time). Rule booster floors still apply.

In `pooled` mode every signin reports tier `cold_start_pooled` because
all users route to the single pooled fit. The `model_tier` field is
persisted on every `AnomalyScore` row and visible in the alerts CLI,
the API responses, and the dashboard's SHAP detail card.

### Off-hours-admin rule (gated)

The Sprint 3 calibration documented an off-hours admin sign-in as the
single attack pattern the booster missed. Sprint 3.5 added a rule
that fires when (a) the user holds one of the four tier-0 admin role
template ids (Global Admin, Privileged Role Admin, Privileged
Authentication Admin, Security Admin), AND (b) either the user has a
per-user time-only model and the row's negated time-only score is at
or above the user's training-distribution p90, OR the user is on the
cold-start path and the UTC hour falls in the 22:00-06:00 night band.

The rule's score floor is 0.85 and combines via `max` with the four
hybrid rules and the IF score so a stronger signal is never
downgraded. Decile 9 (p90) was chosen empirically.

**Gate (Sprint 3.5b):** the rule is feature-flagged behind
`CSTACK_ML_OFF_HOURS_ADMIN_ENABLED`, default off. Sprint 3.5
calibration showed the rule's per-user time anchor inflates false
positives on the synthetic fixtures because the synthesizer's admins
have a deterministic work-hours profile and any rare-but-legitimate
overnight sign-in trips the p90 threshold. Set the env var to `true`
(or `1` / `yes` / `on`) to activate; Sprint 7 with real admin
behaviour data will recalibrate against genuine per-user
distributions.

## Calibration results

Sprint 3.5b restored the Sprint 3 pooled-topology defaults after
Sprint 3.5's per-user calibration showed a uniform precision
regression. The HEAD calibration metrics (default config: pooled
topology, off-hours-admin rule gated off) sweep across all three
fixture tenants and all three scenarios on 2026-04-30:

| tenant   | scenario       | rows | flagged | ge 0.7 | GT  | TP  | precision | recall | F1    | FPR   |
| -------- | -------------- | ---- | ------- | ------ | --- | --- | --------- | ------ | ----- | ----- |
| tenant-a | baseline       | 3321 | 173     | 61     | 0   | 0   | n/a       | n/a    | n/a   | 0.018 |
| tenant-a | replay-attacks | 3489 | 191     | 101    | 27  | 25  | 0.248     | 0.926  | 0.391 | 0.022 |
| tenant-a | noisy          | 3718 | 195     | 104    | 27  | 25  | 0.240     | 0.926  | 0.382 | 0.021 |
| tenant-b | baseline       | 2909 | 149     | 53     | 0   | 0   | n/a       | n/a    | n/a   | 0.018 |
| tenant-b | replay-attacks | 2876 | 155     | 91     | 27  | 25  | 0.275     | 0.926  | 0.424 | 0.023 |
| tenant-b | noisy          | 2958 | 162     | 91     | 27  | 25  | 0.275     | 0.926  | 0.424 | 0.023 |
| tenant-c | baseline       | 4459 | 231     | 65     | 0   | 0   | n/a       | n/a    | n/a   | 0.015 |
| tenant-c | replay-attacks | 4461 | 238     | 98     | 27  | 24  | 0.245     | 0.889  | 0.384 | 0.017 |
| tenant-c | noisy          | 4522 | 246     | 94     | 27  | 24  | 0.255     | 0.889  | 0.397 | 0.016 |

Recall meets the 0.80 floor on every attack scenario (0.889-0.926),
including tenant-c noisy that Sprint 3.5 dropped to 0.741. Precision
0.245-0.275, F1 0.382-0.424.

### Sprint 3.5 vs Sprint 3.5b

| scenario        | metric    | 3.5 (per-user, rule on) | 3.5b (pooled, rule off) | delta  |
| --------------- | --------- | ----------------------- | ----------------------- | ------ |
| tenant-a/replay | precision | 0.209                   | 0.248                   | +0.039 |
| tenant-a/replay | recall    | 0.852                   | 0.926                   | +0.074 |
| tenant-a/noisy  | precision | 0.205                   | 0.240                   | +0.035 |
| tenant-a/noisy  | recall    | 0.889                   | 0.926                   | +0.037 |
| tenant-b/replay | precision | 0.235                   | 0.275                   | +0.040 |
| tenant-b/replay | recall    | 0.852                   | 0.926                   | +0.074 |
| tenant-b/noisy  | precision | 0.225                   | 0.275                   | +0.050 |
| tenant-b/noisy  | recall    | 0.852                   | 0.926                   | +0.074 |
| tenant-c/replay | precision | 0.209                   | 0.245                   | +0.036 |
| tenant-c/replay | recall    | 0.852                   | 0.889                   | +0.037 |
| tenant-c/noisy  | precision | 0.180                   | 0.255                   | +0.075 |
| tenant-c/noisy  | recall    | 0.741                   | 0.889                   | +0.148 |

Pooled-topology + hybrid-rules-only restores Sprint 3 behaviour and
fixes the tenant-c noisy slip Sprint 3.5 introduced. The Sprint 3.5
infrastructure (PerUserBundle, cold-start fallback, off-hours-admin
rule, per-user time anchor, MLflow `artifact_location` plumbing,
`--skip-if-registered`) remains in place; the topology and the rule
are simply gated off until Sprint 7 has real-tenant data to
calibrate against.

### Gate verification

A second sweep on tenant-a/replay-attacks with both flags activated
(`CSTACK_ML_TRAINING_TOPOLOGY=per_user`,
`CSTACK_ML_OFF_HOURS_ADMIN_ENABLED=true`) reproduces Sprint 3.5
metrics exactly: precision 0.209, recall 0.852, F1 0.336, FPR 0.025.
The gate works.

### Sprint 3.5 archived calibration table

For reference, the per-user-topology calibration that Sprint 3.5
ran (and that Sprint 3.5b gated off because of the precision
regression):

| tenant   | scenario       | rows | flagged | ge 0.7 | GT  | TP  | precision | recall | F1    | FPR   |
| -------- | -------------- | ---- | ------- | ------ | --- | --- | --------- | ------ | ----- | ----- |
| tenant-a | baseline       | 3321 | 191     | 71     | 0   | 0   | n/a       | n/a    | n/a   | 0.021 |
| tenant-a | replay-attacks | 3489 | 227     | 110    | 27  | 23  | 0.209     | 0.852  | 0.336 | 0.025 |
| tenant-a | noisy          | 3718 | 231     | 117    | 27  | 24  | 0.205     | 0.889  | 0.333 | 0.025 |
| tenant-b | baseline       | 2909 | 168     | 64     | 0   | 0   | n/a       | n/a    | n/a   | 0.022 |
| tenant-b | replay-attacks | 2876 | 191     | 98     | 27  | 23  | 0.235     | 0.852  | 0.368 | 0.026 |
| tenant-b | noisy          | 2958 | 201     | 102    | 27  | 23  | 0.225     | 0.852  | 0.357 | 0.027 |
| tenant-c | baseline       | 4459 | 261     | 89     | 0   | 0   | n/a       | n/a    | n/a   | 0.020 |
| tenant-c | replay-attacks | 4461 | 273     | 110    | 27  | 23  | 0.209     | 0.852  | 0.336 | 0.020 |
| tenant-c | noisy          | 4522 | 273     | 111    | 27  | 20  | 0.180     | 0.741  | 0.290 | 0.020 |

### Layer attribution (tenant-a x replay-attacks)

The same scoring run with different layer combinations enabled. On
tenant-a every user is above the 30-signin threshold so the
cold-start pooled tier is dormant; the table shows the four
meaningful steps.

| layer combination                | flagged_high | TP  | FP  | precision | recall | F1    | FPR   |
| -------------------------------- | ------------ | --- | --- | --------- | ------ | ----- | ----- |
| per-user IF only (no rules)      | 35           | 2   | 33  | 0.057     | 0.074  | 0.065 | 0.010 |
| per-user + cold-start (no rules) | 35           | 2   | 33  | 0.057     | 0.074  | 0.065 | 0.010 |
| per-user + pooled + hybrid rules | 98           | 22  | 76  | 0.224     | 0.815  | 0.352 | 0.022 |
| full (+ off-hours-admin)         | 110          | 23  | 87  | 0.209     | 0.852  | 0.336 | 0.025 |

The four hybrid rules carry the workload, exactly as in Sprint 3
(impossible-travel, new country + new ASN, failure + new ASN, MFA
bypass + legacy auth). The off-hours-admin rule adds the missing
recall point at the cost of ~1.5 precision points; the per-user IF
alone catches almost nothing on synthetic data because the rules
already cover the unambiguous attack patterns and the per-user IF is
too sensitive on each user's small training distribution.

### Tier distribution

Across all 9 fixture scenarios scoring runs route 100% of rows
through `per_user`. Every fixture user has at least 30 sign-ins, so
the cold-start pooled tier and the rule-only path are both dormant
on this fixture. Sprint 7 with real tenant data is expected to
exercise both: live tenants typically have a long tail of users with
low sign-in volumes plus visitors / contractors who never reach the
threshold.

### Lift attribution narrative

- **Per-user IF alone** does almost nothing for recall on synthetic
  data. The pooled IF was the same. Tree-based anomaly detectors
  struggle when train and test distributions overlap, which they do
  by construction in our synthesizer.
- **Hybrid rules** lift recall from 0.07 to 0.82. They encode
  unambiguous attack patterns the IF cannot learn from baseline data
  alone.
- **Off-hours-admin rule** adds the 0.85 plateau by closing the
  Sprint 3 admin-time miss. It costs precision because the rule
  fires on legitimate-but-unusual admin sign-ins too; in production
  this is the kind of finding that wants triage rather than auto-
  alert.
- **Per-user infrastructure** (the bundle, the cold-start fallback,
  the time anchor) is plumbed end to end and exercised by tests.
  Sprint 7's real-data calibration is what will turn the
  infrastructure into precision lift.

The first Sprint 3 scoring run with the IF alone produced TP = 0
across all attacks. Three structural fixes restored recall:

1. A row-alignment bug between `_build_score_features` and
   `score_batch` was applying IF predictions to the wrong rows.
2. A `travel_speed_kmh` interaction feature lets the IF isolate
   physically-impossible velocity directly.
3. A small rule-based booster (`_rule_score_boosts`, now in
   `cstack_ml_anomaly.rules`) raises the normalised score to a hard
   floor for four unambiguous attack patterns.

Sprint 3.5 carried these forward and added the per-user-anchored
off-hours-admin rule. `docs/SPRINT_NOTES.md` carries both sprint
narratives end to end.

## Known limitations

- Synthetic per-user behaviours fit the synthesizer's patterns rather
  than discovering user-individual patterns the model would catch on
  live data. The per-user IF topology and the off-hours-admin rule
  are plumbed end to end but feature-flagged (Sprint 3.5b) because
  synthetic-data calibration regressed; Sprint 7 real-tenant data is
  where they get to prove themselves.
- Precision on the default pooled topology sits at 0.245-0.275 across
  attack scenarios. The hybrid rules drive recall above the 0.80 floor;
  the IF cannot lift precision further when train and test
  distributions overlap by construction (synthetic) or when admins
  signing in overnight is genuinely ambiguous (real).
- ASN lookup is stubbed via IP prefix matching. Real GeoIP
  integration is Sprint 7.
- Scoring is batch only. Real-time scoring is V2.
- No autoencoder yet. Sprint 3.5 reassessed and decided the IF
  precision ceiling on synthetic data did not justify the autoencoder
  build; revisit if Sprint 7 real-data calibration shows the same
  ceiling on live tenants.
- MLflow file-backend deprecation warning surfaces in tests that
  still use `file://` URIs. Production paths default to SQLite as of
  Sprint 6.6 with `MLFLOW_ARTIFACT_ROOT` pinned by Sprint 3.5; tests
  stay on file:// for per-test isolation simplicity.

## Roadmap

- **Sprint 4**: FastAPI backend exposing audit and anomaly findings
  with weekly retrain cron.
- **Sprint 6**: LLM narrator consumes the SHAP top-3 plus rule
  references and generates investigator-ready summaries.
- **Sprint 7**: live tenant validation, real ASN lookup, real
  per-user baselines. The first activation experiment will flip
  `CSTACK_ML_TRAINING_TOPOLOGY=per_user` against the test tenant and
  re-measure precision/recall. If the per-user lift materialises on
  real data, the default flips. Same gate-and-measure pattern for
  `CSTACK_ML_OFF_HOURS_ADMIN_ENABLED=true`. SHAP runtime budget
  tuning against tenant-scale traffic.
- **Future**: per-role pooled tier (a third tier between per-user
  and tenant-pooled, useful when many users hold the same role and
  the pooled model would be too generic but per-user is too sparse).
  Cross-tenant embeddings. Real-time scoring through a streaming bus.
