1. Use GitFlow branching model
2. If the commit is fully authored by agent it should have agent as author. In mixes authorship agent's conribution should be mentioned
3. Update **Status** below after every change

## Status

### Phase 1 ✅ — Legacy Purge & Python Environment Setup
- Deleted: Dockerfile, cloudbuild*.yaml, deploy.sh, functions/, app/ (NiceGUI), pyproject.toml, poetry.lock
- Created: root `requirements.txt` with clean deps (requests, pydantic, pandas, openpyxl, pyyaml, tqdm)
- Rebuilt `.venv` with uv (Python 3.12 + 18 clean packages, no GCP/NiceGUI/Matplotlib)
- Updated `.gitignore` (added .venv/, frontend/node_modules/, frontend/dist/)

### Next: Phase 2 — Database Refactor & Scraper Update
