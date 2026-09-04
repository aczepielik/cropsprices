#!/usr/bin/env python3
"""Download all crop price resources from the API.

Uses the old dane.gov.pl API for historical data and the new
zsrir.minrol.gov.pl API for bulletin week 32 of 2026 onwards.
"""

import logging

from cropsprices.download_manager import DownloadManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def main():
    manager = DownloadManager()

    # Old API for historical data (bulletins before week 32, 2026)
    url = "https://api.dane.gov.pl/1.4/datasets/912,zintegrowany-system-rolniczej-informacji-rynkowej-biuletyny-informacyjne-rynek-owocow-i-warzyw-swiezych/resources"
    params = {"sort": "modified"}
    manager.process_resources(url, params)

    # New API for current data (bulletins from week 32, 2026 onwards)
    manager.process_new_api()


if __name__ == "__main__":
    main()
