# Manual Override Files

This directory contains manually corrected XLSX files that replace broken ones from the API.

## When to use

Use overrides when a source XLSX file has data quality issues that the parser cannot handle:
- Misplaced data (e.g., city names in date rows)
- Missing required columns
- Corrupted formatting

## How to use

1. Download the broken XLSX from `data/raw/`
2. Fix the issue manually in Excel/LibreOffice
3. Save the corrected file here as `{resource_id}.xlsx`
   - The resource ID is the numeric prefix in the filename (e.g., `1909262` from `1909262,rynek-owocow-i-warzyw-...`)
4. Commit this file to git (overrides ARE committed, unlike `data/raw/`)

## How it works

The `bulk_get_resources.py` script checks `data/overrides/` before downloading from the API. If an override exists for a resource ID, it uses the override instead of downloading.

## Current overrides

| Resource ID | Original Filename | Issue | Fixed |
|---|---|---|---|
| (none yet) | | | |
