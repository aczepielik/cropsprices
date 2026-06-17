# Rewrite Plan

## Cleanup Summary

### Deleted
- `cropsprices.egg-info/` — empty build artifact
- `.data/` — empty directory
- `.pytest_cache/` — test cache artifact
- `mocks/index.html` through `mocks/mock5.html` — intermediate mock iterations (mock6.html is authoritative)
- `mocks/Screenshot from 2026-06-17 *.png` — dev screenshots
- `scripts/export_bqtables_to_parquet.py` — old BQ→Parquet export
- `scripts/dev_db_views.sql`, `scripts/staging_db_views.sql` — old NiceGUI SQL views
- `scripts/bulk_process_resources_dry.py` — old dry-run script

### Relocated
- `node_modules/` → `.tools/node_modules/` — Playwright for agentic screenshot tooling, moved out of root

### Updated
- `.gitignore` — covers new artifacts (egg-info, pytest cache, tools, mock PNGs)
- `.agents/agents.md` — rewritten status referencing DataFlow.md as authoritative, corrected Phase 2 strategy

### Kept intact (reusable ETL core)
- `cropsprices/parsers.py` — Excel parsing logic, no GCP deps
- `cropsprices/models.py` — Pydantic models for api.dane.gov.pl responses
- `cropsprices/apiquery.py` — generic paged API client
- `scripts/cloud_init/bulk_get_resources.py` — API fetch + XLSX download (needs GCP decoupling)
- `scripts/cloud_init/bulk_process_resources.py` — Excel parse orchestration (needs GCP decoupling)
- `scripts/cloud_init/init_*.py` — BQ schema setup (reference only)

### Post-cleanup structure
```
cropsprices/
├── Architecture.md              # historical record
├── NewArchitecture.md           # superseded (first draft)
├── DataFlow.md                  # AUTHORITATIVE design doc
├── PLAN.md                      # this file
├── LICENSE
├── README.md
├── requirements.txt
├── .venv/
├── data/                        # ETL intermediate files (gitignored)
│   ├── raw/                     # Downloaded XLSX bulletins (gitignored)
│   └── parsed/                  # Intermediate DataFrames (gitignored)
├── cropsprices/                 # reusable ETL core
│   ├── __init__.py
│   ├── apiquery.py
│   ├── models.py
│   └── parsers.py
├── scripts/
│   ├── cloud_init/              # bulk fetch + parse orchestration (to be renamed)
│   │   ├── bulk_get_resources.py
│   │   ├── bulk_process_resources.py
│   │   ├── init_dataset.py
│   │   ├── init_prices_table.py
│   │   └── init_resources_table.py
│   └── build_arrow_db.py        # NEW (Phase 2)
├── public/
│   └── data/                    # FINAL Arrow output (committed per-branch)
│       ├── manifest.json
│       ├── lookups.arrow
│       ├── prices_*.arrow
│       └── weekly_prices_*.arrow
├── mocks/
│   └── mock6.html               # authoritative UI mock
├── tests/                       # existing tests for parsers
├── .agents/
│   ├── agents.md
│   ├── planning/
│   └── skills/
└── .tools/
    └── node_modules/            # Playwright for agentic tooling
```

### .gitignore rules
```gitignore
# ETL intermediates — never committed
data/raw/
data/parsed/

# public/data/ is the OUTPUT — committed per-branch by CI
# (not gitignored — that's the point)
```

---

## Phase 2: Data Refactor & Scraper Update

**Design doc:** `DataFlow.md` (supersedes `NewArchitecture.md`)
**Strategy:** Monthly partitioning + pre-aggregated weekly files (Option 2 from DataFlow.md §4.6)

### Step 1: Decouple bulk_get_resources.py from GCP

Remove BigQuery/GCS/SecretManager dependencies. Keep the core logic:
- `query_paged_api()` from `cropsprices/apiquery.py` — unchanged
- `Resource` validation from `cropsprices/models.py` — unchanged
- XLSX download from `api.dane.gov.pl` — keep, output to local filesystem

**New behavior:**
- Fetches resource metadata from API
- Validates with Pydantic models
- Downloads XLSX files to `data/raw/` (local directory)
- Writes a local manifest of downloaded files (JSON)

**Dependencies to remove:** `google-cloud-bigquery`, `google-cloud-storage`, `google-cloud-secret-manager`, `google-cloud-logging`

### Step 2: Decouple bulk_process_resources.py from GCP

Remove BigQuery insert logic. Keep the core logic:
- Sheet detection (`ceny hurt_warz`, `WK`, `ceny hurt_owoc`, `OK`)
- Skiprows retry loop (tries 0-4)
- `parse_excel()` from `cropsprices/parsers.py` — unchanged

**New behavior:**
- Reads XLSX from `data/raw/`
- Parses sheets into DataFrames
- Outputs structured data to `data/parsed/` as Parquet or CSV
- No BigQuery writes

**Dependencies to remove:** `google-cloud-bigquery`, `google-cloud-storage`, `google-cloud-secret-manager`, `google-cloud-logging`

### Step 3: Implement scripts/build_arrow_db.py

Takes parsed DataFrames and produces the partitioned Arrow files per DataFlow.md §4.6.

**Outputs into `public/data/`:**
- `manifest.json` — years, products, months, lastUpdate
- `lookups.arrow` — dictionary tables (products, places, origins)
- `prices_{YYYY}_{MM}_{product}.arrow` — raw monthly data (~504 files, ~2KB each)
- `weekly_prices_{YYYY}_{product}.arrow` — pre-aggregated weekly cells (~42 files, ~1KB each)

**Arrow columns per monthly file:**

| Column       | Type    | Meaning                                |
|--------------|---------|----------------------------------------|
| `date`       | Date64  | Observation date (YYYY-MM-DD)          |
| `product_id` | UInt16  | FK → lookups.products                  |
| `place_id`   | UInt16  | FK → lookups.places                    |
| `origin_id`  | UInt8   | FK → lookups.origins                   |
| `price_min`  | Float32 | Minimum wholesale price (zł/kg)       |
| `price_max`  | Float32 | Maximum wholesale price (zł/kg)       |

**Arrow columns per weekly pre-agg file:**

| Column       | Type    | Meaning                                |
|--------------|---------|----------------------------------------|
| `week`       | UInt8   | ISO week number (1-53)                 |
| `cellVal`    | Float32 | Average midprice across markets        |
| `ribbonMin`  | Float32 | Min price_min across markets           |
| `ribbonMax`  | Float32 | Max price_max across markets           |
| `ribbonAvg`  | Float32 | Average of min/max across markets      |

**Dependencies to add:** `pyarrow` (already in requirements via pandas, but explicit usage)

### Step 4: Incremental scraper

Reuses `apiquery.py` + `models.py` to:
1. Fetch latest resources from API
2. Compare against `manifest.json` to find missing months
3. Download only new XLSX files
4. Parse and generate only new monthly + weekly Arrow files
5. Update `manifest.json`

### Step 5: Generate initial dataset

Run full ETL pipeline:
1. `bulk_get_resources.py` (decoupled) → download all XLSX to `data/raw/`
2. `bulk_process_resources.py` (decoupled) → parse all XLSX to DataFrames
3. `build_arrow_db.py` → generate all Arrow files into `public/data/`

**Expected output:** ~546 files, ~1.04 MB total

---

## Phase 3: React TypeScript Frontend

### Step 1: Initialize Vite + React project

```
frontend/
├── package.json
├── tsconfig.json
├── vite.config.ts
├── index.html
├── public/
│   └── data/          # Arrow files copied here at build time
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── components/
│   ├── hooks/
│   ├── lib/
│   │   ├── arrow-loader.ts    # fetch + decode Arrow files
│   │   ├── cache.ts           # IndexedDB caching layer
│   │   ├── filters.ts         # filter chain logic
│   │   └── types.ts           # TypeScript types
│   └── styles/
│       └── globals.css        # Tailwind
└── tailwind.config.js
```

**Dependencies:**
- `vite`, `@vitejs/plugin-react`
- `react`, `react-dom`
- `apache-arrow` (Apache Arrow JS)
- `arquero` (optional, for data manipulation)
- `recharts` (charts)
- `tailwindcss`, `postcss`, `autoprefixer`

### Step 2: Data loading layer

Per DataFlow.md §4.6:

```typescript
// Snapshot view: ~8 monthly files, ~63 KB total
loadSnapshotView(product: string, date: string, windowWeeks: number)

// Heatmap view: 7 weekly pre-agg files, ~58 KB total
loadHeatmapView(product: string)

// IndexedDB caching with immutability awareness
fetchArrow(key: string, immutable: boolean): Promise<ArrayBuffer>
```

**Loading waterfall:**
```
Snapshot (first load):
  T+0ms     manifest.json (1 KB)
  T+10ms    lookups.arrow (50 KB)
  T+30ms    [parallel] 8 monthly files (16 KB)
  T+50ms    Snapshot renders (67 KB total)

Heatmap (warm cache):
  T+0ms     [parallel] 7 weekly files (7 KB) ← IndexedDB
  T+5ms     Heatmap renders (58 KB total)
```

### Step 3: IndexedDB caching

Per DataFlow.md §5:
- In-memory cache (React state) for currently viewed data
- IndexedDB for all loaded Arrow buffers (~1.1 MB max)
- HTTP cache headers for immutable past data (max-age=31536000)
- ETag validation for mutable current-year data

---

## Phase 4: UI Implementation & CI/CD

### Environments (Option A: Branch-based deploys)

| Environment | Trigger | URL | Data |
|---|---|---|---|
| **Dev** | `vite dev` locally | `localhost:5173` | `public/data/` generated locally, or mock |
| **Staging** | Push to any PR branch | `staging-<hash>.pages.dev` | Same Arrow files as prod |
| **Prod** | Merge to `main` | `cropsprices.pages.dev` | Full dataset |

**No data duplication** — staging uses the same Arrow files as prod. The only difference is code (UI features, bug fixes). Every PR gets its own preview URL automatically.

**Dev workflow:**
```
scripts/cloud_init/bulk_get_resources.py     # downloads XLSX to data/raw/
scripts/cloud_init/bulk_process_resources.py  # parses to data/parsed/
scripts/build_arrow_db.py                     # writes to public/data/
```
Raw XLSX files stay on disk for debugging. Never committed.

**CI workflow (staging/prod):**
```
1. Checkout branch
2. bulk_get_resources.py → data/raw/ (ephemeral)
3. bulk_process_resources.py → data/parsed/ (ephemeral)
4. build_arrow_db.py → public/data/
5. git add public/data/ && git commit -m "data: update dataset"
6. Deploy public/data/ to Pages
```
Raw + parsed are never committed — gone after the pipeline finishes.

### Step 1: Build dashboard from mock6.html

Two views:
1. **Snapshot (Widok Aktualny)** — KPI cards, context chart (±N weeks, 3 years), market breakdown table
2. **Heatmap (Mapa Cieplna)** — Week × Year grid with bottom/right marginals

**Design tokens from mock6.html:**
```css
--bg: #fcfcfb;
--surface: #ffffff;
--ink: #171511;
--muted: #6e6a61;
--rule: #d8d3ca;
--soft: #f3f1ed;
--pale: #f7f6f4;
--green: #396b51;
--rust: #a9683d;
--blue: #2c4f6e;
--missing: #b0a89c;
```

### Step 2: GitHub Actions workflow

```yaml
# .github/workflows/update-data.yml
on:
  schedule:
    - cron: '0 6 * * 1'  # Every Monday at 6 AM UTC
  workflow_dispatch:       # Manual trigger

jobs:
  update-data:
    runs-on: ubuntu-latest
    steps:
      - checkout
      - setup python 3.12
      - run bulk_get_resources.py (decoupled)
      - run bulk_process_resources.py (decoupled)
      - run build_arrow_db.py
      - git add public/data/ && git commit -m "data: update dataset"
      - deploy to GitHub Pages / Cloudflare Pages
```

**Why commit public/data/ instead of serving from CI artifact:**
- Cloudflare Pages serves from git — commit is the deploy trigger
- Cache headers on immutable files (past years) work correctly from git
- Every branch has its own data snapshot for review
- Rollback is just `git revert`

### Step 3: Deploy

- **Cloudflare Pages** (recommended): Free, fast global CDN, per-branch preview deploys, fine-grained cache headers
- **GitHub Pages:** Free, simple, GitHub-native, per-branch preview deploys
- Both serve static files with appropriate cache headers per DataFlow.md §5

---

## Key Design Decisions

1. **Monthly partitioning over yearly** — Snapshot context chart crosses year boundaries (Jan ±7 weeks needs Dec prev year). Monthly files give surgical access.
2. **Pre-aggregated weekly files** — Heatmap needs all years. 7 weekly files (~7 KB) vs 84 monthly files (~168 KB).
3. **Origin as product identity** — "Truskawki krajowe" and "Truskawki importowane" are separate product_ids, not a filterable column.
4. **IndexedDB caching** — ~95% of files are immutable after year closes. Cache forever with no revalidation.
5. **Playwright in .tools/** — Agentic screenshot tooling, not a project dependency.
6. **Branch-based deploys (Option A)** — No data duplication. Every PR gets a preview URL. Staging uses same Arrow files as prod.
7. **data/ gitignored, public/data/ committed** — Raw XLSX and parsed intermediates never leave dev machine. Only final Arrow output crosses git boundaries.
