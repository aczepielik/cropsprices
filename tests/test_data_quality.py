"""Tests for data quality fixes (Step 2a, 2b, 2c from PLAN.md)."""

from pathlib import Path

import pytest

from cropsprices.parsers import parse_excel, VALID_UNITS

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
        data = parse_excel(
            str(FIXTURES / "column_shift_fruits.xlsx"),
            sheet_name="HURT OWOC",
            is_fruit=True,
            skiprows=4,
        )
        bad_rows = [
            d for d in data if d["Unit"] not in VALID_UNITS
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


class TestStructuralShiftRejection:
    """Bulletin 34 HURT OWOC has entire table shifted right by one column.

    Both columns B and C contain the same product names. The parser picks
    column B as product_col, but price data is aligned with column C.
    Result: variety names end up in the Unit column.

    The _validate_units heuristic rejects this when <50% of non-empty
    Unit values are valid units.
    """

    def test_bulletin34_fruit_rejected(self):
        """Bulletin 34 HURT OWOC must be rejected (structural shift)."""
        with pytest.raises(ValueError, match="Structural shift"):
            parse_excel(
                str(FIXTURES / "column_shift_fruits_new.xlsx"),
                sheet_name="HURT OWOC",
                is_fruit=True,
                skiprows=4,
            )

    def test_bulletin34_vegetable_ok(self):
        """Bulletin 34 HURT WARZ is structurally correct and should parse."""
        data = parse_excel(
            str(FIXTURES / "column_shift_fruits_new.xlsx"),
            sheet_name="HURT WARZ",
            is_fruit=False,
            skiprows=4,
        )
        assert len(data) > 100
        products = {d["Product"] for d in data}
        assert "Marchew" in products


class TestDuplicateRowRemoval:
    """Bulletin 33 HURT OWOC has duplicate rows at the bottom (rows 51-54
    duplicate rows 49-50). The parser should deduplicate automatically.
    """

    def test_no_exact_duplicates(self):
        """Parsed data should have no exact duplicate rows."""
        data = parse_excel(
            str(FIXTURES / "duplicate_rows.xlsx"),
            sheet_name="HURT OWOC",
            is_fruit=True,
            skiprows=4,
        )
        seen = set()
        for r in data:
            key = (r["Product"], r["Unit"], r["Place"], r["Date"],
                   r["Statistic"], r["Price"], r["Origin"])
            assert key not in seen, f"Duplicate row found: {key}"
            seen.add(key)

    def test_winogrona_appears_reasonable_count(self):
        """Winogrona should not appear more times than markets × stats."""
        data = parse_excel(
            str(FIXTURES / "duplicate_rows.xlsx"),
            sheet_name="HURT OWOC",
            is_fruit=True,
            skiprows=4,
        )
        winogrona = [d for d in data if d["Product"] == "Winogrona"]
        # 5 markets × 2 stats (Min/Max) = 10 max, minus missing data
        assert len(winogrona) <= 15, (
            f"Winogrona appears {len(winogrona)} times — likely duplicates remain"
        )


class TestShiftedDuplicateHandling:
    """Bulletin 35 HURT OWOC has row 43 as a shifted duplicate of row 42.

    The duplicate has 'kg' in a price column which used to cause a hard
    validation error. Now ExcelData coerces it to NaN, and clean_result_df
    drops the resulting rows.
    """

    def test_bulletin35_parses_successfully(self):
        """Bulletin 35 HURT OWOC should parse without errors."""
        data = parse_excel(
            str(FIXTURES / "shifted_duplicate.xlsx"),
            sheet_name="HURT OWOC",
            is_fruit=True,
            skiprows=4,
        )
        assert len(data) > 50

    def test_no_invalid_units(self):
        """All unit values should be valid after parsing."""
        data = parse_excel(
            str(FIXTURES / "shifted_duplicate.xlsx"),
            sheet_name="HURT OWOC",
            is_fruit=True,
            skiprows=4,
        )
        bad = [d for d in data if d["Unit"] not in VALID_UNITS]
        assert len(bad) == 0, f"Invalid units: {[(d['Product'], d['Unit']) for d in bad[:5]]}"

    def test_no_exact_duplicates(self):
        """No exact duplicate rows after parsing."""
        data = parse_excel(
            str(FIXTURES / "shifted_duplicate.xlsx"),
            sheet_name="HURT OWOC",
            is_fruit=True,
            skiprows=4,
        )
        seen = set()
        for r in data:
            key = (r["Product"], r["Unit"], r["Place"], r["Date"],
                   r["Statistic"], r["Price"], r["Origin"])
            assert key not in seen, f"Duplicate: {key}"
            seen.add(key)


class TestParserAssumptions:
    """Explicit tests for structural invariants the parser relies on.

    These assumptions were discovered during the bulletin 34-35 investigation
    and were previously undocumented.  If any of these fail, the parser will
    produce silently wrong data rather than raising an error.
    """

    def test_valid_units_is_nonempty(self):
        """VALID_UNITS must be a non-empty subset of known measurement units."""
        assert len(VALID_UNITS) > 0
        assert "kg" in VALID_UNITS

    def test_no_duplicate_rows_in_known_good_bulletin(self):
        """A known-good bulletin (32) should produce zero exact duplicate rows."""
        data = parse_excel(
            str(FIXTURES / "new_format.xlsx"),
            sheet_name="HURT OWOC",
            is_fruit=True,
            skiprows=4,
        )
        seen = set()
        for r in data:
            key = (r["Product"], r["Unit"], r["Place"], r["Date"],
                   r["Statistic"], r["Price"], r["Origin"])
            assert key not in seen, (
                f"Duplicate row in known-good bulletin: {key}"
            )
            seen.add(key)

    def test_all_rows_have_valid_unit(self):
        """Every parsed row's Unit must be in VALID_UNITS."""
        for sheet, is_fruit in [("HURT WARZ", False), ("HURT OWOC", True)]:
            data = parse_excel(
                str(FIXTURES / "new_format.xlsx"),
                sheet_name=sheet,
                is_fruit=is_fruit,
                skiprows=4,
            )
            bad = [d for d in data if d["Unit"] not in VALID_UNITS]
            assert len(bad) == 0, (
                f"{sheet}: rows with invalid units: "
                f"{[(d['Product'], d['Unit']) for d in bad[:3]]}"
            )

    def test_every_row_has_required_fields(self):
        """Every parsed row must have Product, Place, Date, Statistic, Price, Origin."""
        required = {"Product", "Place", "Date", "Statistic", "Price", "Origin"}
        data = parse_excel(
            str(FIXTURES / "new_format.xlsx"),
            sheet_name="HURT OWOC",
            is_fruit=True,
            skiprows=4,
        )
        for i, r in enumerate(data):
            missing = required - set(r.keys())
            assert not missing, f"Row {i} missing fields: {missing}"
            assert r["Product"], f"Row {i} has empty Product"
            assert r["Place"], f"Row {i} has empty Place"
            assert r["Date"], f"Row {i} has empty Date"

    def test_origin_is_always_krajowe_or_importowane(self):
        """Origin must be 'KRAJOWE' or 'IMPORTOWANE', never empty or garbage."""
        for sheet, is_fruit in [("HURT WARZ", False), ("HURT OWOC", True)]:
            data = parse_excel(
                str(FIXTURES / "new_format.xlsx"),
                sheet_name=sheet,
                is_fruit=is_fruit,
                skiprows=4,
            )
            origins = {d["Origin"] for d in data}
            assert origins <= {"KRAJOWE", "IMPORTOWANE"}, (
                f"{sheet}: unexpected origins: {origins - {'KRAJOWE', 'IMPORTOWANE'}}"
            )

    def test_implicit_labels_forward_filled(self):
        """Rows after KRAJOWE/IMPORTOWANE labels inherit the correct Origin."""
        data = parse_excel(
            str(FIXTURES / "new_format.xlsx"),
            sheet_name="HURT WARZ",
            is_fruit=False,
            skiprows=4,
        )
        origins = [d["Origin"] for d in data]
        # Must not have empty Origin between KRAJOWE and IMPORTOWANE sections
        assert "" not in origins, "Found rows with empty Origin"
