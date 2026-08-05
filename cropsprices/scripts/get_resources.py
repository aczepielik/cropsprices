#!/usr/bin/env python3
"""Download only new crop price resources from the API.

Filters resources by modified date to skip already-downloaded ones.
"""

import argparse
import logging
from datetime import datetime, timezone

from cropsprices.download_manager import DownloadManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Download new resources from the API")
    parser.add_argument(
        "--since",
        type=str,
        default=None,
        help="Only download resources modified after this date (YYYY-MM-DD)",
    )
    args = parser.parse_args()

    url = "https://api.dane.gov.pl/1.4/datasets/912,zintegrowany-system-rolniczej-informacji-rynkowej-biuletyny-informacyjne-rynek-owocow-i-warzyw-swiezych/resources"
    params = {"sort": "modified"}

    if args.since:
        since_date = datetime.strptime(args.since, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        logger.info(f"Filtering resources modified since {since_date.date()}")
        # TODO: implement API-level date filtering when field format is known
        # For now, download all and filter locally
        params["fq"] = f"modified:[{args.since}T00:00:00Z TO *]"

    manager = DownloadManager()
    manager.process_resources(url, params)


if __name__ == "__main__":
    main()
