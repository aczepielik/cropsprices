import warnings
from pathlib import Path

import pytest

from cropsprices.parsers import parse_excel

FIXTURES = Path(__file__).parent / "fixtures"


class TestLegacySheetNamesColZero:
    """Legacy sheet names (ceny hurt_warz/owoc), product in col 0, skiprows=1."""

    def test_vegetables(self):
        data = parse_excel(
            str(FIXTURES / "old_format.xlsx"),
            sheet_name="ceny hurt_warz",
            is_fruit=False,
            skiprows=1,
        )
        assert len(data) > 0
        assert data[0]["Product"] == "Buraki cwikowe"
        assert data[0]["Place"] == "Bronisze"
        assert data[0]["Unit"] == "kg"
        assert data[0]["Origin"] == "KRAJOWE"

    def test_fruits(self):
        data = parse_excel(
            str(FIXTURES / "old_format.xlsx"),
            sheet_name="ceny hurt_owoc",
            is_fruit=True,
            skiprows=1,
        )
        assert len(data) > 0
        assert data[0]["Product"] == "Gruszki"
        assert data[0]["Place"] == "Bronisze"


class TestLegacySheetNames:
    """Legacy sheet names (ceny hurt_warz/owoc) but with newer title prefix."""

    def test_vegetables(self):
        data = parse_excel(
            str(FIXTURES / "rynek_old_sheets.xlsx"),
            sheet_name="ceny hurt_warz",
            is_fruit=False,
            skiprows=1,
        )
        assert len(data) > 0
        assert data[0]["Product"] == "Buraki cwikowe"

    def test_fruits(self):
        data = parse_excel(
            str(FIXTURES / "rynek_old_sheets.xlsx"),
            sheet_name="ceny hurt_owoc",
            is_fruit=True,
            skiprows=1,
        )
        assert len(data) > 0
        assert data[0]["Product"] == "Gruszki"


class TestHurtSheetFormat:
    """HURT WARZ/OWOC sheets: product in col 1, extra header rows (skiprows=4).

    These tests would FAIL before the parser changes (last 2 commits)
    because:
    - ExcelData validator checked col 0 for KRAJOWE (now checks any col)
    - _set_data_rows_columns assumed product in col 0
    - _swap_min_max_if_necessary failed on StringDtype columns
    - extract_dates_and_places didn't handle missing place names
    """

    def test_vegetables(self):
        data = parse_excel(
            str(FIXTURES / "new_format.xlsx"),
            sheet_name="HURT WARZ",
            is_fruit=False,
            skiprows=4,
        )
        assert len(data) > 0
        assert data[0]["Product"] == "Buraki cwikowe"
        assert data[0]["Place"] == "Bronisze"
        assert data[0]["Unit"] == "kg"

    def test_fruits(self):
        data = parse_excel(
            str(FIXTURES / "new_format.xlsx"),
            sheet_name="HURT OWOC",
            is_fruit=True,
            skiprows=4,
        )
        assert len(data) > 0
        assert data[0]["Product"] == "Gruszki"
        assert data[0]["Place"] == "Bronisze"

    def test_fruit_variety_concatenation(self):
        """Fruit data should concatenate Product + Variety."""
        data = parse_excel(
            str(FIXTURES / "new_format.xlsx"),
            sheet_name="HURT OWOC",
            is_fruit=True,
            skiprows=4,
        )
        boskoop = [d for d in data if "Boskoop" in d["Product"]]
        assert len(boskoop) > 0

    def test_dates_are_iso_strings(self):
        data = parse_excel(
            str(FIXTURES / "new_format.xlsx"),
            sheet_name="HURT WARZ",
            is_fruit=False,
            skiprows=4,
        )
        for row in data:
            assert row["Date"] is not None
            # Date should be parseable as YYYY-MM-DD
            parts = row["Date"].split("-")
            assert len(parts) == 3

    def test_min_max_values_are_numeric(self):
        data = parse_excel(
            str(FIXTURES / "new_format.xlsx"),
            sheet_name="HURT WARZ",
            is_fruit=False,
            skiprows=4,
        )
        for row in data:
            assert isinstance(row["Price"], (int, float))


class TestHurtSheetMissingPlaces:
    """New format where some place names are NaN in the header.

    Before the fix, extract_dates_and_places() would return fewer places
    than the actual number of Max/Min column pairs, causing a column
    count mismatch in _set_data_rows_columns().
    """

    def test_missing_place_gets_placeholder(self):
        data = parse_excel(
            str(FIXTURES / "new_format_missing_places.xlsx"),
            sheet_name="HURT WARZ",
            is_fruit=False,
            skiprows=4,
        )
        assert len(data) > 0
        places = set(d["Place"] for d in data)
        assert "Bronisze" in places
        assert "Kalisz" in places
        assert "Poznań" in places
        assert "Rzeszów" in places
        # The missing place (col 8) gets a placeholder name
        assert "Rynek3" in places


class TestBulkProcessSheetDetection:
    """Test that bulk_process_resources.py detects both old and new sheet names."""

    def test_detects_old_sheet_names(self):
        from scripts.cloud_init.bulk_process_resources import DataManager

        dm = DataManager()
        assert "ceny hurt_warz" in dm.VEG_SHEET_NAMES
        assert "ceny hurt_owoc" in dm.FRUIT_SHEET_NAMES

    def test_detects_new_sheet_names(self):
        from scripts.cloud_init.bulk_process_resources import DataManager

        dm = DataManager()
        assert "HURT WARZ" in dm.VEG_SHEET_NAMES
        assert "HURT OWOC" in dm.FRUIT_SHEET_NAMES
