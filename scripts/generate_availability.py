#!/usr/bin/env python3
"""Generate per-product availability CSVs.

For each (category, origin) folder, one CSV per product_name x unit.
Rows = ISO weeks (YYYY-Www), columns = markets.
Cell = "X" if data exists, empty otherwise.
"""

import json
import os
from datetime import date, timedelta
from pathlib import Path

import pyarrow.ipc as ipc

DATA_DIR = Path("public/data")
OUT_DIR = Path("data/availability")


def iso_week(d: date) -> tuple[int, int]:
    """Return (ISO year, ISO week) for a date."""
    # ISO week: Thursday-based. Week 1 contains Jan 4.
    ordinal = d.toordinal()
    jan4 = date(d.year, 1, 4)
    start_of_week1 = jan4 - timedelta(days=jan4.weekday())  # Monday of week 1
    week_num = (ordinal - start_of_week1.toordinal()) // 7 + 1
    # ISO year can differ from calendar year
    if week_num < 1:
        # Belongs to previous ISO year
        prev_jan4 = date(d.year - 1, 1, 4)
        prev_start = prev_jan4 - timedelta(days=prev_jan4.weekday())
        week_num = (ordinal - prev_start.toordinal()) // 7 + 1
        return d.year - 1, week_num
    elif week_num > 52:
        # Check if it belongs to next ISO year
        next_jan4 = date(d.year + 1, 1, 4)
        next_start = next_jan4 - timedelta(days=next_jan4.weekday())
        if ordinal >= next_start.toordinal():
            return d.year + 1, 1
    return d.year, week_num


def load_arrow(path: Path) -> list[dict]:
    """Load an Arrow file and return list of row dicts."""
    with open(path, "rb") as f:
        table = ipc.open_file(f).read_all()
    rows = []
    for i in range(len(table)):
        rows.append({
            "date": table.column("date")[i].as_py(),
            "place": table.column("place")[i].as_py(),
            "product": table.column("product")[i].as_py(),
            "unit": table.column("unit")[i].as_py(),
            "origin": table.column("origin")[i].as_py(),
            "category": table.column("category")[i].as_py(),
        })
    return rows


def build_availability(rows: list[dict]) -> dict:
    """Build { (iso_year, iso_week): { market: True/False } } from rows."""
    weeks: dict[tuple[int, int], set[str]] = {}
    for r in rows:
        d = r["date"]
        if isinstance(d, str):
            d = date.fromisoformat(d)
        yw = iso_week(d)
        market = r["place"]
        weeks.setdefault(yw, set()).add(market)
    return weeks


def write_csv(product_name: str, unit: str, origin: str, category: str,
              weeks: dict, markets: list[str]):
    """Write one CSV file for a product."""
    out_dir = OUT_DIR / category / origin
    out_dir.mkdir(parents=True, exist_ok=True)

    # Filename: product name with special chars replaced
    safe_name = product_name.replace("/", "-").replace(" ", "_").replace(":", "")
    filename = f"{safe_name}_{unit}.csv"
    filepath = out_dir / filename

    # Sort weeks chronologically
    sorted_weeks = sorted(weeks.keys())

    with open(filepath, "w") as f:
        # Header
        f.write("Week," + ",".join(markets) + "\n")
        for yw in sorted_weeks:
            label = f"{yw[0]}-W{yw[1]:02d}"
            present = weeks.get(yw, set())
            cells = ["X" if m in present else "" for m in markets]
            f.write(label + "," + ",".join(cells) + "\n")

    return filepath


def main():
    manifest = json.load(open(DATA_DIR / "manifest.json"))
    all_markets = sorted(manifest["places"])

    # Group products by (category, origin)
    product_groups: dict[tuple[str, str], list[dict]] = {}
    for p in manifest["products"]:
        key = (p["category"], p["origin"])
        product_groups.setdefault(key, []).append(p)

    total_files = 0
    total_empty = 0

    for (category, origin), products in sorted(product_groups.items()):
        print(f"\n{'='*60}")
        print(f"  {category} / {origin}  ({len(products)} products)")
        print(f"{'='*60}")

        for product in sorted(products, key=lambda p: p["name"]):
            name = product["name"]
            unit = product["unit"]

            # Load archive data
            archive_path = DATA_DIR / "archive" / f"{name}-{unit}-{origin}.arrow"
            current_path = DATA_DIR / "2026" / f"{name}-{unit}-{origin}.arrow"

            all_rows = []
            if archive_path.exists():
                all_rows.extend(load_arrow(archive_path))
            if current_path.exists():
                all_rows.extend(load_arrow(current_path))

            if not all_rows:
                print(f"  {name} ({unit}): NO DATA")
                filepath = write_csv(name, unit, origin, category, {}, all_markets)
                total_empty += 1
                total_files += 1
                continue

            weeks = build_availability(all_rows)
            filepath = write_csv(name, unit, origin, category, weeks, all_markets)
            n_weeks = len(weeks)
            print(f"  {name} ({unit}): {n_weeks} weeks → {filepath.name}")
            total_files += 1

    print(f"\n{'='*60}")
    print(f"  Done: {total_files} CSVs generated, {total_empty} products with no data")
    print(f"  Output: {OUT_DIR}/")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
