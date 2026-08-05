#!/usr/bin/env python3
"""Process all downloaded XLSX files into parsed CSVs."""

import logging

from cropsprices.processing_manager import ProcessingManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def main():
    manager = ProcessingManager()
    manager.process_xlsx_files()


if __name__ == "__main__":
    main()
