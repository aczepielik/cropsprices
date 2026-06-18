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
- `scripts/etl/bulk_get_resources.py` — API fetch + XLSX download (decoupled from GCP)
- `scripts/etl/bulk_process_resources.py` — Excel parse orchestration (decoupled from GCP)

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
│   ├── parsed/                  # Intermediate DataFrames (gitignored)
│   └── overrides/               # Manual XLSX fixes (committed)
├── cropsprices/                 # reusable ETL core
│   ├── __init__.py
│   ├── apiquery.py
│   ├── models.py
│   └── parsers.py
├── scripts/
│   ├── etl/                     # bulk fetch + parse orchestration
│   │   ├── bulk_get_resources.py
│   │   └── bulk_process_resources.py
│   └── build_arrow_db.py        # Arrow export (Phase 2)
├── public/
│   └── data/                    # FINAL Arrow output (committed per-branch)
│       ├── manifest.json
│       └── prices_*.arrow       # Monthly partitioned, dictionary-encoded
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
**Strategy:** Monthly partitioning with dictionary-encoded strings, client-side heatmap aggregation

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
- Sheet detection: handles both old and new naming conventions:
  - Vegetables: `ceny hurt_warz`, `HURT WARZ`, `WK`
  - Fruits: `ceny hurt_owoc`, `HURT OWOC`, `OK`
- Skiprows retry loop (tries 0-7, up from 0-4 to handle new format with extra header rows)
- `parse_excel()` from `cropsprices/parsers.py` — handles format variations

**New behavior:**
- Reads XLSX from `data/raw/`
- Parses sheets into DataFrames
- Outputs structured data to `data/parsed/` as CSV
- No BigQuery writes

**Dependencies to remove:** `google-cloud-bigquery`, `google-cloud-storage`, `google-cloud-secret-manager`, `google-cloud-logging`

### Step 2a: Data Quality Fixes

#### Fix 1: Product identity — unit and origin must be part of the product key

**Problem:** `build_arrow_db.py` groups by `Product` name alone. The same name can represent incomparable products:
- "Rzodkiewka, kg" vs "Rzodkiewka, pęczek" — different units, different prices
- "Gruszki" KRAJOWE vs "Gruszki" IMPORTOWANE — different origins, different price ranges
- The `Unit` column is currently dropped entirely in `pivot_min_max()` (`parsers.py:46-47`)

**Impact:** 33 products have both KRAJOWE and IMPORTOWANE rows. 30 products have multiple unit variants (kg, pęczek, szt., szt). These are all mixed into the same Arrow file under the same product name.

**Fix:** The product key for Arrow files must be a composite of `Product + Unit + Origin`. The CSV output must preserve all three fields. `build_arrow_db.py` must group by the composite key, not just Product. Each unique combination becomes a separate product identity in the dashboard (e.g., "Rzodkiewka kg KRAJOWE" and "Rzodkiewka pęczek KRAJOWE" are separate selectable items).

**Files to change:**
- `cropsprices/parsers.py` — stop dropping Unit in `pivot_min_max()`, or add it to the output
- `scripts/build_arrow_db.py` — group by (Product, Unit, Origin), include Unit in output schema
- Arrow schema: add `unit` column (dictionary-encoded)

#### Fix 2: Filtered dropdown — category and origin metadata missing

**Problem:** The sidebar filter chain (DataFlow.md §2) requires: category (warzywa/owoce), origin (krajowe/importowane), product, and market. Currently:
- **Category** — not stored anywhere after parsing. `bulk_process_resources.py` knows `is_fruit` when it calls the parser, but this info is discarded when writing CSVs.
- **Origin** — exists as a row-level column in Arrow files, but is not part of product identity (see Fix 1)
- **Product** — flat list of 138 names in `manifest.json`, no unit/category metadata
- **Markets** — available, 17 unique places

**Impact:** Cannot build the cascading filter UI (warzywa→owoce→krajowe→importowane→product) without knowing which products belong to which category.

**Fix:** Add `category` column to the CSV output in `bulk_process_resources.py`. Derive it from the sheet name: `ceny hurt_warz`/`HURT WARZ`/`WK` = `warzywa`, `ceny hurt_owoc`/`HURT OWOC`/`OK` = `owoce`. Include category in Arrow files and `manifest.json`. The manifest should expose a structured product list:

```json
{
  "products": [
    {"name": "Rzodkiewka", "unit": "kg", "origin": "KRAJOWE", "category": "warzywa"},
    {"name": "Rzodkiewka", "unit": "pęczek", "origin": "KRAJOWE", "category": "warzywa"},
    {"name": "Truskawki", "unit": "kg", "origin": "KRAJOWE", "category": "owoce"}
  ],
  "places": ["Białystok", "Bronisze", ...],
  "years": [2018, 2019, ...]
}
```

**Files to change:**
- `scripts/etl/bulk_process_resources.py` — pass `is_fruit` flag into CSV output
- `cropsprices/parsers.py` — include category in parsed output
- `scripts/build_arrow_db.py` — include category in Arrow schema and manifest
- `public/data/manifest.json` — structured product list with category/unit/origin

#### Fix 3: Strip "(puste)" and "(różne)" variety suffixes

**Problem:** The parser concatenates Product + Variety (`parsers.py:331-332`). When the source Excel has "(puste)" (Polish for "empty") in the variety column, it becomes "Maliny (puste)". But "Maliny (puste)" and "Maliny" are the same product — generic maliny with no specific variety. The "(puste)" suffix is noise from 12 specific older XLSX files.

Similarly, "(różne)" (Polish for "various") creates "Maliny (różne)" which is also just generic maliny.

**Impact:** 15 products have "(puste)" duplicates (e.g., "Ananasy" + "Ananasy (puste)", "Truskawki" + "Truskawki (puste)"). This inflates the product list and fragments data.

**Fix:** In `_process_fruit_data()` (`parsers.py:322-337`), strip "(puste)" and "(różne)" from the concatenated product name. After the `f"{Product} {Variety}"` join, remove these suffixes:

```python
product_name = f"{product} {variety}".strip()
product_name = product_name.replace(" (puste)", "").replace(" (różne)", "")
```

**Files to change:**
- `cropsprices/parsers.py` — `_process_fruit_data()` method

### Step 2b: Investigate — Fruit name appearing in Unit column (column shift bug)

**Root cause:** In 7 specific XLSX files, the fruit sheet has a column structure where the Unit ("Jedn.") column is shifted one position to the right. The parser reads the NEXT product's name as the Unit value.

**Example from file `1452006` (March 2026):**
```
Raw Excel row 23: | Banany |  | Arbuzy |  | kg | 6  | 8
Parser reads:      Product=Banany, Variety=Arbuzy, Unit=kg (correct)
But output shows:  Product=Banany, Unit=Arbuzy (wrong — Arbuzy is next product, not unit)
```

The parser's `_set_data_rows_columns()` detects the Unit column at index 4, but in these files the actual unit data is at index 5. Column 4 contains the next product name (from a duplicated product-name column in the source).

**Affected files (7 total, all fruits):**
- 1452006 — March 2026
- 1505470 — March 2026
- 1545573 — March-April 2026
- 1593417 — March-April 2026
- 1650995 — April 2026
- 59719 — July 2024
- 59793 — July 2024

**Impact:** 530 rows (0.3% of total) have fruit names as Unit values. The correct unit is always `kg` (except Jabłka Gala which shows "kk" — likely a typo for "kg"). The price data itself is still correct (Min/Max values are read from the right columns).

**Fix options:**
1. **Post-hoc correction in `build_arrow_db.py`**: If Unit is not in `{kg, szt., szt, pęczek, l}`, replace it with the correct unit from other files for the same product. Simple but fragile.
2. **Fix in parser**: After reading the sheet, validate that Unit values are real units. If not, try shifting the column index by 1 and re-reading. More robust.
3. **Override files**: Add corrected XLSX to `data/overrides/`. Correct but doesn't fix the parser for future occurrences.

**Recommendation:** Fix in parser (option 2). After `_set_data_rows_columns()`, validate the Unit column. If none of the values match known units (`kg`, `szt.`, `szt`, `pęczek`, `l`), try reading Unit from the next column index.

### Step 2c: Handle Source Data Format Changes

The upstream data source (`api.dane.gov.pl`) has changed format multiple times:
1. **Pre-2021**: `ceny hurt_warz`/`ceny hurt_owoc` sheets, product names in col 0
2. **2021-2025**: Same sheet names, same structure
3. **Nov 2025**: Title prefix changed to "Rynek owoców i warzyw", sheet names changed to `HURT WARZ`/`HURT OWOC`, product names moved to col 1, extra header rows added
4. **Future changes**: Inevitable — the source has changed format 3+ times

**Parser resilience:**
- `extract_dates_and_places()`: Counts Max/Min pairs from header row, fills missing place names with `Rynek{i}` placeholders
- `_set_data_rows_columns()`: Detects product column dynamically (not hardcoded to col 0), handles leading NaN columns and duplicate header columns
- `_swap_min_max_if_necessary()`: Uses `pd.to_numeric` for safe comparison across dtypes
- `ExcelData.validate_data()`: Strips whitespace, finds KRAJOWE/IMPORTOWANE in any column before start_col

**When CI/CD encounters an unparseable file:**
1. `bulk_process_resources.py` logs the error and continues to the next file
2. The parse failure is recorded in the manifest with the file ID and error message
3. A summary report is generated showing: total files processed, successes, failures, and failure reasons
4. **Escalation**: If any files fail to parse, the CI workflow:
   - Creates a GitHub Issue titled "ETL parse failure: {N} files failed" with the error log
   - Labels it `data-quality`
   - Does NOT block deployment (partial data is better than no data)
5. Manual intervention: Developer downloads the failing XLSX, inspects the format, updates the parser if needed, and re-runs

**Manual override mechanism:**
For files with source data errors (e.g., misplaced "Wrocław" in dates row), a manual override directory exists:

```
data/overrides/
├── README.md           # Instructions for manual overrides
└── {resource_id}.xlsx  # Corrected XLSX files that replace broken ones
```

The pipeline checks `data/overrides/` before downloading from the API. If an override exists for a resource ID, it uses the override instead of the downloaded file. Overrides are committed to git (unlike `data/raw/` which is gitignored).

### Step 3: Implement scripts/build_arrow_db.py

Takes parsed DataFrames and produces monthly partitioned Arrow files with dictionary-encoded strings.

**Outputs into `public/data/`:**
- `manifest.json` — years, products, lastUpdate
- `prices_{YYYY}_{MM}_{product}.arrow` — monthly data (~500+ files, ~2KB each)

**Arrow columns per monthly file:**

| Column      | Type              | Meaning                                |
|-------------|-------------------|----------------------------------------|
| `date`      | Date64            | Observation date (YYYY-MM-DD)          |
| `product`   | Utf8 (dictionary) | Product name                           |
| `place`     | Utf8 (dictionary) | Market name                            |
| `origin`    | Utf8 (dictionary) | KRAJOWE / IMPORTOWANE                  |
| `price_min` | Float32           | Minimum wholesale price (zł/kg)       |
| `price_max` | Float32           | Maximum wholesale price (zł/kg)       |

**No `lookups.arrow`** — dictionary encoding inline. Frontend extracts unique values from loaded data.
**No weekly pre-agg files** — frontend loads monthly files and aggregates heatmap cells client-side (enables market toggling).

**Dependencies to add:** `pyarrow>=17.0.0`

### Step 4: Incremental scraper

Reuses `apiquery.py` + `models.py` to:
1. Fetch latest resources from API
2. Compare against `manifest.json` to find missing months
3. Download only new XLSX files
4. Parse and generate only new monthly Arrow files
5. Update `manifest.json`

### Step 5: Generate initial dataset

Run full ETL pipeline:
1. `bulk_get_resources.py` (decoupled) → download all XLSX to `data/raw/`
2. `bulk_process_resources.py` (decoupled) → parse all XLSX to DataFrames
3. `build_arrow_db.py` → generate monthly Arrow files into `public/data/`

**Expected output:** ~500+ files, ~1 MB total

---

## Phase 3: Svelte TypeScript Frontend

### Step 1: Initialize Vite + Svelte project

```
frontend/
├── package.json
├── svelte.config.js
├── vite.config.ts
├── index.html
├── public/
│   └── data/          # Arrow files copied here at build time
├── src/
│   ├── main.ts
│   ├── App.svelte
│   ├── lib/
│   │   ├── arrow-loader.ts    # fetch + decode Arrow files
│   │   ├── cache.ts           # IndexedDB caching layer
│   │   ├── filters.ts         # filter chain logic
│   │   ├── helpers.ts         # heatColor, niceTicks, SVG path builders
│   │   └── types.ts           # TypeScript types
│   ├── components/
│   │   ├── Sidebar.svelte           # tab nav + filter controls
│   │   ├── FilterZone.svelte        # category, product, market checkboxes
│   │   ├── SnapshotView.svelte      # LayerCake container for snapshot
│   │   ├── HeatmapView.svelte       # LayerCake container for heatmap
│   │   ├── HeatmapCells.svelte      # rect grid with color scale
│   │   ├── ContextChart.svelte      # area polygons for 3-year context
│   │   ├── PriceRibbons.svelte      # bottom marginal ribbon paths
│   │   ├── YearBands.svelte         # right marginal year ranges
│   │   ├── KpiCards.svelte          # HTML KPI cards
│   │   └── MarketTable.svelte       # HTML market breakdown table
│   └── styles/
│       └── globals.css        # Tailwind
└── tailwind.config.js
```

**Dependencies:**
- `vite`, `@sveltejs/vite-plugin-svelte`
- `svelte` (v5)
- `layercake` (v10) — headless graphics framework for scale management
- `apache-arrow` (Apache Arrow JS)
- `d3-scale` — re-exported by LayerCake but useful directly for custom scales
- `tailwindcss`, `postcss`, `autoprefixer`

**Why LayerCake over Recharts / raw SVG:**
- Recharts is React-only and adds ~150 KB. The heatmap and context chart are custom SVG — Recharts can't render them.
- Raw SVG (mock6.html style) works but requires manual scale management, resize handling, and `niceTicks()` boilerplate. LayerCake eliminates all of that.
- LayerCake (~15 KB) provides: automatic scale computation from data extents, responsive container sizing, shared coordinate spaces across SVG layers, and helper functions (`bin`, `stack`, `groupLonger`).

### Step 2: Data loading layer

Per DataFlow.md:

```typescript
// Snapshot view: ~8 monthly files, ~16 KB total
loadSnapshotView(product: string, date: string, windowWeeks: number)

// Heatmap view: all monthly files for product, ~24 KB total
// Client aggregates by week×year, re-aggregates when markets toggle
loadHeatmapView(product: string)

// IndexedDB caching with immutability awareness
fetchArrow(key: string, immutable: boolean): Promise<ArrayBuffer>
```

**Loading waterfall:**
```
Snapshot (first load):
  T+0ms     manifest.json (1 KB)
  T+10ms    [parallel] 8 monthly files (16 KB)
  T+30ms    Snapshot renders (17 KB total)

Heatmap (first load):
  T+0ms     manifest.json (1 KB)           ← already cached
  T+10ms    [parallel] ~84 monthly files (168 KB)
  T+50ms    Client aggregates by week×year
  T+60ms    Heatmap renders
  Market toggle: re-filter + re-aggregate (no new fetch)
```

### Step 3: IndexedDB caching

Per DataFlow.md §5:
- In-memory cache (Svelte store) for currently viewed data
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
scripts/etl/bulk_get_resources.py        # downloads XLSX to data/raw/
scripts/etl/bulk_process_resources.py    # parses to data/parsed/
scripts/build_arrow_db.py                # writes to public/data/
```
Raw XLSX files stay on disk for debugging. Never committed.

**CI workflow (staging/prod):**
```
1. Checkout branch
2. Apply overrides: data/overrides/ → data/raw/ (manual fixes take priority)
3. bulk_get_resources.py → data/raw/ (skips files already in overrides)
4. bulk_process_resources.py → data/parsed/
   - Logs parse failures but does NOT fail the build
   - Generates parse_report.json with success/failure counts
5. build_arrow_db.py → public/data/
6. git add public/data/ && git commit -m "data: update dataset"
7. Deploy public/data/ to Pages
8. If parse_report.json has failures:
   - Create GitHub Issue "ETL parse failure: {N} files" with error details
   - Label: data-quality
   - Do NOT block deployment
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
2. **Client-side heatmap aggregation** — Market toggling requires re-aggregation. Loading all monthly files (~168 KB) is still fast; enables full interactivity matching mock6.html.
3. **Dictionary-encoded strings (no FK, no lookups.arrow)** — 68 products, 11 places, 2 origins are small enough for inline dictionary encoding. Simpler than FK + separate lookup tables.
4. **Origin as product identity** — "Truskawki krajowe" and "Truskawki importowane" are separate products, not a filterable column.
5. **IndexedDB caching** — ~95% of files are immutable after year closes. Cache forever with no revalidation.
6. **Playwright in .tools/** — Agentic screenshot tooling, not a project dependency.
7. **Branch-based deploys (Option A)** — No data duplication. Every PR gets a preview URL. Staging uses same Arrow files as prod.
8. **data/ gitignored, public/data/ committed** — Raw XLSX and parsed intermediates never leave dev machine. Only final Arrow output crosses git boundaries.
