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
| ml-anomaly.training           |----> signalguard-anomaly-pooled-<tenant>
| Pipeline(StandardScaler, IF)  |      @challenger -> @champion via aliases
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

V1 trains one pooled Isolation Forest per tenant on the last `lookback_days`
of sign-ins. Per-user models would be more sensitive (a user who never
roams looks anomalous when they suddenly travel even if the pattern is
normal at the tenant level), but they introduce the cold-start problem
for new users, multiply MLflow registry entries by hundreds, and require
robust handling of users with too few samples to fit a dedicated tree
ensemble. V1 punts that complexity to Sprint 3.5 (see "Known limitations"
below) and proves the lifecycle on a single shared model first.

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
2. For each user, builds a per-row `UserHistory` and extracts features.
3. Fits the `Pipeline(StandardScaler, IsolationForest(n=200,
random_state=42))` on the resulting DataFrame.
4. Logs the run to MLflow with parameters, metrics, and the sklearn
   model artifact.
5. Registers the artifact under
   `signalguard-anomaly-pooled-<tenant_id>` and assigns the
   `@challenger` alias.

`random_state=42` is the convention everywhere in the package. Tests
assert reproducibility by re-fitting and comparing predictions.

The MLflow tracking URI defaults to a local `./mlruns/` directory using
`Path.as_uri()` so Windows drive paths produce the `file:///` scheme
MLflow's registry requires. The tracking server is intentionally local
in V1; pointing at a remote server is a one-line override on
`configure_tracking`.

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

## Calibration results

Full pipeline ran from a clean DuckDB and `mlruns/` against all three
fixture tenants and all three scenarios on 2026-04-29.

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

Recall sits between 0.815 and 0.926 on attacks across all tenants.
Precision is 0.24-0.30 because the pooled IF still surfaces baseline
outliers (legitimate travel, mobile-carrier ASN swaps) above the 0.7
threshold. The missed events are the off-hours admin sign-in (no
unambiguous feature signal at the tenant level) and the first sign-in
of an attack chain that on its own looks like a normal sign-in.

The first scoring run with the IF alone produced TP = 0 across all
attacks. Three structural fixes restored recall:

1. A row-alignment bug between `_build_score_features` and
   `score_batch` was applying IF predictions to the wrong rows.
2. A `travel_speed_kmh` interaction feature lets the IF isolate
   physically-impossible velocity directly.
3. A small rule-based booster (`_rule_score_boosts`) raises the
   normalised score to a hard floor for four unambiguous attack
   patterns (impossible travel, new country + new ASN, failure +
   new ASN, MFA bypass + legacy auth).

`docs/SPRINT_NOTES.md` under "Sprint 3 anomaly calibration" carries
the full investigation; the booster + interaction feature pattern is
a deliberately small layer on top of the IF and does not replace it.

## Known limitations

- Pooled-only model. Per-user models, autoencoder fallback, and
  weekly automated retrain are Sprint 3.5 work.
- Off-hours admin sign-ins are not caught by the booster. Per-user
  hour distributions in Sprint 3.5 should fix this.
- ASN lookup is stubbed via IP prefix matching. Real GeoIP integration
  is Sprint 7.
- Scoring is batch only. Real-time scoring is V2.
- No autoencoder yet. Sprint 3.5 will reassess once we have live
  tenant baselines; if needed, the autoencoder package will plug into
  the same `ml-features.pipeline` contract.
- MLflow file-backend deprecation warning (MLflow 2.18+). Migration to
  a SQLite backend is a Sprint 3.5 housekeeping item; the warning does
  not affect functionality.

## Roadmap

- **Sprint 3.5** (next): per-user IF + cold-start fallback, hybrid
  rules + IF detector for unambiguous attack patterns, full
  three-tenant calibration including the `noisy` scenario, SQLite
  MLflow backend.
- **Sprint 4**: FastAPI backend exposing audit and anomaly findings
  with weekly retrain cron.
- **Sprint 6**: LLM narrator consumes the SHAP top-3 plus rule
  references and generates investigator-ready summaries.
- **Sprint 7**: live tenant validation, real ASN lookup, SHAP runtime
  budget tuning against tenant-scale traffic.
- **V2**: cross-tenant embeddings, real-time scoring through a
  streaming bus.
