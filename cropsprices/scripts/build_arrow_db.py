#!/usr/bin/env python3
"""Rebuild the entire Arrow database and manifest from parsed CSVs."""

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


def detect_archive_year(output_dir: Path) -> int | None:
    """Find existing archive-{year} directory and return the year."""
    import re
    for d in output_dir.iterdir():
        if d.is_dir():
            m = re.match(r"archive-(\d{4})$", d.name)
            if m:
                return int(m.group(1))
    return None


def main(parsed_dir: Path = DEFAULT_PARSED_DIR, output_dir: Path = DEFAULT_OUTPUT_DIR):
    output_dir.mkdir(parents=True, exist_ok=True)

    df = load_all_csvs(parsed_dir)
    df = normalize_dataframe(df)
    df = pivot_min_max(df)
    df["year"] = pd.to_datetime(df["Date"]).dt.year

    current_year = int(df["year"].max())
    archive_year = detect_archive_year(output_dir) or (current_year - 1)
    logger.info(f"Current year: {current_year}, archive year: {archive_year}")

    archive_files = write_archive_files(df, output_dir, current_year, archive_year)
    current_files = write_current_year_files(df, output_dir, current_year)

    manifest = build_manifest(df, archive_files, current_files, current_year, archive_year)
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    logger.info(f"Wrote manifest to {manifest_path}")
    logger.info(f"Years: {manifest['years']}, Products: {len(manifest['products'])}, Places: {len(manifest['places'])}")
    logger.info(f"Archive: {len(archive_files)} files, Current: {len(current_files)} files, Total: {len(archive_files) + len(current_files)} files")


if __name__ == "__main__":
    main()
