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
- **Strategy:** Monthly partitioning + pre-aggregated weekly files (Option 2 from DataFlow.md §4.6)
- **Reusable ETL core:** `cropsprices/` package (parsers.py, models.py, apiquery.py) — no GCP deps
- **Orchestration:** `scripts/cloud_init/` — needs decoupling from BigQuery/GCS, keep API fetch + parse logic
- **Next Steps:**
    - Decouple `bulk_get_resources.py` from GCP (remove BigQuery/GCS writes, output to local FS)
    - Decouple `bulk_process_resources.py` from GCP (remove BigQuery inserts, output to DataFrame)
    - Implement `scripts/build_arrow_db.py` for monthly + weekly partitioned Arrow export
    - Update scraper for incremental `api.dane.gov.pl` fetches using manifest.json
    - Generate `manifest.json`, `lookups.arrow`, and initial `.arrow` chunks into `public/data/`

### Phase 3 — React TypeScript Frontend
- **Stack:** Vite + React + TypeScript, Tailwind CSS, Recharts, Apache Arrow JS, Arquero
- **Data loading:** Snapshot (~8 monthly files, ~63KB) + Heatmap (~7 weekly pre-agg files, ~58KB)
- **Caching:** IndexedDB with immutability awareness (DataFlow.md §5)
- **Next Steps:**
    - Initialize Vite + React project
    - Implement Arrow/Arquero data loading layer with lazy-loading
    - Build snapshot and heatmap views from `mocks/mock6.html`

### Phase 4 — UI Implementation & CI/CD
- **Hosting:** GitHub Pages or Cloudflare Pages (free static CDN)
- **Next Steps:**
    - Build dashboard UI matching mock6.html
    - Author GitHub Actions workflow for weekly ETL runs
    - Deploy to static hosting
