import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.ipc as ipc

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("build_arrow_db")

PARSED_DIR = Path("data/parsed")
OUTPUT_DIR = Path("public/data")


def load_all_csvs() -> pd.DataFrame:
    csvs = sorted(PARSED_DIR.glob("*.csv"))
    logger.info(f"Loading {len(csvs)} CSV files from {PARSED_DIR}")

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

    max_rows = max_rows.rename(columns={"Price": "price_max"}).drop(columns=["Statistic", "Unit"])
    min_rows = min_rows.rename(columns={"Price": "price_min"}).drop(columns=["Statistic", "Unit"])

    merged = max_rows.merge(
        min_rows,
        on=["Product", "Place", "Date", "Origin"],
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

    table = pa.table({
        "date": date_array,
        "product": product_array,
        "place": place_array,
        "origin": origin_array,
        "price_min": price_min_array,
        "price_max": price_max_array,
    })
    return table


def sanitize_filename(name: str) -> str:
    return name.replace("/", "-").replace("\\", "-")


def write_monthly_files(df: pd.DataFrame) -> list[str]:
    df["year"] = pd.to_datetime(df["Date"]).dt.year
    df["month"] = pd.to_datetime(df["Date"]).dt.month

    files_written = []
    for (year, month, product), group in df.groupby(["year", "month", "Product"]):
        table = make_table(group)
        product_key = sanitize_filename(product)
        filename = f"prices_{year}_{month:02d}_{product_key}.arrow"
        filepath = OUTPUT_DIR / filename

        sink = pa.BufferOutputStream()
        writer = ipc.new_file(sink, table.schema)
        writer.write_table(table)
        writer.close()
        filepath.write_bytes(sink.getvalue().to_pybytes())

        files_written.append(filename)

    logger.info(f"Wrote {len(files_written)} monthly Arrow files")
    return files_written


def build_manifest(df: pd.DataFrame, files: list[str]) -> dict:
    years = sorted(df["year"].unique().tolist())
    products = sorted(df["Product"].unique().tolist())

    manifest = {
        "years": [int(y) for y in years],
        "products": products,
        "lastUpdate": datetime.now(timezone.utc).isoformat(),
    }
    return manifest


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = load_all_csvs()
    df = pivot_min_max(df)
    df["year"] = pd.to_datetime(df["Date"]).dt.year

    files = write_monthly_files(df)

    manifest = build_manifest(df, files)
    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    logger.info(f"Wrote manifest to {manifest_path}")
    logger.info(f"Years: {manifest['years']}, Products: {len(manifest['products'])}")


if __name__ == "__main__":
    main()
