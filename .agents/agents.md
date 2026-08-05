1. Use GitFlow branching model
2. If the commit is fully authored by agent it should have agent as author. In mixes authorship agent's contribution should be mentioned
3. Update **Status** below after every change
4. **Beginner-oriented comments in frontend code.** The user is learning web development. All new frontend code (`.svelte`, `.ts` in `frontend/`) should include educational comments that explain *why*, not just *what*. Cover concepts like reactive state, component lifecycle, data flow patterns, and library-specific APIs. Comments are stripped during production minification so there is zero cost.

## Status

### All phases complete

- **ETL:** Python package (`cropsprices/`) with CLI entry points. Queries api.dane.gov.pl, downloads XLSX, parses to CSV, builds Arrow IPC files.
- **Frontend:** Svelte 5 + Vite + TypeScript + Tailwind CSS + LayerCake + Apache Arrow JS. Two views: Snapshot (KPIs + context chart) and Heatmap (week × year grid).
- **CI/CD:** GitHub Actions — ETL cron every 12h + deploy on push to main. Deployed to GitHub Pages.
- **Data:** ~147 products × 17 markets, ~231 Arrow files, ~5 MB. Archive tier (immutable) + current-year tier (weekly updates).
