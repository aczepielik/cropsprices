#!/usr/bin/env python3
"""Update availability CSVs for specific products only.

Use --product to filter by product name (case-insensitive substring match).
"""

import argparse

from cropsprices.scripts.generate_availability import main as generate_main


def main():
    parser = argparse.ArgumentParser(description="Update availability CSVs for specific products")
    parser.add_argument(
        "--product",
        type=str,
        default=None,
        help="Filter by product name (case-insensitive substring match)",
    )
    args = parser.parse_args()

    generate_main(product_filter=args.product)


if __name__ == "__main__":
    main()
