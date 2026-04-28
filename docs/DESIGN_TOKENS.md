# Cstack design tokens

Light-first. Warm neutrals. Engineer-grade density. Single source of truth for visual decisions across cstack.

Reference points: Linear, Stripe, Attio.

## Surfaces

Warm light, never pure white as the page background. Pure white is reserved for elevated surfaces (cards, panels) so they feel raised against the warm page tone.

| Token            | Value     | Use                              |
| ---------------- | --------- | -------------------------------- |
| `bg`             | `#FAFAF9` | Page background, warm off-white  |
| `surface`        | `#FFFFFF` | Cards, panels, table rows        |
| `surface-subtle` | `#F4F4F2` | Subdued sections, expanded rows  |
| `surface-hover`  | `#F2F2F0` | Row and item hover state         |
| `surface-inset`  | `#F7F7F5` | Input wells, embedded selectors  |

## Borders

| Token             | Value     | Use                        |
| ----------------- | --------- | -------------------------- |
| `border`          | `#E8E8E6` | Primary hairline, default  |
| `border-strong`   | `#D8D8D5` | Hover affordance on cards  |
| `border-subtle`   | `#EFEFEC` | Internal table row dividers |

## Text

Four-step text scale. Use `fg` for primary content, `fg-secondary` for supporting copy, `fg-tertiary` for metadata and labels, `fg-quaternary` for disabled or placeholder.

| Token             | Value     |
| ----------------- | --------- |
| `fg`              | `#1A1A19` |
| `fg-secondary`    | `#525250` |
| `fg-tertiary`     | `#76766F` |
| `fg-quaternary`   | `#A3A39C` |

## Brand

Cstack indigo. The signature accent. Used sparingly: primary buttons, focus rings, active links, the "live" status indicator. Should appear on roughly 3 to 5 percent of any given screen.

| Token           | Value     |
| --------------- | --------- |
| `brand`         | `#4338CA` |
| `brand-hover`   | `#3730A3` |
| `brand-subtle`  | `#EEF0FF` |
| `brand-text`    | `#312E81` |

## Module accents

Each module has a secondary accent for context cues (sidebar active state, breadcrumb pill, module card border on hover). Never used outside of module context.

| Token         | Value     | Module             |
| ------------- | --------- | ------------------ |
| `sg`          | `#0F766E` | SignalGuard (teal) |
| `sg-subtle`   | `#E6F4F2` |                    |
| `sg-text`     | `#134E4A` |                    |

Future modules (LicenseLens `#7C3AED`, Driftwatch `#0E7490`, ChangeRadar `#9F1239`, CompliancePulse `#A16207`) will be added when their sprints land. Do not use these until then.

## Severity

Color paired with shape so the severity signal is colour-blind safe. Always render the shape next to the colour fill.

| Token       | Color     | Shape          |
| ----------- | --------- | -------------- |
| `crit`      | `#B91C1C` | Filled circle  |
| `crit-bg`   | `#FBE9E9` |                |
| `high`      | `#C2410C` | Filled triangle |
| `high-bg`   | `#FBEBE0` |                |
| `med`       | `#A16207` | Filled diamond |
| `med-bg`    | `#FAF1DD` |                |
| `low`       | `#1E40AF` | Filled square  |
| `low-bg`    | `#E6EAF7` |                |
| `info`      | `#525252` | Hollow circle  |
| `info-bg`   | `#ECECEA` |                |

## Status

Used for sync status, health indicators, validation states. Never for severity (severity has its own scale above).

| Token       | Value     | Use            |
| ----------- | --------- | -------------- |
| `ok`        | `#15803D` | Healthy, synced |
| `ok-bg`     | `#E5F2EA` |                |
| `warn`      | `#A16207` | Stale, attention needed |
| `err`       | `#B91C1C` | Failed, blocked |
| `neutral`   | `#A3A3A3` | Idle, inactive |

## Coverage matrix

Five-step protection scale for the heatmap. Always paired with an icon for accessibility.

| Token             | Value     | Meaning                |
| ----------------- | --------- | ---------------------- |
| `cov-strong`      | `#15803D` | MFA + compliant device |
| `cov-strong-bg`   | `#DDEEDF` |                        |
| `cov-good`        | `#5EA982` | MFA only               |
| `cov-good-bg`     | `#E6F0E5` |                        |
| `cov-amber`       | `#C2880C` | Compliant device only  |
| `cov-amber-bg`    | `#FAEFD0` |                        |
| `cov-weak`        | `#D97757` | Report-only            |
| `cov-weak-bg`     | `#FDE6DC` |                        |
| `cov-bad`         | `#B91C1C` | Unprotected            |
| `cov-bad-bg`      | `#FBE3E3` |                        |

## Typography

Inter for UI, JetBrains Mono for technical data. Loaded from Google Fonts. Both with `font-feature-settings: "cv11", "ss01"` for Inter and tabular nums for mono.

```
sans:  Inter, -apple-system, "Segoe UI", sans-serif
mono:  JetBrains Mono, ui-monospace, "SF Mono", Menlo, monospace
```

Base font size: **13px**. Engineers want density. Common sizes:

| Token   | Size  | Use                              |
| ------- | ----- | -------------------------------- |
| `t-12`  | 12px  | Eyebrow labels, microcopy        |
| `t-13`  | 13px  | Body, table content, default     |
| `t-14`  | 14px  | Section labels, sidebar items    |
| `t-16`  | 16px  | Card titles, callouts            |
| `t-18`  | 18px  | H3 within content                |
| `t-22`  | 22px  | Page titles                      |
| `t-28`  | 28px  | Hero stat numbers                |
| `t-36`  | 36px  | Onboarding wizard headlines      |

Weights: 400 (body), 500 (medium emphasis, labels, button text), 600 (headings). Never 700.

Tracking: `-0.012em` to `-0.018em` on headings. Inter looks shouty at default tracking past 20px.

Eyebrow labels (10.5px, weight 600, uppercase, letter-spacing 0.07em, `fg-tertiary`).

## Shape (border radius)

| Token   | Value | Use                          |
| ------- | ----- | ---------------------------- |
| `r-sm`  | 3px   | Pills, chips, small badges   |
| `r`     | 5px   | Buttons, inputs, default     |
| `r-md`  | 6px   | Cards, panels                |
| `r-lg`  | 8px   | Modal panels, popovers       |

## Shadow

Used sparingly. Borders before shadows. Shadows reserved for floating elements.

```
shadow-pop:    0 2px 8px rgba(15,15,20,0.04), 0 1px 2px rgba(15,15,20,0.04)
shadow-modal:  0 10px 40px rgba(15,15,20,0.08), 0 2px 8px rgba(15,15,20,0.04)
shadow-card:   0 1px 0 rgba(255,255,255,0.7) inset    /* gentle interior highlight */
```

No glows. No coloured shadows. No glassmorphism.

## Motion

| Token       | Value                              |
| ----------- | ---------------------------------- |
| `ease`      | `cubic-bezier(0.2, 0, 0, 1)`       |
| `dur-fast`  | 100ms                              |
| `dur`       | 150ms                              |

Fast transitions for hover and focus state changes (100ms). Slightly slower for layout shifts and panel transitions (150ms). Nothing longer. No bouncy springs. No staggered list animations.

## Iconography

`lucide-react` at stroke width 1.5. Never filled. Standard sizes: 12px (inside chips), 13px (table rows, sidebar), 14px (buttons), 16px (default content), 20px (section headers). Never larger than 24px in working screens.

A small set of fixed stroke widths matters: 1.5 for general use, 1.7 for sidebar module icons (slightly heavier reads more confident at small sizes).

## Spacing

4px base grid. Common multiples: 8, 12, 16, 24, 32, 48.

Working screens (tables, finding lists, dashboards) use **tight rhythm**: 8 to 12px between table rows, 16 to 24px between sections.

Marketing-style screens (onboarding, settings) use **generous rhythm**: 24 to 48px between sections.

## Focus ring

```
outline: 2px solid var(--brand);
outline-offset: 1px;
```

Always visible, never `outline: none` without a replacement. Same colour as the brand accent.

## Numerics

Always use `font-variant-numeric: tabular-nums` and `font-feature-settings: "tnum"` on numbers in tables, stats, timestamps, IDs. Aligns digits visually so columns of numbers read cleanly.

The `mono` class additionally applies the JetBrains Mono family for IDs, GUIDs, IP addresses, hashes, file paths.

## Tone of UI copy

Sentence case for everything. No Title Case. No exclamation marks. No emoji. Examples:

- `Last sync 14 min ago`, not `We last refreshed your data 14 minutes ago`
- `12 policies analysed across 247 users`, not `We've successfully analysed all of your conditional access policies`
- `No findings above threshold`, not `Great job! Your tenant looks healthy`
- `Cert with thumbprint X not found in CurrentUser\\My store`, not `Something went wrong, please try again`

## What's NOT in the design system

- Title case headings
- Bright saturated colours outside the palettes above
- Gradient backgrounds (the only gradient is the cstack wordmark logo tile)
- Decorative illustrations
- Stock photography
- Glassmorphism, neumorphism, glow effects
- Coloured borders (use color in fills, borders stay neutral)
- Multi-tone shadows
- Custom icon sets (lucide only)
- Emoji
- Marketing copy in product UI

## Applying tokens in Tailwind

The tokens above map directly into `tailwind.config.ts`. Sprint 5a's Phase 1 wires them in. Once wired, all UI code should reference `bg-surface`, `text-fg-secondary`, `border-border`, etc, never hex values inline. If you're reaching for a hex literal in a component, the token is missing or you're working outside the system.
