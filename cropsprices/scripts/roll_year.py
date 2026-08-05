#!/usr/bin/env python3
"""Roll the data pipeline to a new year.

Merges the current year's data into archive, creates a new year directory,
updates the manifest, and deletes the old year directory.

Usage:
    roll-year              # roll from current to next year
    roll-year --to 2028    # roll to a specific year
    roll-year --yes        # skip confirmation prompt
"""

import argparse
import json
import logging
import shutil
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
from cropsprices.scripts.build_arrow_db import detect_archive_year

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Roll the data pipeline to a new year")
    parser.add_argument(
        "--to",
        type=int,
        default=None,
        help="Target year (default: current year + 1)",
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompt",
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

    # Load and prepare data
    df = load_all_csvs(parsed_dir)
    df = normalize_dataframe(df)
    df = pivot_min_max(df)
    df["year"] = pd.to_datetime(df["Date"]).dt.year

    current_year = int(df["year"].max())
    new_year = args.to or (current_year + 1)
    old_archive_year = detect_archive_year(output_dir) or (current_year - 1)
    new_archive_year = new_year - 1

    # Preview what will happen
    logger.info(f"Year roll: {current_year} → {new_year}")
    logger.info(f"  Archive: archive-{old_archive_year}/ → archive-{new_archive_year}/")
    logger.info(f"  Current year dir: {current_year}/ → {new_year}/")
    logger.info(f"  Manifest: currentYear {current_year} → {new_year}, archiveYear {old_archive_year} → {new_archive_year}")

    # Confirm
    if not args.yes:
        response = input("\nProceed with year roll? [y/N] ").strip().lower()
        if response not in ("y", "yes"):
            logger.info("Aborted.")
            return

    # 1. Write new archive (includes data up to new_year - 1)
    logger.info(f"Writing archive-{new_archive_year}/ ...")
    archive_files = write_archive_files(df, output_dir, new_year, new_archive_year)

    # 2. Write new year directory
    logger.info(f"Writing {new_year}/ ...")
    current_files = write_current_year_files(df, output_dir, new_year)

    # 3. Write updated manifest
    manifest = build_manifest(df, archive_files, current_files, new_year, new_archive_year)
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    logger.info(f"Wrote manifest to {manifest_path}")

    # 4. Delete old year directory
    old_year_dir = output_dir / str(current_year)
    if old_year_dir.exists():
        logger.info(f"Deleting {old_year_dir}/ ...")
        shutil.rmtree(old_year_dir)
    else:
        logger.warning(f"Old year directory {old_year_dir}/ not found, skipping delete")

    # 5. Optionally delete old archive directory
    old_archive_dir = output_dir / f"archive-{old_archive_year}"
    if old_archive_dir.exists() and old_archive_year != new_archive_year:
        if args.yes:
            logger.info(f"Deleting {old_archive_dir}/ ...")
            shutil.rmtree(old_archive_dir)
        else:
            response = input(f"\nDelete old archive {old_archive_dir.name}/? [y/N] ").strip().lower()
            if response in ("y", "yes"):
                logger.info(f"Deleting {old_archive_dir}/ ...")
                shutil.rmtree(old_archive_dir)
            else:
                logger.info(f"Keeping {old_archive_dir}/")

    # Summary
    logger.info(f"\nYear roll complete:")
    logger.info(f"  Archive: archive-{new_archive_year}/ ({len(archive_files)} files)")
    logger.info(f"  Current: {new_year}/ ({len(current_files)} files)")
    logger.info(f"  Manifest: currentYear={new_year}, archiveYear={new_archive_year}")


if __name__ == "__main__":
    main()
