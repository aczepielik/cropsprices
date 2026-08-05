#!/usr/bin/env python3
"""Process only new or modified XLSX files into parsed CSVs.

Skips files that already have a corresponding parsed CSV,
unless --force is used.
"""

import argparse
import logging
from pathlib import Path

from cropsprices.processing_manager import ProcessingManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Process new XLSX files into parsed CSVs")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reprocess all files even if parsed CSVs exist",
    )
    parser.add_argument(
        "--raw-dir",
        type=str,
        default="data/raw",
        help="Directory containing raw XLSX files (default: data/raw)",
    )
    parser.add_argument(
        "--parsed-dir",
        type=str,
        default="data/parsed",
        help="Directory for parsed CSV output (default: data/parsed)",
    )
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    parsed_dir = Path(args.parsed_dir)

    if args.force:
        logger.info("Force mode: processing all files")
        manager = ProcessingManager(raw_dir=str(raw_dir), parsed_dir=str(parsed_dir))
        manager.process_xlsx_files()
        return

    # Incremental: only process files without a matching parsed CSV
    xlsx_files = sorted(raw_dir.glob("*.xlsx"))
    logger.info(f"Found {len(xlsx_files)} XLSX files")

    new_files = []
    for xlsx in xlsx_files:
        # Check if both vegetable and fruit CSVs exist
        veg_csv = parsed_dir / f"{xlsx.stem}_vegetables.csv"
        fruit_csv = parsed_dir / f"{xlsx.stem}_fruits.csv"
        if not veg_csv.exists() or not fruit_csv.exists():
            new_files.append(xlsx)

    if not new_files:
        logger.info("No new files to process")
        return

    logger.info(f"Processing {len(new_files)} new files")
    manager = ProcessingManager(raw_dir=str(raw_dir), parsed_dir=str(parsed_dir))
    for filepath in new_files:
        manager._process_single_file(filepath)


if __name__ == "__main__":
    main()
