# Screenshots and image assets

UI screenshots referenced from [docs/SCREENSHOTS.md](../SCREENSHOTS.md) and the
root [README.md](../../README.md). All images are checked into git; they are
documentation, not build output.

## Where they come from

Captured manually from the running dashboard at `localhost:3000` against fixture
data. There is no automated screenshot tooling. To recapture, follow the local
dev steps in the root README and:

```sh
uv run cstack fixtures load-all
uv run cstack audit all --tenant tenant-b
uv run cstack signins extract --tenant tenant-a --scenario replay-attacks
uv run cstack anomaly train --tenant tenant-a --lookback-days 365
uv run cstack anomaly promote --tenant tenant-a --force
uv run cstack anomaly score --tenant tenant-a
```

That seeds enough findings, anomalies, and SHAP attributions to cover the eight
hero screens.

## Naming convention

- kebab-case
- descriptive (what the screen shows, not what feature you were testing)
- `.png` extension

Examples: `home-overview.png`, `findings-expanded.png`, `coverage-matrix.png`.

## Resolution

- Capture at 1920x1200 or larger.
- Browser zoom 100 percent. Operating-system display scale 200 percent (retina /
  HiDPI). The committed PNGs render crisply on hi-DPI displays without
  sub-pixel scaling.

## When to recapture

- Any time the design changes meaningfully (new component, tonal shift, layout
  reflow, severity icon swap).
- After a fresh fixture corpus regen. Old screenshots drift quickly from current
  numbers.
- After a Tailwind 4 or Next.js major upgrade if rendering changes.

## Expected screenshots

The eight hero shots referenced from [SCREENSHOTS.md](../SCREENSHOTS.md):

- [ ] `home-overview.png`
- [ ] `signalguard-overview.png`
- [ ] `findings-list.png`
- [ ] `findings-expanded.png`
- [ ] `coverage-matrix.png`
- [ ] `anomaly-feed.png`
- [ ] `anomaly-drilldown.png`
- [ ] `settings-audit-rules.png`

Tick each box in this file when the corresponding PNG lands.
