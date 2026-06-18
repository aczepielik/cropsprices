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
- `cropsprices/bulk_get_resources.py` — API fetch + XLSX download (decoupled from GCP)
- `cropsprices/bulk_process_resources.py` — Excel parse orchestration (decoupled from GCP)
- `cropsprices/build_arrow_db.py` — Arrow export (Phase 2)

### Post-cleanup structure
```
cropsprices/
├── Architecture.md              # historical record
├── NewArchitecture.md           # superseded (first draft)
├── DataFlow.md                  # AUTHORITATIVE design doc
├── PLAN.md                      # this file
├── LICENSE
├── README.md
├── pyproject.toml               # package config with entry points
├── requirements.txt
├── .venv/
├── data/                        # ETL intermediate files (gitignored)
│   ├── raw/                     # Downloaded XLSX bulletins (gitignored)
│   ├── parsed/                  # Intermediate DataFrames (gitignored)
│   └── overrides/               # Manual XLSX fixes (committed)
├── cropsprices/                 # reusable ETL core + scripts
│   ├── __init__.py
│   ├── apiquery.py
│   ├── models.py
│   ├── parsers.py
│   ├── bulk_get_resources.py    # entry point: bulk-get-resources
│   ├── bulk_process_resources.py # entry point: bulk-process-resources
│   └── build_arrow_db.py        # entry point: build-arrow-db
├── frontend/                    # Svelte + TypeScript dashboard
│   ├── src/
│   │   ├── App.svelte           # Root component
│   │   ├── lib/                 # Data loading, filters, helpers, types
│   │   └── components/          # Sidebar, FilterZone, SnapshotView, HeatmapView
│   └── ...
├── public/
│   └── data/                    # FINAL Arrow output (committed per-branch)
│       ├── manifest.json        # Structured product list, years, places
│       ├── archive/             # Past years: 181 flat files, 2.5 MB
│       └── 2026/                # Current year: 87 files, 504 KB
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

## Known Bugs (discovered 2026-06-18) ✅ ALL FIXED

These bugs persisted despite being discussed in earlier sessions. Root cause: **context rot** — the conversation grew long enough that earlier decisions and fixes were not carried through to implementation.

### Bug A: (puste) still in manifest.json ✅

**Root cause:** The puste-stripping fix in `parsers.py` only affects *new* parsing runs. The existing CSVs in `data/parsed/` were generated before the fix and still contain "(puste)". `build_arrow_db.py` reads stale CSVs, so `manifest.json` inherits stale product names (12 products like "Ananasy (puste)").

**Fix:** Re-ran full ETL pipeline. Verified: 0 products with puste/różne in manifest.

### Bug B: Manifest has flat product list instead of 4 structured lists ✅

**Root cause:** `build_arrow_db.py:118` builds `products` as `sorted(df["Product"].unique())` — a flat list of 138 strings. The dashboard needs four separate filter lists (owoce/krajowe, owoce/importowane, warzywa/krajowe, warzywa/importowane) as described in DataFlow.md §2.

**Fix:** `build_arrow_db.py` now uses `Unit` and `Origin` columns to produce structured product metadata. Verified: manifest has 186 structured products with name/unit/origin/category.

### Bug C: Scripts duplicated in `scripts/` and `cropsprices/` ✅

**Root cause:** The refactor moved scripts into `cropsprices/` as package modules with entry points, but the old `scripts/` copies were never deleted. The stale copies in `scripts/etl/` and `scripts/build_arrow_db.py` diverged from the canonical `cropsprices/` versions.

**Fix:** Deleted `scripts/` directory entirely. The `cropsprices/` versions are canonical (referenced by `pyproject.toml` entry points).

---

## Phase 2: Data Refactor & Scraper Update ✅

**Design doc:** `DataFlow.md` (supersedes `NewArchitecture.md`)
**Strategy:** Archive flat files (past years) + current-yearly files, frontend heatmap aggregation

### Step 1: Decouple bulk_get_resources.py from GCP ✅

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

### Step 2: Decouple bulk_process_resources.py from GCP ✅

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

### Step 2a: Data Quality Fixes ✅

#### Fix 1: Product identity — unit and origin must be part of the product key

**Problem:** `build_arrow_db.py` groups by `Product` name alone. The same name can represent incomparable products:
- "Rzodkiewka, kg" vs "Rzodkiewka, pęczek" — different units, different prices
- "Gruszki" KRAJOWE vs "Gruszki" IMPORTOWANE — different origins, different price ranges
- The `Unit` column is currently dropped entirely in `pivot_min_max()` (`parsers.py:46-47`)

**Impact:** 33 products have both KRAJOWE and IMPORTOWANE rows. 30 products have multiple unit variants (kg, pęczek, szt., szt). These are all mixed into the same Arrow file under the same product name.

**Fix:** The product key for Arrow files must be a composite of `Product + Unit + Origin`. The CSV output must preserve all three fields. `build_arrow_db.py` must group by the composite key, not just Product. Each unique combination becomes a separate product identity in the dashboard (e.g., "Rzodkiewka kg KRAJOWE" and "Rzodkiewka pęczek KRAJOWE" are separate selectable items).

**Files to change:**
- `cropsprices/parsers.py` — stop dropping Unit in `pivot_min_max()`, or add it to the output
- `cropsprices/build_arrow_db.py` — group by (Product, Unit, Origin), include Unit in output schema
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
  "years": [2018, 2019, ...],
  "currentYear": 2026
}
```

**Files to change:**
- `cropsprices/bulk_process_resources.py` — pass `is_fruit` flag into CSV output
- `cropsprices/parsers.py` — include category in parsed output
- `cropsprices/build_arrow_db.py` — include category in Arrow schema and manifest
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

### Step 2b: Investigate — Fruit name appearing in Unit column (column shift bug) ✅

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

### Step 2c: Handle Source Data Format Changes ✅

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

### Step 3: Implement build_arrow_db.py ✅

Takes parsed DataFrames and produces Arrow files with dictionary-encoded strings.

**Output structure (268 files, 5.3 MB total):**

```
public/data/
├── manifest.json
├── archive/                              # ~181 files, ~4.2 MB
│   ├── Truskawki-kg-KRAJOWE.arrow        # All past years concatenated (~46 KB)
│   └── ...
└── 2026/                                 # ~87 files, ~1.1 MB
    ├── Truskawki-kg-KRAJOWE.arrow        # Current year only (~9 KB)
    └── ...
```

**Two tiers:**
- **Archive** (`archive/*.arrow`): One flat file per product, all past years concatenated. Changes once per year (January 1st merge). Cached as immutable.
- **Current year** (`{YYYY}/*.arrow`): One file per product, current year only. Grows weekly as new observations arrive. Re-validated via ETag.

**Arrow columns:**

| Column | Type | Meaning |
|---|---|---|
| `date` | Date32 | Observation date |
| `product` | Utf8 (dictionary) | Product name |
| `place` | Utf8 (dictionary) | Market name |
| `origin` | Utf8 (dictionary) | KRAJOWE / IMPORTOWANE |
| `price_min` | Float32 | Minimum wholesale price (zł/kg) |
| `price_max` | Float32 | Maximum wholesale price (zł/kg) |

**No `lookups.arrow`** — dictionary encoding inline. Frontend extracts unique values from loaded data.
**No pre-aggregated files** — frontend loads raw Arrow files and aggregates heatmap cells client-side (enables market toggling).
**No compression** — files average 5 KB, compression overhead exceeds savings.

**Dependencies to add:** `pyarrow>=17.0.0`

### Step 4: Incremental scraper (future enhancement)

Reuses `apiquery.py` + `models.py` to:
1. Fetch latest resources from API
2. Compare against `manifest.json` to find missing months
3. Download only new XLSX files
4. Parse and generate only new Arrow files
5. Update `manifest.json`

### Step 5: Generate initial dataset ✅

Run full ETL pipeline:
1. `bulk_get_resources.py` (decoupled) → download all XLSX to `data/raw/`
2. `bulk_process_resources.py` (decoupled) → parse all XLSX to DataFrames
3. `build_arrow_db.py` → generate Arrow files into `public/data/`

**Actual output:** 268 files, 3.4 MB total (archive: 181 files/2.5 MB, current: 87 files/504 KB)

---

## Phase 3: Svelte TypeScript Frontend ✅

### Step 1: Initialize Vite + Svelte project ✅

```
frontend/
├── package.json              # Vite 8 + Svelte 5 + Tailwind 4 + Apache Arrow + LayerCake
├── svelte.config.js
├── vite.config.ts            # Tailwind v4 + Svelte plugins
├── index.html                # Polish lang, Inter font
├── README.md
├── public/
│   ├── favicon.svg
│   └── icons.svg
├── src/
│   ├── main.ts
│   ├── app.css               # CSS custom properties (design tokens from mock6.html)
│   ├── App.svelte            # Root: manifest load → filter state → view switching
│   ├── lib/
│   │   ├── arrow-loader.ts   # fetch + decode Arrow files (tableFromIPC named import)
│   │   ├── filters.ts        # filterByMarkets, filterByDate, aggregateByDate/WeekYear
│   │   ├── helpers.ts        # heatColor, niceTicks, formatPrice, formatDate
│   │   └── types.ts          # Manifest, PriceRecord, Filters, ViewMode, etc.
│   └── components/
│       ├── Sidebar.svelte         # Tab nav: Snapshot / Heatmap
│       ├── FilterZone.svelte      # Category → Origin → Product cascade + market checkboxes
│       ├── SnapshotView.svelte    # KPI cards + market breakdown table
│       └── HeatmapView.svelte     # Week × Year SVG grid with color scale
└── tailwind.config.js
```

**Dependencies:**
- `vite` (v8), `@sveltejs/vite-plugin-svelte` (v7)
- `svelte` (v5) — runes reactivity ($state, $derived, $bindable)
- `layercake` (v10) — headless graphics framework for scale management
- `apache-arrow` (v21) — Arrow IPC file decoding (tableFromIPC named import)
- `tailwindcss` (v4), `postcss`, `autoprefixer`
- `typescript` (v6), `svelte-check`

**Why LayerCake over Recharts / raw SVG:**
- Recharts is React-only and adds ~150 KB. The heatmap and context chart are custom SVG — Recharts can't render them.
- Raw SVG (mock6.html style) works but requires manual scale management, resize handling, and `niceTicks()` boilerplate. LayerCake eliminates all of that.
- LayerCake (~15 KB) provides: automatic scale computation from data extents, responsive container sizing, shared coordinate spaces across SVG layers, and helper functions (`bin`, `stack`, `groupLonger`).

**Code style:** All frontend code includes beginner-oriented comments explaining *why*, not just *what* (see `.agents/agents.md` rule 4). Comments are stripped during production minification.

### Step 2: Data loading layer ✅

Implemented in `src/lib/arrow-loader.ts`:

```typescript
// Named import — only tableFromIPC from apache-arrow
import { tableFromIPC } from 'apache-arrow';

// Cache manifest (fetched once per page load)
loadManifest(): Promise<Manifest>

// Load archive + current-year files in parallel
loadProductData(name, unit, origin, currentYear): Promise<PriceRecord[]>
```

**Filter cascade** (FilterZone.svelte):
1. **Kategoria** — Owoce / Warzywa (category)
2. **Pochodzenie** — Krajowe / Importowane (origin)
3. **Produkt** — filtered by category + origin

**Loading waterfall:**
```
First load:
  T+0ms     manifest.json (~2 KB)
  T+10ms    [parallel] archive (~46 KB) + current-year (~9 KB)
  T+50ms    Snapshot/Heatmap renders (~57 KB total)

Market toggle:
  T+0ms     Re-filter loaded data (0 KB)
  T+2ms     Re-renders
```

### Step 3: HTTP caching (no IndexedDB)

At 57 KB total load, HTTP cache is sufficient. No IndexedDB.

**Cache headers:**
```yaml
archive/*.arrow:
  Cache-Control: public, max-age=31536000, immutable

{YYYY}/*.arrow:
  Cache-Control: no-cache
  ETag: "<hash>"

manifest.json:
  Cache-Control: no-cache
  ETag: "<hash>"
```

**Archive immutability note:** Archive files change once per year (January 1st merge). With `immutable` headers, stale for ~1 day after merge — acceptable for crop prices. If unacceptable, use `max-age=25920000` (300 days).

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
python -m cropsprices.bulk_get_resources        # downloads XLSX to data/raw/
python -m cropsprices.bulk_process_resources    # parses to data/parsed/
python -m cropsprices.build_arrow_db            # writes to public/data/
```
Raw XLSX files stay on disk for debugging. Never committed.

**CI workflow (staging/prod):**
```
1. Checkout branch
2. Apply overrides: data/overrides/ → data/raw/ (manual fixes take priority)
3. python -m cropsprices.bulk_get_resources → data/raw/ (skips files already in overrides)
4. python -m cropsprices.bulk_process_resources → data/parsed/
   - Logs parse failures but does NOT fail the build
   - Generates parse_report.json with success/failure counts
5. python -m cropsprices.build_arrow_db → public/data/
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
- Cache headers on immutable files (archive) work correctly from git
- Every branch has its own data snapshot for review
- Rollback is just `git revert`

### Step 3: Deploy

- **Cloudflare Pages** (recommended): Free, fast global CDN, per-branch preview deploys, fine-grained cache headers
- **GitHub Pages:** Free, simple, GitHub-native, per-branch preview deploys
- Both serve static files with appropriate cache headers per DataFlow.md §5

---

## Key Design Decisions

1. **Archive flat + current-yearly** — Past years concatenated into one flat file per product (immutable, forever cache). Current year is a separate file that grows weekly (mutable, ETag-validated). 268 files total, 5.3 MB.
2. **Client-side heatmap aggregation** — Market toggling requires re-aggregation. Loading 2 files (~57 KB) is trivial; enables full interactivity matching mock6.html.
3. **Dictionary-encoded strings (no FK, no lookups.arrow)** — 186 products, 17 places, 2 origins are small enough for inline dictionary encoding. Simpler than FK + separate lookup tables.
4. **Origin as product identity** — "Truskawki krajowe" and "Truskawki importowane" are separate products, not a filterable column.
5. **No IndexedDB** — At 57 KB total load, HTTP cache (immutable for archive, ETag for current year) is sufficient. Saves ~100 lines of cache management code.
6. **No compression** — Files average 5 KB. Compression overhead exceeds savings. Gzip/brotli on transport gets to ~3-4 MB.
7. **Playwright in .tools/** — Agentic screenshot tooling, not a project dependency.
8. **Branch-based deploys (Option A)** — No data duplication. Every PR gets a preview URL. Staging uses same Arrow files as prod.
9. **data/ gitignored, public/data/ committed** — Raw XLSX and parsed intermediates never leave dev machine. Only final Arrow output crosses git boundaries.
