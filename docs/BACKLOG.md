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
- [ ] **Sprint 7 activation experiments for gated ML paths.** First
      live-tenant work flips `CSTACK_ML_TRAINING_TOPOLOGY=per_user`
      against the test tenant, measures precision/recall delta vs the
      pooled default, decides whether to flip the default. Same
      gate-and-measure pattern for `CSTACK_ML_OFF_HOURS_ADMIN_ENABLED=true`.
      Treat this as a controlled A/B-style measurement (one tenant,
      side-by-side metrics, explicit decision criterion before the
      sweep), not a default flip. Sprint 3.5 plumbed both; Sprint 3.5b
      gated them after synthetic regression; Sprint 7 has the data to
      evaluate them properly.
- [ ] **CI env hygiene for ML feature flags.** Add a package-level
      `conftest.py` autouse fixture in `packages/ml-anomaly/tests/` and
      `packages/ml-features/tests/` that calls `monkeypatch.delenv` on
      `CSTACK_ML_TRAINING_TOPOLOGY` and `CSTACK_ML_OFF_HOURS_ADMIN_ENABLED`
      so any env-var leaks from CI runners do not silently activate
      gated paths during tests. ~5 minute fix; do before Sprint 7.
      Surfaced in Sprint 3.5b final report under "Gate concern".
- [ ] **Anomaly-bootstrap idempotency in compose.** The
      `anomaly-bootstrap` service in `infra/docker/compose.yaml`
      retrains every up because `--skip-if-registered` does not trigger
      when the named volume already carries an `@champion` alias.
      Investigate whether the flag's check (does a champion alias
      already exist for the tenant?) is correctly evaluated before the
      train call. Sprint 6.6 logged this; it is still open.
- [ ] **Husky pre-commit lint-staged hook.** The existing
      `.husky/pre-commit` is a placeholder ("lint-staged is added in a
      later sprint") and does not actually run prettier on staged files.
      Format drift recurs whenever docs are hand-edited; Sprint 6.5
      polish work and recent post-3.5 commits both produced drift CI
      caught only after push. Add `lint-staged` config to
      `package.json`, wire `.husky/pre-commit` to run
      `npx lint-staged`, cover both `.md` and `.ts` / `.tsx` / `.json`
      patterns. Mid-priority; not blocking Sprint 7 but worth doing
      before too many more sprints accumulate doc drift.
- [ ] **Capture remaining UI screenshots.** `docs/images/anomaly-feed.png`
      and `docs/images/anomaly-drilldown.png` are still placeholders.
      Replace `<!-- screenshot pending -->` markers in
      `docs/SCREENSHOTS.md` and root `README.md` once captured.
- [ ] **Replace pwsh cert-store shell-out** with native cryptography lookup.
      `packages/graph-client/src/cstack_graph_client/credentials.py` currently
      shells to PowerShell to load the cert from the Windows CurrentUser store.
- [ ] **Real ASN/GeoIP lookup**, replacing the IP-prefix stub in
      `packages/ml-features/src/cstack_ml_features/asn_stub.py`. Maxmind or
      ipinfo. Function signature stays the same.

## Mid-term (V1 polish, conditional on demand)

- [ ] **Hard time floor on the off-hours-admin rule.** When activating
      in Sprint 7 against real data, if the false-positive rate is
      high, add a hard 06:00-22:00 user-local-time boundary inside
      `_off_hours_admin` in addition to the per-user time anchor. The
      rule's design intent assumed real per-user variance; if
      synthetic-style determinism also appears in real data the hard
      floor protects against routine admin overnight activity firing
      the rule.
- [ ] **Sklearn / numpy version pinning for reproducible calibration.**
      Sprint 3.5b found that calibration values drift between
      sklearn / numpy versions: Sprint 3's recorded numbers shifted
      ~0.02-0.05 on precision and ~0.04-0.11 on recall after a routine
      library update. Pin specific versions in `pyproject.toml` and
      decide between (a) hard pinning (`==X.Y.Z`) for ML packages so
      calibration tables are reproducible, or (b) tolerance-aware
      tests that do not require exact decimals. Option (a) is
      friendlier for new contributors; option (b) keeps dep upgrades
      cheap.
- [ ] Streaming LLM narrative responses in the dashboard. Today the UI shows a
      skeleton during the ~10-second generation; SSE would close that gap.
- [ ] Spend dashboard for LLM token usage. Replaces the
      `cstack narrative cache-stats` CLI with a UI surface and historical
      chart of dollars per tenant per day.
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

## CIPP-inspired patterns (CodeBlue internal tool roadmap)

cstack is an internal MSP tool, not a CIPP competitor. CIPP is a mature
reference codebase whose patterns can inform this one. Items are
prioritised against CodeBlue's actual fleet shape (small handful of
tenants today, scaling) rather than CIPP's broad SaaS audience.

### High leverage

- [ ] **Standards engine.** Promote each audit rule from a single
      Report-mode evaluator to a tri-mode (`Report` / `Alert` /
      `Remediate`) abstraction. Today every rule is Report-only
      (findings persist). Alert-mode pushes findings into Teams or
      ticketing on a schedule. Remediate-mode is V2 territory because
      it requires Graph write scopes and explicit safeguards (read-only
      posture today). The Report -> Alert step is the cheap win and
      the right next move once Sprint 7 lands.
- [ ] **Per-rule remediation playbooks** as structured PowerShell
      snippets the dashboard exposes for one-click copy. Today the LLM
      narrative includes remediation prose; formalising as a per-rule
      structured field (alongside the existing `references` list) lets
      the UI render them deterministically without a per-finding LLM
      call.
- [ ] **BPA-style scorecard.** Aggregate findings into a tenant-level
      compliance score with category breakdowns. Builds on the existing
      `findings_summary` endpoint; the new work is the presentation
      layer and the scoring formula. Useful for CodeBlue's quarterly
      client review meetings.

### Tenant variables and templating

- [ ] **System variables and per-tenant variables** for use in
      narratives, alert templates, and remediation snippets. System:
      `{TenantId}`, `{TenantDisplayName}`, `{Now}`. Per-tenant
      user-defined: `{ContactEmail}`, `{TicketingSystemUrl}`,
      `{EscalationPath}`. Land after Sprint 7 when the variable space
      has real callers.

### Multi-tenant action UI

- [ ] **Bulk-tenant action surface.** Patterns from CIPP: select N
      tenants, run an action across all of them, see per-tenant results
      streaming in. Deferred until cstack scales beyond two or three
      tenants on the CodeBlue fleet.

### Compliance and retention

- [ ] **Audit log retention policy.** Cstack already retains findings
      indefinitely (DuckDB), unlike Microsoft's 30-day default for some
      logs. Surface this as a feature in docs and add bounded retention
      (90 / 180 / 365 day windows) configurable per tenant.
- [ ] **PDF export for BPA scorecards.** Out of cstack's "internal
      tool" scope today, but useful when CodeBlue wants to share a
      cleaned-up scorecard with a client. wkhtmltopdf or weasyprint
      from the FastAPI app.

### Identity and access

- [ ] **GDAP migration helpers.** Only relevant when cstack has a real
      partner (GDAP) relationship. Defer until live tenants and a real
      GDAP need.
- [ ] **SAM / encrypted token storage.** Cstack stores cert thumbprints
      in `tenants.json` plaintext. Encrypt at rest (Windows DPAPI for
      single-host installs; KMS-style integration for fleet). Sprint 7
      follow-up.

### Authoring surface (V2 territory)

- [ ] **Custom Standards definitions** authored in YAML or via UI
      without touching code. CIPP supports user-defined standards; cstack's
      15 rules are code-defined today. Significant work; defer until V2
      because the eval harness and prompt-version machinery would need
      to extend to user-defined rule families too.

## Long-term (V2 territory)

- [ ] **Per-role pooled tier.** A third anomaly modelling tier between
      tenant-pooled and per-user: pool sign-ins by role (Global Admin,
      Helpdesk, Finance, etc.) when the per-user fits are too sparse but
      the tenant-pooled model is too generic. Sprint 3.5 left the
      architectural slot open but did not implement; revisit once
      Sprint 7 surfaces the real-data shape that motivates it.
- [ ] Cross-tenant anomaly models. Embedding-based shared signals across the
      MSP fleet, with per-tenant fine-tuning on top.
- [ ] Semantic cache deduplication for the narrative cache. Two findings with
      byte-different but semantically identical evidence get separate cache
      entries today; embedding similarity collapses them.
- [ ] LSTM autoencoder layer alongside the Isolation Forest. Sprint 3.5
      reassessed and decided the per-user IF infrastructure was the right
      next step instead; revisit only if Sprint 7 real-data calibration
      shows the same precision ceiling that synthetic data exhibited.
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
- [ ] Whether per-prompt customisation (one prompt template per rule_id family)
      lifts narrative quality over the single canonical template. Eval harness
      can answer this when there's tenant variety; punted for now.
- [ ] **CI runner env-var leak surface.** Confirm whether GitHub Actions
      or any other CI runner cstack uses sets `CSTACK_*` env vars at the
      runner level. If yes, the `conftest.py` env-scrubbing fixture
      (Near-term) is not sufficient and the CI workflow itself needs an
      explicit env-cleaning step. Lower priority than the conftest
      fixture but worth checking once.

## Other future modules

These are toolkit additions, not signalguard work. Each has its own design
accent already reserved in `docs/DESIGN_TOKENS.md` and a single-line module
slot ready in the dashboard sidebar.

- [ ] LicenseLens: M365 license utilisation and cost optimisation.
- [ ] Driftwatch: tenant configuration drift detection across snapshots.
- [ ] ChangeRadar: change-management and audit-trail correlator.
- [ ] CompliancePulse: scheduled compliance attestation reporting.

## Last reviewed

Last reviewed: 2026-04-30 after Sprint 3.5b. Next review: when tenant
access lands for Sprint 7.
