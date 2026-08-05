#!/usr/bin/env python3
"""Update the Arrow database for a specific year only.

Defaults to the current year. Use --year to target a different year.
"""

import argparse
import json
import logging
from pathlib import Path

import pandas as pd

from cropsprices.arrow_db import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_PARSED_DIR,
    build_manifest,
    load_all_csvs,
    normalize_dataframe,
    pivot_min_max,
    write_archive_files,
    write_current_year_files,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Update Arrow database for a specific year")
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="Year to rebuild (default: current year from data)",
    )
    parser.add_argument(
        "--parsed-dir",
        type=str,
        default=str(DEFAULT_PARSED_DIR),
        help="Directory containing parsed CSVs",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(DEFAULT_OUTPUT_DIR),
        help="Output directory for Arrow files",
    )
    args = parser.parse_args()

    parsed_dir = Path(args.parsed_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = load_all_csvs(parsed_dir)
    df = normalize_dataframe(df)
    df = pivot_min_max(df)
    df["year"] = pd.to_datetime(df["Date"]).dt.year

    target_year = args.year or int(df["year"].max())
    logger.info(f"Updating year: {target_year}")

    # Only rebuild current year's files (archive is not touched)
    year_df = df[df["year"] == target_year]
    if year_df.empty:
        logger.warning(f"No data for year {target_year}")
        return

    current_files = write_current_year_files(year_df, output_dir, target_year)

    # Rebuild manifest with all data (needed for consistency)
    all_df = load_all_csvs(parsed_dir)
    all_df = normalize_dataframe(all_df)
    all_df = pivot_min_max(all_df)
    all_df["year"] = pd.to_datetime(all_df["Date"]).dt.year
    current_year = int(all_df["year"].max())

    archive_files = write_archive_files(all_df, output_dir, current_year)
    manifest = build_manifest(all_df, archive_files, current_files, current_year)
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    logger.info(f"Wrote manifest to {manifest_path}")


if __name__ == "__main__":
    main()
