"""Tests for data quality fixes (Step 2a, 2b, 2c from PLAN.md)."""

from pathlib import Path

import pytest

from cropsprices.parsers import parse_excel

FIXTURES = Path(__file__).parent / "fixtures"


class TestStripPusteSuffix:
    """Fix 3: Strip '(puste)' and '(różne)' variety suffixes from fruit products.

    Uses real file 17660 which has both 'Maliny' and 'Maliny (puste)' as
    separate products. They are the same thing — 'puste' is a placeholder
    for empty variety in the source spreadsheet.
    """

    def test_no_puste_in_products(self):
        """Product names should not contain '(puste)'."""
        data = parse_excel(
            str(FIXTURES / "fruit_puste.xlsx"),
            sheet_name="ceny hurt_owoc",
            is_fruit=True,
            skiprows=2,
        )
        products = {d["Product"] for d in data}
        puste_products = {p for p in products if "(puste)" in p}
        assert len(puste_products) == 0, f"Found products with (puste): {puste_products}"

    def test_no_rozne_in_products(self):
        """Product names should not contain '(różne)'."""
        data = parse_excel(
            str(FIXTURES / "fruit_puste.xlsx"),
            sheet_name="ceny hurt_owoc",
            is_fruit=True,
            skiprows=2,
        )
        products = {d["Product"] for d in data}
        rozne_products = {p for p in products if "(różne)" in p}
        assert len(rozne_products) == 0, f"Found products with (różne): {rozne_products}"

    def test_maliny_still_exists(self):
        """'Maliny' should still be present after stripping '(puste)'."""
        data = parse_excel(
            str(FIXTURES / "fruit_puste.xlsx"),
            sheet_name="ceny hurt_owoc",
            is_fruit=True,
            skiprows=2,
        )
        products = {d["Product"] for d in data}
        assert "Maliny" in products

    def test_real_variety_preserved(self):
        """Real varieties like 'Jabłka Boskoop' should not be stripped."""
        data = parse_excel(
            str(FIXTURES / "fruit_puste.xlsx"),
            sheet_name="ceny hurt_owoc",
            is_fruit=True,
            skiprows=2,
        )
        products = {d["Product"] for d in data}
        assert "Jabłka: Boskoop" in products
        assert "Jabłka: Gala" in products


class TestColumnShiftUnitBug:
    """Fix 2b: Fruit name appearing in Unit column (column shift bug).

    Uses real file 1452006 from March 2026 where 7 XLSX files have a
    column structure that causes the parser to read the next product's
    name as the Unit value.
    """

    def test_unit_is_not_fruit_name(self):
        """Unit should never be a fruit/vegetable name."""
        data = parse_excel(
            str(FIXTURES / "column_shift_fruits.xlsx"),
            sheet_name="HURT OWOC",
            is_fruit=True,
            skiprows=4,
        )
        known_fruits = {
            "Ananasy", "Arbuzy", "Banany", "Borówki amerykańskie",
            "Cytryny", "Grejpfruty", "Gruszki", "Maliny", "Mandarynki",
            "Nektarynki", "Pomarańcze", "Truskawki", "Winogrona", "Śliwki",
        }
        bad_rows = [
            d for d in data if d["Unit"] in known_fruits
        ]
        assert len(bad_rows) == 0, (
            f"Unit contains fruit names: {[(d['Product'], d['Unit']) for d in bad_rows[:5]]}"
        )

    def test_unit_values_are_valid(self):
        """Unit should be one of the known unit types."""
        valid_units = {"kg", "szt.", "szt", "pęczek", "l"}
        data = parse_excel(
            str(FIXTURES / "column_shift_fruits.xlsx"),
            sheet_name="HURT OWOC",
            is_fruit=True,
            skiprows=4,
        )
        bad_rows = [
            d for d in data if d["Unit"] not in valid_units
        ]
        assert len(bad_rows) == 0, (
            f"Invalid units: {[(d['Product'], d['Unit']) for d in bad_rows[:5]]}"
        )

    def test_gruszki_unit_is_kg(self):
        """Gruszki should have Unit='kg', not Unit='Gruszki'."""
        data = parse_excel(
            str(FIXTURES / "column_shift_fruits.xlsx"),
            sheet_name="HURT OWOC",
            is_fruit=True,
            skiprows=4,
        )
        gruszki = [d for d in data if d["Product"] == "Gruszki"]
        assert len(gruszki) > 0
        for d in gruszki:
            assert d["Unit"] == "kg", f"Gruszki Unit should be 'kg', got '{d['Unit']}'"
