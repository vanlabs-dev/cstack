# Backlog

> See [docs/INDEX.md](./INDEX.md) for the full documentation map.

Parked work. Not blocking; revisit when relevant. Items move into a sprint
when prioritised.

## Near-term (next 1-2 sprints)

- [ ] **Sprint 7: Live tenant integration.** Wire signalguard to a real client
      tenant via the existing certificate-auth path. Calibrate audit rules and
      LLM narratives against real Graph data. Replace stub ASN lookup with a
      real GeoIP database. Address synthetic-data assumptions baked into
      earlier sprints (CRLF tolerances, break-glass naming, 90-day stale
      thresholds calibrated to fixture timing).
- [ ] **Sprint 3.5: Per-user IF anomaly model.** Per-user models lift precision
      against off-hours admin sign-ins that the pooled IF misses. Includes a
      cold-start fallback to the pooled model for users below the sample
      threshold; SQLite-backed MLflow registry; full three-tenant calibration
      across all three scenarios (baseline, replay-attacks, noisy).
- [ ] **Replace pwsh cert-store shell-out** with native cryptography lookup.
      `packages/graph-client/src/cstack_graph_client/credentials.py` currently
      shells to PowerShell to load the cert from the Windows CurrentUser store.
- [ ] **Real ASN/GeoIP lookup**, replacing the IP-prefix stub in
      `packages/ml-features/src/cstack_ml_features/asn_stub.py`. Maxmind or
      ipinfo. Function signature stays the same.

## Mid-term (V1 polish, conditional on demand)

- [ ] Streaming LLM narrative responses in the dashboard. Today the UI shows a
      skeleton during the ~10-second generation; SSE would close that gap.
- [ ] Spend dashboard for LLM token usage. Replaces the
      `cstack narrative cache-stats` CLI with a UI surface and historical
      chart of dollars per tenant per day.
- [ ] Containerisation. Docker Compose for local; deploy stack TBD. Re-enable
      the Next.js `output: "standalone"` build (disabled today because pnpm
      symlinks fail on Windows; works on Linux CI).
- [ ] Phone breakpoints (<768px) in the dashboard. Tablet (>=768px) is wired;
      phone is functionally rendered but not visually audited.
- [ ] Mutation flows in the dashboard for findings (snooze, mark resolved) and
      anomalies. Buttons are stubbed in 5b but require backend support.
- [ ] Per-rule enable/disable in the Audit Rules settings tab. Catalogue is
      read-only today; toggling requires a tenant-scoped rule_state table and
      the audit runner reading it.
- [ ] Anomaly narratives. The LLM narrator currently runs only on CA findings.
      SHAP attributions plus rule references would feed a similar prompt for
      anomaly findings; deferred while pointwise calibration matures.
- [ ] Executive tenant summaries. Cross-finding aggregation that reads as a
      one-paragraph briefing, suitable for an MSP's weekly client report.
- [ ] Token usage logging to a structured backend (instead of file logs).
- [ ] FastAPI scheduler for weekly automated retrains (Sprint 4 territory).
- [ ] Notifications, Data & sync, and Integrations settings tabs in the
      dashboard. Currently placeholders awaiting backend.

## Long-term (V2 territory)

- [ ] Cross-tenant anomaly models. Embedding-based shared signals across the
      MSP fleet, with per-tenant fine-tuning on top.
- [ ] Semantic cache deduplication for the narrative cache. Two findings with
      byte-different but semantically identical evidence get separate cache
      entries today; embedding similarity collapses them.
- [ ] LSTM autoencoder layer alongside the Isolation Forest. Sprint 3.5 will
      reassess once we have live-tenant baselines; deferred unless IF cannot
      be calibrated to the precision target.
- [ ] Real-time scoring through a streaming bus. Today scoring is batch only.
- [ ] Multi-language narratives. English-only today; the prompt template
      versioning supports localised variants.
- [ ] Custom fine-tuned narrative model. Would need a corpus of eval-passing
      narratives that meet the human-engineer bar; unclear when (or if) the
      cost-quality math clears the bar.
- [ ] Real authentication on the regenerate endpoint, beyond the dev API key.
      OAuth or JWT; reserved `Authorization: Bearer` route shape.
- [ ] Tenant-key automatic revoke API. Today rotation is mint-then-strip-by-hand.

## Investigation / open questions

- [ ] Mobile (<768px) layouts. Whether to invest depends on whether MSP
      engineers actually triage on phones. Park until that's known.
- [ ] MLflow file-backend deprecation. Migration to a SQLite backend is a
      housekeeping item; the warning does not affect functionality.
- [ ] Whether per-prompt customisation (one prompt template per rule_id family)
      lifts narrative quality over the single canonical template. Eval harness
      can answer this when there's tenant variety; punted for now.

## Other future modules

These are toolkit additions, not signalguard work. Each has its own design
accent already reserved in `docs/DESIGN_TOKENS.md` and a single-line module
slot ready in the dashboard sidebar.

- [ ] LicenseLens: M365 license utilisation and cost optimisation.
- [ ] Driftwatch: tenant configuration drift detection across snapshots.
- [ ] ChangeRadar: change-management and audit-trail correlator.
- [ ] CompliancePulse: scheduled compliance attestation reporting.
