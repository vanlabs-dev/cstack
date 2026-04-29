# Screenshots

Visual reference for cstack's UI. Captured against fixture data (tenant-a,
tenant-b, tenant-c).

> See [docs/INDEX.md](./INDEX.md) for the full documentation map.

For capture conventions and recapture instructions see
[docs/images/README.md](./images/README.md).

## Home

<!-- screenshot pending: home-overview.png -->

Module grid, tenant connections panel with sync status dots, recent activity
feed grouped by day. The cstack workspace landing screen.

## SignalGuard tenant overview

<!-- screenshot pending: signalguard-overview.png -->

Four KPI cards with sparklines (open findings, anomalies last 7d, coverage
score, last sync), CA audit and anomaly summary cards, coverage matrix preview,
data freshness panel.

## CA audit findings list

<!-- screenshot pending: findings-list.png -->

Filter chip strip across the top, dense findings table with severity badges
(colour + shape paired for accessibility), right rail with summary card and
filtered counts.

## CA audit findings expanded

<!-- screenshot pending: findings-expanded.png -->

One row inline-expanded showing the four-section LLM narrative (why this
fired, what it means, remediation, caveats), affected objects with
copy-id affordance, evidence JSON, references, and the regenerate button
(dev key only).

## Coverage matrix

<!-- screenshot pending: coverage-matrix.png -->

Five-by-five heatmap of user segments by app segments. Severity-shape protection
level indicators in each cell; clicking a cell opens a side panel showing
matching policies and weak-cell findings.

## Sign-in anomaly feed

<!-- screenshot pending: anomaly-feed.png -->

Timeline list of flagged sign-ins with SHAP top-3 feature chips, filter rail
on the left, bulk-select with sticky action bar at the bottom.

## Sign-in anomaly drill-down

<!-- screenshot pending: anomaly-drilldown.png -->

Sixty-forty split: full sign-in metadata table on the left grouped into
sections (identity, location, network, client, auth, outcome); location card,
SHAP waterfall, and per-user sign-in history strip on the right.

## Settings, audit rules tab

<!-- screenshot pending: settings-audit-rules.png -->

Read-only catalogue of the 15 CA audit rules with severity badges, descriptions,
and references to Microsoft Learn, CISA SCuBA, CIS, and NCSC NZ.
