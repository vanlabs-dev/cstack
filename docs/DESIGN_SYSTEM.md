# Cstack design system

Component patterns, layout primitives, and screen blueprints. Companion to `DESIGN_TOKENS.md`. This document tells the build phase what to make, with what density, and at what level of polish.

The design source artefacts live in `.design/` (gitignored, working material). This document is the committed reference.

## Layout shell

Every authenticated screen sits inside the same shell:

```
┌────────────────────────────────────────────────────────────────────────┐
│ Sidebar (224px)  │  Topbar (44px, breadcrumbs + actions)               │
│                  │ ─────────────────────────────────────────────────── │
│  Wordmark        │                                                     │
│  Tenant scope    │  Main content (max-width 1600px, padded 24-32px)    │
│   ↳ All / Cmpr   │                                                     │
│                  │                                                     │
│  Modules         │                                                     │
│   ● SignalGuard  │                                                     │
│   ○ LicenseLens  │                                                     │
│   ○ ...          │                                                     │
│                  │                                                     │
│  ───────         │                                                     │
│  Home            │                                                     │
│  Docs            │                                                     │
│  Settings        │                                                     │
│  ─ User profile  │                                                     │
└────────────────────────────────────────────────────────────────────────┘
```

### Sidebar (224px wide, collapsible)

- **Wordmark block** (top): a 24px black gradient tile rendering a single lowercase `c` in JetBrains Mono, paired with `cstack` in Inter 14px/600. Version string `v0.4.2` in mono 9.5px below the wordmark. Live indicator (`Dot ok` + "live") in the top-right corner.
- **Tenant scope** section: eyebrow label, then a button-styled selector showing the current tenant with a 2-letter coloured tile (deterministic colour per tenant) and the tenant name. Below that, two ghost buttons: "All tenants" and "Compare". URL drives state via `?tenant=<id>`.
- **Modules** section: eyebrow label, then a vertical list. Active module has:
  - 2px left strip in module accent colour (`sg` for SignalGuard)
  - Subtle background (`surface-subtle`)
  - Icon tile with module accent background (`sg-subtle`) and accent foreground (`sg`)
  - Slightly heavier weight (500)
  - Coming-soon modules have `fg-quaternary` text and a `SOON` mono label on the right
- **Footer** (bottom): Home, Docs, Settings rows. Below that, user profile block with avatar, name, and tenant subdomain.

### Topbar (44px)

Three regions:

- **Left**: breadcrumbs. First breadcrumb is a module pill (e.g. `[shield] SignalGuard`) with the module accent background. Subsequent breadcrumbs are plain text separated by chevrons.
- **Centre**: empty (no tabs in topbar).
- **Right**: contextual actions for the current screen. Always at least one secondary button (`btn`) and one primary button (`btn-primary`) when actions exist. Examples: `[refresh] Sync all` + `[plus] Add tenant`.

## Component primitives

### Severity badge

```
┌──────────────┐
│ ● Critical   │   crit:  filled circle,  bg #FBE9E9, fg #B91C1C
│ ▲ High       │   high:  filled triangle, bg #FBEBE0, fg #C2410C
│ ◆ Medium     │   med:   filled diamond,  bg #FAF1DD, fg #A16207
│ ■ Low        │   low:   filled square,   bg #E6EAF7, fg #1E40AF
│ ○ Info       │   info:  hollow circle,   bg #ECECEA, fg #525252
└──────────────┘
```

11px text, 500 weight, 2px/7px padding, 3px radius. The shape is an 8px element rendered to the left of the label. Triangle uses CSS borders trick. Diamond uses a rotated square. Hollow circle uses `border: 1.5px solid` with transparent background.

### Buttons

Three variants: default (`btn`), primary (`btn-primary`), ghost (`btn-ghost`). Three sizes: small (`btn-sm`, 24px), default (28px), large (`btn-lg`, 32px). Buttons can take an optional leading icon at 12-13px.

Default buttons have a subtle border and 1px shadow. Primary buttons use brand fill with a 12% white interior highlight inset. Ghost buttons have no border or background until hovered. All transitions are 100ms.

### Cards

```
border: 1px solid var(--border)
background: var(--surface)
border-radius: 6px
```

Card hover state lifts the border to `border-strong` over 150ms. Never use shadows on cards. The interior padding is typically 16px to 20px depending on density.

### Tables

Engineering-grade dense tables. Header row is 11.5px, weight 500, `fg-tertiary` colour, with a 1px bottom border. Body rows are 13px, 9px/10px padding, with a `border-subtle` separator between rows. Hover state changes the row background to `surface-hover`. The last row has no bottom border.

A row that's expanded inline gets `surface-subtle` background to differentiate from its neighbours.

Sort icons are tiny chevrons (10px) shown only on the active sort column. Default sort indicator is hidden until hover.

### Pills and chips

22px tall, 8px horizontal padding, 12px text. Used for filter chips, tag chips, breadcrumb module pills. Active chip swaps to `fg` background with `bg` text (high contrast inverse). Hover state changes border to `border-strong`.

### Segmented control

```
[ Day | Week | Month ]
```

Tight inline group. 22px tall buttons with 9px padding. Background is `surface-subtle` with a 1px border. Active button gets `surface` fill and a 2px shadow. Used for time range selectors and view toggles.

### Input fields

32px tall by default, with 1px border and 5px radius. Use `surface-inset` for the field background to make the field visually recede from the page. Focus state shows the brand-coloured 2px outline ring.

### Sparkline

26px tall, 80-88px wide. Polyline at 1.25 stroke width. Optional area fill underneath at 8% opacity in the same colour. No axes, no labels, no tooltips. Pure data shape only.

### Status dot

6px circle. Four kinds: `dot-ok` (green), `dot-warn` (amber), `dot-err` (red), `dot-idle` (neutral grey). Used in tenant connection rows, sync status indicators, live indicators.

### Eyebrow label

10.5px, weight 600, uppercase, letter-spacing 0.07em, colour `fg-tertiary`. Used above section headings to provide subtle context labels.

### Avatar

22-32px circle, deterministic colour from a small palette (purples, olives, slates, teals, ambers — never bright). Initials in white at 42% of the avatar size, weight 600.

## Page header pattern

Every screen has a consistent header:

```
┌──────────────────────────────────────────────────────────────┐
│ Eyebrow context label                                         │
│ Page title (22px/600, -0.018em tracking)        [actions →]  │
│ Optional sub line (13px, fg-tertiary)                         │
└──────────────────────────────────────────────────────────────┘
```

24px below this header before main content begins.

## Screen blueprints

Eight screens designed. Sprint 5a builds three (marked with target). Sprint 5b builds the rest.

### 1. Cstack home (Sprint 5a target)

Three sections stacked vertically:

1. **Workspace header** with eyebrow ("Workspace · iridiumops"), greeting line ("Good afternoon, Marcus"), and a sub-line summarising state ("8 tenants connected · 47 open findings · last refreshed 2m ago").
2. **Module grid** in a responsive grid (1 active card spanning more space, 4 coming-soon cards smaller). Each card has the module icon in its accent tile, module name, description, and either active stats (findings, tenants) or a "soon" pill with ETA.
3. **Two-column row**:
   - Left (60%): **Tenant connections** table with name, ID, user count, sync status (dot + label), last refresh time, and a row action menu. Status dots colour-code state (synced/syncing/error/stale). Click a tenant row to navigate to that tenant's overview.
   - Right (40%): **Recent activity feed** as a flat list. Each entry has severity badge, title, tenant + module attribution line, and relative timestamp. Click to navigate to the finding detail.

### 2. SignalGuard tenant overview (Sprint 5b)

Per-tenant dashboard. Top row of 4 stat cards (critical, high, anomalies last 24h, policies analysed) with sparklines. Then a two-column split: CA Audit summary card (severity bar chart + top categories + link to findings) and Anomaly summary card (top 5 alerts as compact list). Below: coverage matrix preview (small heatmap, click to expand). Footer: data freshness panel with last sync, next scheduled sync, manual refresh.

### 3. CA Audit findings list (Sprint 5a target)

Two-column layout: main content + 240px right rail.

**Main**:

- Filter chip strip at top showing active filters with X to remove. "Clear all" link. "Add filter" button opens dropdown of filter dimensions.
- Findings table with columns: checkbox, severity badge, title + affected object, finding ID (mono), age, status, row actions menu.
- Row click toggles inline expansion. Expanded row shows:
  - Section: **Why this fired** (LLM narrative paragraph)
  - Section: **Affected objects** (structured list, copyable IDs in mono)
  - Section: **Evidence** (key-value table with collapsible JSON for nested values)
  - Section: **Remediation** (numbered steps, with copyable PowerShell snippets in code blocks)
  - Section: **References** (external links to MS docs, NCSC NZ, CIS)
  - Action bar at bottom of expansion: snooze, mark resolved, copy as JSON, open in Entra portal.

**Right rail**:

- **Summary** card: total findings, by-severity breakdown (with mini bars), filtered count.
- **Snoozed** count.
- **Bulk actions** card (visible when rows selected): snooze selected, mark resolved selected, export selected.

### 4. Coverage matrix (Sprint 5b)

Full-width heatmap grid. Rows = user segments, columns = app segments. Cells coloured by protection level using `cov-*` tokens. Each cell pairs colour with a tiny icon (lock, shield-check, half-shield, broken-shield) for accessibility. Cell click opens a side panel showing applicable policies, conditions, and what's missing. Top toolbar has: include disabled policies toggle, include report-only as protection toggle, app/user segment filters.

### 5. Sign-in anomaly feed (Sprint 5b)

Timeline list, newest first. Each row: avatar + user name, time (relative + exact on hover), location (country flag + city), device summary, anomaly score (0-100, severity-coded), top 3 SHAP feature chips. Filter rail above: user, severity threshold, time range segmented control, status. Bulk select for dismiss / escalate / mark known-good.

### 6. Sign-in anomaly drill-down (Sprint 5a target)

Two-column layout, 60/40 split.

**Left (60%)**: Full sign-in metadata table grouped into sections (identity, location, network, client, auth, outcome). Mono font for IDs, IPs, GUIDs, timestamps. Each row is a label (`fg-tertiary`) and value (`fg`). Some values have copy-to-clipboard affordance.

**Right (40%)**:

- **Location card** (top): country, city, ASN, with comparison to user's typical countries from history.
- **SHAP waterfall** (middle): horizontal bar chart. Each bar is one feature contribution. Bar colour follows direction (`crit` for "pushes anomalous", `neutral` for "pushes normal"). Sorted by absolute value descending. Use `recharts` for rendering.
- **User history strip** (bottom): horizontal scroll of last 30 sign-ins. Each is a small block, anomalies highlighted with severity colour.

Persistent action bar at the bottom: open in Entra portal, mark known-good, escalate, copy details as JSON, copy as PowerShell investigation snippet.

### 7. Tenant onboarding (Sprint 5b)

Multi-step wizard. Three steps: tenant ID input → cert generation → consent script + verification. Plain-English permission descriptions. Progress indicator across the top. Final success state is understated: confirmation, tenant ID, "go to overview" action.

### 8. Settings (Sprint 5b)

Tab structure: General, Auth & Permissions, Data & Sync, Notifications, Audit Rules, Anomaly Tuning, Integrations, API Keys. Two-column form layout: label + description on left, control on right.

## Empty states

```
┌──────────────────────────────┐
│  [icon, 24px, fg-tertiary]   │
│                              │
│  No findings above threshold │
│                              │
│  [primary action button]     │
└──────────────────────────────┘
```

Terse. Technical. One clear action. No illustrations.

## Loading states

Skeleton elements matching the layout. Width and height of the actual content. Animated with a subtle shimmer at 1.5s duration. Never use spinners on dashboards (spinners are acceptable on action buttons during request).

## Error boundaries

Plain panel with:

- Eyebrow: error type (e.g. "API request failed")
- Title: short summary
- Body: the RFC 7807 problem detail's `detail` field
- Mono block: correlation ID for support
- Action: retry button + "open docs" link

Never show raw stack traces in production UI.

## Density principles

- Working screens (findings, anomalies, signins) prefer density. 8-12px between rows is correct.
- Marketing-style screens (onboarding, settings) prefer breathing room. 24-48px between sections.
- Engineers reading data want to see more, not less. Don't add whitespace because "it looks cleaner". Less data on screen means more scrolling, more context-switching, more cognitive load.

## What success looks like

If a screen sits next to Linear, Stripe Dashboard, or Attio and feels at home, it's done. If it feels at home next to Salesforce, ServiceNow, or a 2018 enterprise SaaS dashboard, it's not done.
