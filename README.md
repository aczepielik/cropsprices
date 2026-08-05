# Crops Prices Dashboard

Interactive dashboard tracking wholesale fruit and vegetable prices across 17 Polish wholesale markets. Data sourced from the Polish government open data portal ([api.dane.gov.pl](https://api.dane.gov.pl), dataset 912).

**Live site:** [aczepielik.github.io/cropsprices](https://aczepielik.github.io/cropsprices/)

---

## Architecture

```
api.dane.gov.pl                 GitHub Actions (every 12h)
      │                                │
      ▼                                ▼
  XLSX bulletins ──→ Python ETL ──→ Arrow IPC files ──→ GitHub Pages
                         │                │
                    data/raw/       public/data/
                   data/parsed/     manifest.json
                   (gitignored)     archive-YYYY/
                                    YYYY/
```

- **ETL pipeline** (`cropsprices/`) — Python package that queries the API, downloads XLSX bulletins, parses them, and writes Apache Arrow IPC files.
- **Frontend** (`frontend/`) — Svelte 5 single-page app that loads Arrow files in the browser and renders two views: Snapshot (KPIs + context chart) and Heatmap (week × year grid).
- **Deployment** — GitHub Actions runs the ETL on a 12-hour cron, commits updated data to `main`, which triggers a Vite build deployed to GitHub Pages.

---

## Data

### Source

The API publishes new "Rynek owoców i warzyw" bulletins every 5–8 days (not on a fixed weekly schedule). Each bulletin is an XLSX workbook with vegetable and fruit wholesale prices for 17 markets.

### Format

Arrow IPC files with dictionary-encoded columns:

| Column | Type | Description |
|---|---|---|
| `date` | Date32 | Observation date |
| `product` | dictionary | Product name (e.g. "Truskawki") |
| `place` | dictionary | Market name (e.g. "Bronisze") |
| `origin` | dictionary | KRAJOWE / IMPORTOWANE |
| `unit` | dictionary | kg, szt., pęczek, l |
| `category` | dictionary | warzywa / owoce |
| `price_min` | Float32 | Minimum wholesale price (zł) |
| `price_max` | Float32 | Maximum wholesale price (zł) |

### File layout

```
public/data/
├── manifest.json                    # Product index, years, markets
├── archive-YYYY/                    # All past years concatenated (immutable)
│   ├── Truskawki-kg-KRAJOWE.arrow
│   └── ...
└── YYYY/                            # Current year (updates weekly)
    ├── Truskawki-kg-KRAJOWE.arrow
    └── ...
```

**Scale:** ~147 products × 17 markets, ~231 files, ~5 MB total. Archive files change once per year (January rollover). Current-year files grow weekly.

### Data flow

The frontend fetches `manifest.json` (~2 KB), then loads two Arrow files per product selection (archive + current year, ~57 KB total). All filtering and aggregation happens client-side — no server queries, no IndexedDB.

---

## Project structure

```
cropsprices/                    # Python ETL package
├── scripts/                    # CLI entry points
│   ├── bulk_get_resources.py   # Download all XLSX from API
│   ├── get_resources.py        # Download only new XLSX
│   ├── bulk_process_resources.py  # Parse all XLSX to CSV
│   ├── process_resources.py    # Parse only new XLSX
│   ├── build_arrow_db.py       # Full Arrow rebuild
│   ├── update_arrow_db.py      # Current-year Arrow rebuild
│   └── roll_year.py            # January year rollover
├── apiquery.py                 # Paginated API client
├── models.py                   # Pydantic models for API responses
├── parsers.py                  # Excel workbook parser (multi-format)
├── download_manager.py         # XLSX download orchestration
├── processing_manager.py       # XLSX → CSV orchestration
├── arrow_db.py                 # Arrow IPC writer + manifest builder
├── product_normalize.py        # Product name/unit deduplication
└── ci_pipeline.py              # Production CI: API → download → merge → Arrow

frontend/                       # Svelte 5 + Vite + TypeScript
├── src/
│   ├── App.svelte              # Root: manifest load → filter state → view switching
│   ├── lib/
│   │   ├── arrow-loader.ts     # Fetch + decode Arrow IPC files
│   │   ├── types.ts            # TypeScript types (Manifest, PriceRecord, Filters)
│   │   ├── filters.ts          # Client-side data filtering/aggregation
│   │   └── helpers.ts          # Color scales, formatting, tick computation
│   └── components/
│       ├── Sidebar.svelte      # Tab nav (Snapshot / Heatmap)
│       ├── FilterZone.svelte   # Category → Origin → Product cascade + market checkboxes
│       ├── SnapshotView.svelte # KPI cards + context chart + market table
│       ├── SnapshotStats.svelte
│       ├── SnapshotTable.svelte
│       └── HeatmapView.svelte  # Week × Year SVG grid with color scale
├── package.json
└── vite.config.ts

public/data/                    # Arrow output (committed, served by frontend)
data/                           # ETL intermediates (mostly gitignored)
├── raw/                        # Downloaded XLSX (gitignored)
├── parsed/                     # Intermediate CSV (gitignored)
├── overrides/                  # Manual XLSX corrections (committed)
├── availability/               # Per-product availability matrices
└── .last-bulletin-id           # CI state marker (last processed bulletin)

.github/workflows/
├── etl.yml                     # Cron every 12h: check API → update Arrow → commit
└── deploy.yml                  # On push to main: test → build → deploy to Pages
```

---

## Development

### Prerequisites

- Python 3.12+ with [uv](https://docs.astral.sh/uv/)
- Node.js 22+

### Local setup

```bash
# Python dependencies
uv venv .venv
uv pip install -e .

# Frontend dependencies
cd frontend && npm install
```

### Running the ETL locally

```bash
# Download new XLSX bulletins
get-resources

# Parse new XLSX → CSV
process-resources

# Rebuild Arrow files for current year
update-arrow-db

# Full Arrow rebuild (all years)
build-arrow-db
```

### Running the frontend

```bash
cd frontend
npm run dev      # Dev server at localhost:5173
npm run build    # Production build to dist/
npm run test     # Run vitest tests
```

---

## CI/CD

### ETL workflow (`.github/workflows/etl.yml`)

Runs every 12 hours via cron, or manually via `workflow_dispatch`.

1. Queries API for latest bulletin
2. Compares with `data/.last-bulletin-id` — exits early if no new data
3. Downloads new XLSX to temp directory
4. Parses, normalizes, merges with existing current-year Arrow data
5. Writes updated Arrow files + manifest
6. Commits to `main` (triggers deploy)

### Deploy workflow (`.github/workflows/deploy.yml`)

Triggers on push to `main` when `frontend/**` or `public/data/**` change.

1. Runs frontend tests (`vitest`)
2. Builds with Vite (`vite build`)
3. Deploys to GitHub Pages via `actions/deploy-pages`

### GitHub setup (one-time)

- Repo Settings → Pages → Source: **"GitHub Actions"**

---

## CLI entry points

All registered in `pyproject.toml`:

| Command | Purpose |
|---|---|
| `bulk-get-resources` | Download all XLSX from API |
| `get-resources` | Download only new XLSX |
| `bulk-process-resources` | Parse all XLSX to CSV |
| `process-resources` | Parse only new XLSX |
| `build-arrow-db` | Full Arrow rebuild |
| `update-arrow-db` | Current-year Arrow rebuild |
| `generate-availability` | Generate availability matrices |
| `update-availability` | Update availability for specific products |
| `roll-year` | Annual year rollover merge |
| `ci-pipeline` | Production CI pipeline |

---

## Year rollover

On January 1st, run `roll-year` to:
1. Concatenate current year into archive
2. Create new year directory
3. Update `manifest.json`
4. Remove old year directory

Not yet automated in CI — manual step.

---

## Testing

```bash
# Python tests (parsers, arrow_db, product normalization)
.venv/bin/pytest tests/ -v

# Frontend tests (components, helpers, arrow loader)
cd frontend && npm test
```

---

## License

See [LICENSE](LICENSE).
