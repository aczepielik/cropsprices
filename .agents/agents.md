1. Use GitFlow branching model
2. If the commit is fully authored by agent it should have agent as author. In mixes authorship agent's conribution should be mentioned
3. Update **Status** below after every change

## Status

### Phase 1 ✅ — Legacy Purge & Python Environment Setup
- Deleted: Dockerfile, cloudbuild*.yaml, deploy.sh, functions/, app/ (NiceGUI), pyproject.toml, poetry.lock
- Created: root `requirements.txt` with clean deps (requests, pydantic, pandas, openpyxl, pyyaml, tqdm)
- Rebuilt `.venv` with uv (Python 3.12 + 18 clean packages, no GCP/NiceGUI/Matplotlib)
- Updated `.gitignore` (added .venv/, frontend/node_modules/, frontend/dist/)

### Phase 2 🏗️ — Data Refactor & Scraper Update
- **Design doc:** `DataFlow.md` (supersedes `NewArchitecture.md`)
- **Strategy:** Monthly partitioning with dictionary-encoded strings, client-side heatmap aggregation
- **Reusable ETL core:** `cropsprices/` package (parsers.py, models.py, apiquery.py) — no GCP deps
- **Orchestration:** `scripts/etl/` (renamed from cloud_init) — decoupled from GCP
- **Done:**
    - Decoupled `bulk_get_resources.py` from GCP (outputs to local `data/raw/`)
    - Decoupled `bulk_process_resources.py` from GCP (outputs to `data/parsed/`)
    - Parser handles both old and new Excel formats (Phase 2a)
    - Manual overrides for 2 source-data-error files
- **Remaining:**
    - Implement `scripts/build_arrow_db.py` for monthly partitioned Arrow export
    - Update scraper for incremental `api.dane.gov.pl` fetches using manifest.json
    - Generate `manifest.json` and initial `.arrow` files into `public/data/`

### Phase 3 — Svelte TypeScript Frontend
- **Stack:** Vite + Svelte + TypeScript, Tailwind CSS, LayerCake, Apache Arrow JS
- **Data loading:** Snapshot (~8 monthly files, ~17KB) + Heatmap (~84 monthly files, ~168KB, client-side aggregation)
- **Caching:** IndexedDB with immutability awareness (DataFlow.md §5)
- **Next Steps:**
    - Initialize Vite + Svelte project
    - Implement Arrow data loading layer with lazy-loading
    - Build snapshot and heatmap views from `mocks/mock6.html` using LayerCake

### Phase 4 — UI Implementation & CI/CD
- **Hosting:** GitHub Pages or Cloudflare Pages (free static CDN)
- **Next Steps:**
    - Build dashboard UI matching mock6.html
    - Author GitHub Actions workflow for weekly ETL runs
    - Deploy to static hosting
