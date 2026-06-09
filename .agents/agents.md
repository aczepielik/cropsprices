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
- **Decision:** Pivot from SQLite to **Partitioned Apache Arrow** (Feather V2).
- **Rationale:** SQLite size (~20MB) is too heavy for Jamstack. Arrow + Arquero provides a <300KB initial payload with lazy-loading for immutable historical chunks.
- **Next Steps:**
    - Implement `scripts/build_arrow_db.py` for partitioned export.
    - Update scraper for incremental `api.dane.gov.pl` fetches.
    - Generate `manifest.json` and initial `.arrow` chunks.
