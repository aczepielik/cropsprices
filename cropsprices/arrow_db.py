import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.ipc as ipc

from cropsprices.product_normalize import normalize_product

logger = logging.getLogger(__name__)

DEFAULT_PARSED_DIR = Path("data/parsed")
DEFAULT_OUTPUT_DIR = Path("public/data")


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Apply normalize_product to Product and Unit columns."""
    if "Unit" in df.columns:
        normalized = df.apply(
            lambda row: normalize_product(row["Product"], row.get("Unit", "")),
            axis=1,
            result_type="expand",
        )
        df = df.copy()
        df["Product"] = normalized[0]
        df["Unit"] = normalized[1]
    else:
        df = df.copy()
        df["Product"] = df["Product"].str.strip()
    return df


def load_all_csvs(parsed_dir: Path) -> pd.DataFrame:
    csvs = sorted(parsed_dir.glob("*.csv"))
    logger.info(f"Loading {len(csvs)} CSV files from {parsed_dir}")

    if not csvs:
        return pd.DataFrame()

    frames = []
    for csv in csvs:
        df = pd.read_csv(csv)
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True)
    logger.info(f"Loaded {len(combined)} total rows")
    return combined


def pivot_min_max(df: pd.DataFrame) -> pd.DataFrame:
    max_rows = df[df["Statistic"] == "Max"].copy()
    min_rows = df[df["Statistic"] == "Min"].copy()

    max_rows = max_rows.rename(columns={"Price": "price_max"}).drop(columns=["Statistic"])
    min_rows = min_rows.rename(columns={"Price": "price_min"}).drop(columns=["Statistic"])

    merge_keys = ["Product", "Place", "Date", "Origin"]
    if "Unit" in max_rows.columns:
        merge_keys.append("Unit")
    if "category" in max_rows.columns:
        merge_keys.append("category")

    merged = max_rows.merge(
        min_rows,
        on=merge_keys,
        how="outer",
    )

    merged["price_min"] = pd.to_numeric(merged["price_min"], errors="coerce").astype("float32")
    merged["price_max"] = pd.to_numeric(merged["price_max"], errors="coerce").astype("float32")
    merged["Date"] = pd.to_datetime(merged["Date"])

    logger.info(f"After pivot: {len(merged)} rows")
    return merged


def make_table(df: pd.DataFrame) -> pa.Table:
    date_array = pa.array(df["Date"].dt.date, type=pa.date32())
    product_array = pa.array(df["Product"], type=pa.dictionary(pa.int8(), pa.utf8()))
    place_array = pa.array(df["Place"], type=pa.dictionary(pa.int8(), pa.utf8()))
    origin_array = pa.array(df["Origin"], type=pa.dictionary(pa.int8(), pa.utf8()))
    price_min_array = pa.array(df["price_min"], type=pa.float32())
    price_max_array = pa.array(df["price_max"], type=pa.float32())

    arrays = {
        "date": date_array,
        "product": product_array,
        "place": place_array,
        "origin": origin_array,
        "price_min": price_min_array,
        "price_max": price_max_array,
    }

    unit_values = df["Unit"] if "Unit" in df.columns else pd.Series([""] * len(df))
    unit_array = pa.array(unit_values, type=pa.dictionary(pa.int8(), pa.utf8()))
    arrays["unit"] = unit_array

    cat_values = df["category"] if "category" in df.columns else pd.Series([""] * len(df))
    cat_array = pa.array(cat_values, type=pa.dictionary(pa.int8(), pa.utf8()))
    arrays["category"] = cat_array

    table = pa.table(arrays)
    return table


def sanitize_filename(name: str) -> str:
    return name.replace("/", "-").replace("\\", "-")


def write_arrow_file(table: pa.Table, filepath: Path) -> None:
    sink = pa.BufferOutputStream()
    writer = ipc.new_file(sink, table.schema)
    writer.write_table(table)
    writer.close()
    filepath.write_bytes(sink.getvalue().to_pybytes())


def compute_week_ranges(group: pd.DataFrame) -> dict:
    """Pre-aggregate per-market, per-year, per-week min/max from raw records.

    Returns a nested dict: {market: {year: {week: {"min": float, "max": float}}}}.
    This is shipped alongside arrow files so the frontend can skip the O(n)
    buildWeekSpreadMap pass at runtime.
    """
    result = {}
    for _, row in group.iterrows():
        place = row["Place"]
        dt = row["Date"]
        year = int(dt.year) if hasattr(dt, "year") else int(pd.Timestamp(dt).year)
        # ISO week number
        week = int(pd.Timestamp(dt).isocalendar()[1])
        p_min = float(row["price_min"]) if pd.notna(row["price_min"]) else None
        p_max = float(row["price_max"]) if pd.notna(row["price_max"]) else None
        if p_min is None and p_max is None:
            continue

        market = result.setdefault(place, {})
        yr = market.setdefault(str(year), {})
        w = yr.setdefault(str(week), {"min": p_min or p_max, "max": p_max or p_min})
        if p_min is not None and p_min < w["min"]:
            w["min"] = p_min
        if p_max is not None and p_max > w["max"]:
            w["max"] = p_max
    return result


def write_weeks_file(week_ranges: dict, filepath: Path) -> None:
    """Write pre-aggregated week ranges as compact JSON."""
    filepath.write_text(json.dumps(week_ranges, separators=(",", ":")))


def write_archive_files(df: pd.DataFrame, output_dir: Path, current_year: int,
                        archive_year: int | None = None) -> list[str]:
    """Write archive arrow files for all years before current_year.

    Archive directory is named archive-{archive_year}/ where archive_year
    defaults to current_year - 1.  Each archive version is immutable —
    on year roll a new directory is created so the URL changes and
    browsers fetch fresh data.
    """
    if archive_year is None:
        archive_year = current_year - 1

    past_df = df[df["year"] < current_year]

    group_keys = ["Product"]
    if "Unit" in past_df.columns:
        group_keys.append("Unit")
    group_keys.append("Origin")

    has_unit = "Unit" in group_keys
    archive_dir = output_dir / f"archive-{archive_year}"
    archive_dir.mkdir(parents=True, exist_ok=True)

    files_written = []
    for key, group in past_df.groupby(group_keys):
        if not isinstance(key, tuple):
            key = (key,)

        key_map = dict(zip(group_keys, key))
        table = make_table(group)

        product_key = sanitize_filename(key_map["Product"])
        unit_key = sanitize_filename(key_map.get("Unit", "")) if has_unit else ""
        origin_key = sanitize_filename(key_map["Origin"])

        filename = f"{product_key}-{unit_key}-{origin_key}.arrow"
        filepath = archive_dir / filename
        write_arrow_file(table, filepath)
        files_written.append(f"archive-{archive_year}/{filename}")

        # Write pre-aggregated week ranges alongside the arrow file
        week_ranges = compute_week_ranges(group)
        weeks_filepath = archive_dir / f"{product_key}-{unit_key}-{origin_key}.weeks.json"
        write_weeks_file(week_ranges, weeks_filepath)

    logger.info(f"Wrote {len(files_written)} archive files to archive-{archive_year}/ (years < {current_year})")
    return files_written


def write_current_year_files(df: pd.DataFrame, output_dir: Path, current_year: int) -> list[str]:
    current_df = df[df["year"] == current_year]

    group_keys = ["Product"]
    if "Unit" in current_df.columns:
        group_keys.append("Unit")
    group_keys.append("Origin")

    has_unit = "Unit" in group_keys
    year_dir = output_dir / str(current_year)
    year_dir.mkdir(parents=True, exist_ok=True)

    files_written = []
    for key, group in current_df.groupby(group_keys):
        if not isinstance(key, tuple):
            key = (key,)

        key_map = dict(zip(group_keys, key))
        table = make_table(group)

        product_key = sanitize_filename(key_map["Product"])
        unit_key = sanitize_filename(key_map.get("Unit", "")) if has_unit else ""
        origin_key = sanitize_filename(key_map["Origin"])

        filename = f"{product_key}-{unit_key}-{origin_key}.arrow"
        filepath = year_dir / filename
        write_arrow_file(table, filepath)
        files_written.append(f"{current_year}/{filename}")

        # Write pre-aggregated week ranges alongside the arrow file
        week_ranges = compute_week_ranges(group)
        weeks_filepath = year_dir / f"{product_key}-{unit_key}-{origin_key}.weeks.json"
        write_weeks_file(week_ranges, weeks_filepath)

    logger.info(f"Wrote {len(files_written)} current-year files ({current_year})")
    return files_written


def load_all_arrow(output_dir: Path) -> pd.DataFrame:
    """Read all Arrow files from archive and current-year directories into one DataFrame."""
    frames = []
    for subdir in sorted(output_dir.iterdir()):
        if not subdir.is_dir():
            continue
        for arrow_file in sorted(subdir.glob("*.arrow")):
            table = pa.ipc.open_file(arrow_file).read_all()
            df = table.to_pandas()
            # Ensure required columns exist (archive files may lack unit/category)
            if "unit" not in df.columns:
                df["unit"] = ""
            if "category" not in df.columns:
                df["category"] = ""
            # Normalize column names to match CSV convention
            df = df.rename(columns={"date": "Date", "product": "Product",
                                     "place": "Place", "origin": "Origin",
                                     "unit": "Unit"})
            frames.append(df)
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True)
    logger.info(f"Loaded {len(combined)} rows from {len(frames)} Arrow files")
    return combined


def write_manifest(manifest: dict, output_dir: Path) -> None:
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    logger.info(f"Wrote manifest to {manifest_path}")


def build_manifest(df: pd.DataFrame, archive_files: list[str], current_files: list[str],
                    current_year: int, archive_year: int | None = None) -> dict:
    if archive_year is None:
        archive_year = current_year - 1

    years = sorted(df["year"].unique().tolist())

    product_cols = ["Product"]
    if "Unit" in df.columns:
        product_cols.append("Unit")
    product_cols.append("Origin")
    if "category" in df.columns:
        product_cols.append("category")

    products_df = df[product_cols].drop_duplicates().sort_values(product_cols).reset_index(drop=True)

    products_list = []
    for _, row in products_df.iterrows():
        entry = {"name": row["Product"], "unit": row.get("Unit", ""), "origin": row["Origin"]}
        entry["category"] = row.get("category", "")
        products_list.append(entry)

    manifest = {
        "years": [int(y) for y in years],
        "currentYear": current_year,
        "archiveYear": archive_year,
        "products": products_list,
        "places": sorted(df["Place"].unique().tolist()),
        "lastUpdate": datetime.now(timezone.utc).isoformat(),
    }
    return manifest
