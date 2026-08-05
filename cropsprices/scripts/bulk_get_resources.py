#!/usr/bin/env python3
"""Download all crop price resources from the API."""

import logging

from cropsprices.download_manager import DownloadManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def main():
    url = "https://api.dane.gov.pl/1.4/datasets/912,zintegrowany-system-rolniczej-informacji-rynkowej-biuletyny-informacyjne-rynek-owocow-i-warzyw-swiezych/resources"
    params = {"sort": "modified"}
    manager = DownloadManager()
    manager.process_resources(url, params)


if __name__ == "__main__":
    main()
