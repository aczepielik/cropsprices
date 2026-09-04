# Manual Override Files

This directory contains manually corrected XLSX files that replace broken ones from the API.

## When to use

Use overrides when a source XLSX file has data quality issues that the parser cannot handle:
- Misplaced data (e.g., city names in date rows)
- Missing required columns
- Corrupted formatting
- Structural shifts (extra columns, duplicated data)

## How to use

1. Download the broken XLSX from `data/raw/` (old API) or the new API
2. Fix the issue manually in Excel/LibreOffice, or programmatically via openpyxl
3. Save the corrected file here as `{id}.xlsx`
   - Old API (dane.gov.pl): use the resource ID (numeric prefix in the filename)
   - New API (zsrir.minrol.gov.pl): use the API file `id` from the JSON response
     (NOT the bulletin week number from the filename — those repeat yearly)
4. Commit this file to git (overrides ARE committed, unlike `data/raw/`)

## How it works

Both the old pipeline (`bulk_get_resources.py`) and the CI pipeline (`ci_pipeline.py`)
check `data/overrides/` before downloading. If an override exists for a resource ID,
it uses the override instead of downloading.

## Current overrides

| ID | API | Issue | Fixed |
|---|---|---|---|
| 1807541 | dane.gov.pl | HURT OWOC sheet has shifted columns (cities at cols 8,10,12,14,16 instead of 5,7,9,11,13) and numeric date serials | Yes - shifted data left by 3 columns, converted date serials |
| 1909262 | dane.gov.pl | HURT OWOC sheet has Wrocław city data in wrong columns (cols 15-17) | Yes - removed Wrocław's malformed data |
| 5029 | zsrir.minrol.gov.pl | HURT OWOC sheet (bulletin 34/2026) has entire table shifted right by one column: duplicate product names in columns B and C, prices misaligned | Yes - removed duplicate column C, shifted data left, fixed Poznań extra column |
