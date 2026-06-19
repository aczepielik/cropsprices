---
name: benchmark
description: Profile dashboard load times, product-change latency, and per-stage bottlenecks using Playwright
---

# Dashboard Benchmark Skill

Measures actual browser-side performance of the cropsprices dashboard: initial load, product-change latency, and per-stage timing breakdown.

## Quick Start

```bash
# From the project root (starts dev server automatically):
node .agents/skills/benchmark/bench.mjs
```

Requires a running Vite dev server. The script starts one automatically if none is found on the target port.

## What It Measures

### Phase 1: Initial Load
- `navigationStart` → `networkidle` (HTTP + Vite transform + Arrow decode)
- `networkidle` → KPI data visible (JS derived cascade: `allWeeks`, `buildWeekSpreadMap`, `globalYRange`, chart SVG)
- Per-resource timing for each `.arrow` and `manifest.json` fetch (size + duration)

### Phase 2: Product Change
- `selectOption` dispatch → first KPI update with real data (no dash/empty)
- Counts intermediate re-renders (empty → data transition)
- Per-resource timing for new Arrow fetches

### Phase 3: Heatmap (optional)
- Switches to Heatmap tab, measures `aggregateByWeekYear` + SVG render

## Output Format

```
=== Initial Load ===
networkidle: 1260 ms
KPI data ready: 1786 ms
Resources:
  manifest.json: 16 ms (22.4 KB)
  Gruszki-kg-KRAJOWE.arrow: 14 ms (41.9 KB)

=== Product Change ===
selectOption dispatched: 178 ms
T+376ms: KPI=30.00 – 40.00 zł
=== RESOLVED in 376 ms ===
Arrow fetches:
  Borówki amerykańskie-kg-KRAJOWE.arrow: 18 ms (5.0 KB)
```

## Interpreting Results

| Metric | Healthy | Concerning |
|--------|---------|------------|
| Arrow decode (42KB archive) | < 30 ms | > 100 ms |
| Arrow decode (5KB current) | < 20 ms | > 50 ms |
| `allWeeks` (2500 records, 380 weeks) | < 15 ms | > 50 ms |
| `buildWeekSpreadMap` (2500 records) | < 10 ms | > 30 ms |
| Product change total | < 500 ms | > 2000 ms |
| Initial load total | < 3000 ms | > 5000 ms |

**If Arrow decode is fast but total is slow**: bottleneck is JS derived cascade or Svelte re-rendering, not data loading. Check for `records = []` clear-and-reload patterns.

**If Arrow decode is slow**: files may be too large (check with `ls -lh public/data/archive/`). Consider pre-aggregating in ETL.

## Architecture Notes

- Data files: `public/data/archive/*.arrow` (historical) + `public/data/{year}/*.arrow` (current year)
- Largest archive: ~50KB, ~2900 rows. Smallest: ~5KB, ~100 rows.
- Arrow files use dictionary-encoded strings for product/place/origin columns.
- Total data: 3.1MB across 181 archive + 181 current-year files.

## Prerequisites

- Node.js 18+
- Playwright with Chromium (`.tools/node_modules/playwright`)
- Vite dev server (auto-started if not running)
