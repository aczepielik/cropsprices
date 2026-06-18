import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.ipc as ipc

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("build_arrow_db")

DEFAULT_PARSED_DIR = Path("data/parsed")
DEFAULT_OUTPUT_DIR = Path("public/data")


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

    if "Unit" in df.columns:
        unit_array = pa.array(df["Unit"], type=pa.dictionary(pa.int8(), pa.utf8()))
        arrays["unit"] = unit_array

    if "category" in df.columns:
        cat_array = pa.array(df["category"], type=pa.dictionary(pa.int8(), pa.utf8()))
        arrays["category"] = cat_array

    table = pa.table(arrays)
    return table


def sanitize_filename(name: str) -> str:
    return name.replace("/", "-").replace("\\", "-")


def write_monthly_files(df: pd.DataFrame, output_dir: Path) -> list[str]:
    df["year"] = pd.to_datetime(df["Date"]).dt.year
    df["month"] = pd.to_datetime(df["Date"]).dt.month

    group_keys = ["year", "month", "Date", "Product"]
    if "Unit" in df.columns:
        group_keys.append("Unit")
    group_keys.append("Origin")

    has_unit = "Unit" in group_keys
    files_written = []
    for key, group in df.groupby(group_keys):
        if not isinstance(key, tuple):
            key = (key,)

        key_map = dict(zip(group_keys, key))
        table = make_table(group)

        date_str = pd.to_datetime(key_map["Date"]).strftime("%Y-%m-%d")
        product_key = sanitize_filename(key_map["Product"])
        unit_key = sanitize_filename(key_map.get("Unit", "")) if has_unit else ""
        origin_key = sanitize_filename(key_map["Origin"])

        year_dir = output_dir / str(key_map["year"]) / f"{key_map['month']:02d}"
        year_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{date_str}-{product_key}-{unit_key}-{origin_key}.arrow"
        filepath = year_dir / filename

        sink = pa.BufferOutputStream()
        writer = ipc.new_file(sink, table.schema)
        writer.write_table(table)
        writer.close()
        filepath.write_bytes(sink.getvalue().to_pybytes())

        files_written.append(f"{key_map['year']}/{key_map['month']:02d}/{filename}")

    logger.info(f"Wrote {len(files_written)} monthly Arrow files")
    return files_written


def build_manifest(df: pd.DataFrame, files: list[str]) -> dict:
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
        "products": products_list,
        "places": sorted(df["Place"].unique().tolist()),
        "lastUpdate": datetime.now(timezone.utc).isoformat(),
    }
    return manifest


def main(parsed_dir: Path = DEFAULT_PARSED_DIR, output_dir: Path = DEFAULT_OUTPUT_DIR):
    output_dir.mkdir(parents=True, exist_ok=True)

    df = load_all_csvs(parsed_dir)
    df = pivot_min_max(df)
    df["year"] = pd.to_datetime(df["Date"]).dt.year

    files = write_monthly_files(df, output_dir)

    manifest = build_manifest(df, files)
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    logger.info(f"Wrote manifest to {manifest_path}")
    logger.info(f"Years: {manifest['years']}, Products: {len(manifest['products'])}, Places: {len(manifest['places'])}")


if __name__ == "__main__":
    main()
