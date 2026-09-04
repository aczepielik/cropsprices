"""Production CI pipeline: check API → download new XLSX → merge with Arrow → write.

Self-contained script for GitHub Actions. No intermediate files committed to repo.
Uses a temp directory for XLSX processing and a marker file for state tracking.
"""

import io
import json
import logging
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from cropsprices.apiquery import PagedAPIQuery
from cropsprices.arrow_db import (
    build_manifest,
    load_all_arrow,
    normalize_dataframe,
    pivot_min_max,
    write_current_year_files,
    write_manifest,
)
from cropsprices.models import Resource
from cropsprices.parsers import parse_excel
from cropsprices.product_normalize import normalize_product

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

API_URL = (
    "https://api.dane.gov.pl/1.4/datasets/912,"
    "zintegrowany-system-rolniczej-informacji-rynkowej-"
    "biuletyny-informacyjne-rynek-owocow-i-warzyw-swieych/resources"
)
VALID_PREFIXES = [
    "ceny hurtowe i targowiskowe",
    "Rynek owoców i warzyw",
]
PUBLIC_DATA_DIR = Path("public/data")
MARKER_PATH = Path("data/.last-bulletin-id")
OVERRIDES_DIR = Path("data/overrides")

VEG_SHEET_NAMES = ["ceny hurt_warz", "HURT WARZ", "WK"]
FRUIT_SHEET_NAMES = ["ceny hurt_owoc", "HURT OWOC", "OK"]


def read_marker() -> dict | None:
    if MARKER_PATH.exists():
        return json.loads(MARKER_PATH.read_text())
    return None


def write_marker(resource_id: str, title: str, modified: str) -> None:
    """Write marker file to track the last processed bulletin.

    ``resource_id`` is stored as-is and compared on the next run to decide
    whether new data is available.
    """
    MARKER_PATH.parent.mkdir(parents=True, exist_ok=True)
    MARKER_PATH.write_text(json.dumps({
        "id": resource_id,
        "title": title,
        "modified": modified,
    }, indent=2, ensure_ascii=False))


REPORT_FILE_LIST_URL = "https://zsrir.minrol.gov.pl/api/ZsrirData/GetReportFileList"
REPORT_DOWNLOAD_URL = "https://zsrir.minrol.gov.pl/api/ZsrirData/DownloadReportFile"
# Report ID 11 (fruit) and 12 (vegetable) share identical XLSX files.
ZSRIR_REPORT_ID = 11


def _fetch_report_files() -> list[dict]:
    """Fetch the raw file list from zsrir.minrol.gov.pl."""
    resp = requests.get(REPORT_FILE_LIST_URL, params={"id": ZSRIR_REPORT_ID},
                        timeout=30, headers={"Accept": "application/json"},
                        verify=False)
    resp.raise_for_status()
    return resp.json().get("reportFiles", [])


def _bulletin_from_file(file_info: dict) -> dict:
    """Transform a single API file entry into the dict shape main() expects.

    Uses the API's unique ``id`` (sequential, monotonically increasing)
    rather than the bulletin week number extracted from the filename,
    because week numbers repeat every year.
    """
    return {
        "id": str(file_info["id"]),
        "attributes": {
            "title": file_info["filename"],
            "modified": file_info["publishedDateTime"],
            "dateFrom": file_info.get("dateFrom", ""),
            "dateTo": file_info.get("dateTo", ""),
            "files": [{
                "format": "xlsx",
                "download_url": f"{REPORT_DOWNLOAD_URL}?id={file_info['id']}",
            }],
        },
    }


def fetch_latest_bulletins() -> list[dict]:
    """Fetch the most recent bulletin resources from zsrir.minrol.gov.pl."""
    files = _fetch_report_files()
    bulletins = [
        _bulletin_from_file(f) for f in files
        if f.get("filename", "").lower().endswith(".xlsx")
    ]
    bulletins.sort(key=lambda b: int(b["id"]), reverse=True)
    return bulletins


def download_xlsx(url: str, dest: Path) -> bool:
    """Download a single XLSX file. Returns True on success."""
    import requests
    try:
        resp = requests.get(url, timeout=60, verify=False)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        return True
    except Exception as e:
        logger.error(f"Download failed {url}: {e}")
        return False


def parse_xlsx_file(filepath: Path) -> pd.DataFrame | None:
    """Parse one XLSX file into a normalized, pivoted DataFrame."""
    raw = filepath.read_bytes()
    frames = []

    for sheet_names, is_fruit in [(VEG_SHEET_NAMES, False), (FRUIT_SHEET_NAMES, True)]:
        for skiprows in range(5):
            for name in sheet_names:
                try:
                    rows = parse_excel(io.BytesIO(raw), sheet_name=name,
                                       is_fruit=is_fruit, skiprows=skiprows)
                    if rows:
                        df = pd.DataFrame(rows)
                        df["category"] = "owoce" if is_fruit else "warzywa"
                        frames.append(df)
                        break
                except Exception:
                    continue
            else:
                continue
            break

    if not frames:
        return None

    combined = pd.concat(frames, ignore_index=True)
    combined = normalize_dataframe(combined)
    combined = pivot_min_max(combined)
    combined["Date"] = pd.to_datetime(combined["Date"])
    return combined


def detect_current_year(output_dir: Path) -> int:
    """Find the current year directory (not archive-*)."""
    import re
    for d in output_dir.iterdir():
        if d.is_dir() and not re.match(r"archive-\d{4}$", d.name):
            try:
                return int(d.name)
            except ValueError:
                continue
    return datetime.now().year


def main() -> None:
    logger.info("CI pipeline: checking for new bulletins")

    # 1. Query API
    bulletins = fetch_latest_bulletins()
    if not bulletins:
        logger.info("No relevant bulletins found in API response")
        sys.exit(0)

    latest = bulletins[0]
    latest_id = latest["id"]
    latest_title = latest["attributes"]["title"]
    latest_modified = latest["attributes"]["modified"]

    # 2. Check marker
    marker = read_marker()
    if marker and marker.get("id") == str(latest_id):
        logger.info(f"No new data (latest: {latest_title})")
        sys.exit(0)

    logger.info(f"New bulletin: {latest_title} (id={latest_id})")

    # 3. Download all new bulletins to temp dir
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        new_count = 0

        for res in bulletins:
            res_id = res["id"]
            # Skip if already processed (marker covers the latest; also check older).
            # Old markers use dane.gov.pl resource IDs (hundreds of thousands);
            # new markers use zsrir.minrol.gov.pl API file IDs (low thousands).
            # On first run the old id is larger than any new API id so nothing
            # would match — detect this by checking whether the marker id looks
            # like the old format.
            marker_id = int(marker.get("id", 0)) if marker else 0
            if marker and marker_id < 100_000 and int(res_id) <= marker_id:
                continue

            xlsx_files = [
                f for f in res["attributes"]["files"]
                if f["format"].lower() == "xlsx"
            ]
            for f in xlsx_files:
                dest = tmp / f"{res_id}.xlsx"
                override = OVERRIDES_DIR / f"{res_id}.xlsx"
                if override.exists():
                    import shutil
                    shutil.copy2(override, dest)
                    logger.info(f"Applied override for bulletin {res_id}")
                    new_count += 1
                elif download_xlsx(str(f["download_url"]), dest):
                    new_count += 1

        if new_count == 0:
            logger.info("No new XLSX files downloaded")
            sys.exit(0)

        logger.info(f"Downloaded {new_count} new XLSX files")

        # 4. Parse all new XLSX files
        new_dfs = []
        for xlsx in sorted(tmp.glob("*.xlsx")):
            df = parse_xlsx_file(xlsx)
            if df is not None and not df.empty:
                new_dfs.append(df)
                logger.info(f"Parsed {xlsx.name}: {len(df)} rows")
            else:
                logger.warning(f"Failed to parse {xlsx.name}")

        if not new_dfs:
            logger.error("No data parsed from new files")
            sys.exit(1)

        # 5. Load existing current-year Arrow data
        current_year = detect_current_year(PUBLIC_DATA_DIR)
        year_dir = PUBLIC_DATA_DIR / str(current_year)
        existing_frames = []
        if year_dir.exists():
            for arrow_file in sorted(year_dir.glob("*.arrow")):
                import pyarrow.ipc as ipc
                table = ipc.open_file(arrow_file).read_all()
                df = table.to_pandas()
                # Ensure required columns
                if "unit" not in df.columns:
                    df["unit"] = ""
                if "category" not in df.columns:
                    df["category"] = ""
                df = df.rename(columns={"date": "Date", "product": "Product",
                                         "place": "Place", "origin": "Origin",
                                         "unit": "Unit"})
                df["Date"] = pd.to_datetime(df["Date"])
                existing_frames.append(df)

        if existing_frames:
            existing_df = pd.concat(existing_frames, ignore_index=True)
            logger.info(f"Loaded {len(existing_df)} existing rows for {current_year}")
        else:
            existing_df = pd.DataFrame()
            logger.info(f"No existing data for {current_year}")

        # 6. Merge and deduplicate
        combined = pd.concat([existing_df] + new_dfs, ignore_index=True)
        dedup_cols = ["Date", "Product", "Place", "Origin"]
        before = len(combined)
        combined = combined.drop_duplicates(subset=dedup_cols, keep="last")
        logger.info(f"Merged: {before} → {len(combined)} rows (deduplicated)")

        # 7. Write updated current-year Arrow files
        combined["year"] = combined["Date"].dt.year
        write_current_year_files(combined, PUBLIC_DATA_DIR, current_year)

        # 8. Rebuild manifest from all data
        all_df = load_all_arrow(PUBLIC_DATA_DIR)
        all_df = normalize_dataframe(all_df)
        all_df["year"] = pd.to_datetime(all_df["Date"]).dt.year
        all_df["Date"] = pd.to_datetime(all_df["Date"])

        archive_year = current_year - 1
        manifest = build_manifest(
            all_df,
            archive_files=[],
            current_files=[],
            current_year=current_year,
            archive_year=archive_year,
        )
        write_manifest(manifest, PUBLIC_DATA_DIR)

    # 9. Update marker
    write_marker(latest_id, latest_title, latest_modified)
    logger.info(f"Done: merged {len(new_dfs)} datasets for {current_year}")


if __name__ == "__main__":
    main()
