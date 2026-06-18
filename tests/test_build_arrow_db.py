"""Tests for build_arrow_db module."""

import json
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.ipc as ipc
import pytest

from cropsprices.build_arrow_db import (
    build_manifest,
    load_all_csvs,
    make_table,
    pivot_min_max,
    sanitize_filename,
    write_monthly_files,
)


@pytest.fixture
def sample_df():
    """Create a sample DataFrame mimicking parsed CSV output."""
    return pd.DataFrame({
        "Product": ["Buraki cwikowe", "Buraki cwikowe", "Cebula", "Cebula"],
        "Place": ["Bronisze", "Kalisz", "Bronisze", "Kalisz"],
        "Date": ["2024-01-15", "2024-01-15", "2024-01-15", "2024-01-15"],
        "Origin": ["KRAJOWE", "KRAJOWE", "KRAJOWE", "KRAJOWE"],
        "Statistic": ["Max", "Max", "Min", "Min"],
        "Price": [2.5, 3.0, 1.5, 2.0],
        "Unit": ["kg", "kg", "kg", "kg"],
    })


@pytest.fixture
def tmp_parsed_dir(tmp_path, sample_df):
    """Create a temporary parsed directory with a CSV file."""
    parsed_dir = tmp_path / "parsed"
    parsed_dir.mkdir()
    sample_df.to_csv(parsed_dir / "test_file_vegetables.csv", index=False)
    return parsed_dir


@pytest.fixture
def tmp_output_dir(tmp_path):
    """Create a temporary output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


class TestLoadAllCsvs:
    def test_loads_csv_files(self, tmp_parsed_dir):
        df = load_all_csvs(tmp_parsed_dir)
        assert len(df) == 4
        assert list(df.columns) == ["Product", "Place", "Date", "Origin", "Statistic", "Price", "Unit"]

    def test_empty_directory(self, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        df = load_all_csvs(empty_dir)
        assert len(df) == 0

    def test_multiple_csv_files(self, tmp_path):
        parsed_dir = tmp_path / "parsed"
        parsed_dir.mkdir()
        df1 = pd.DataFrame({"Product": ["A"], "Value": [1]})
        df2 = pd.DataFrame({"Product": ["B"], "Value": [2]})
        df1.to_csv(parsed_dir / "file1.csv", index=False)
        df2.to_csv(parsed_dir / "file2.csv", index=False)
        result = load_all_csvs(parsed_dir)
        assert len(result) == 2


class TestPivotMinMax:
    def test_pivots_statistics(self, sample_df):
        result = pivot_min_max(sample_df)
        assert "price_min" in result.columns
        assert "price_max" in result.columns
        assert "Statistic" not in result.columns

    def test_merges_min_max_rows(self, sample_df):
        result = pivot_min_max(sample_df)
        # 4 rows (2 products x 2 places) should become 4 rows (merged min/max)
        assert len(result) == 4

    def test_numeric_prices(self, sample_df):
        result = pivot_min_max(sample_df)
        assert result["price_min"].dtype == "float32"
        assert result["price_max"].dtype == "float32"


class TestMakeTable:
    def test_creates_arrow_table(self, sample_df):
        pivoted = pivot_min_max(sample_df)
        table = make_table(pivoted)
        assert isinstance(table, pa.Table)

    def test_correct_columns(self, sample_df):
        pivoted = pivot_min_max(sample_df)
        table = make_table(pivoted)
        expected_cols = {"date", "product", "place", "origin", "price_min", "price_max", "unit"}
        assert set(table.column_names) == expected_cols

    def test_dictionary_encoded_strings(self, sample_df):
        pivoted = pivot_min_max(sample_df)
        table = make_table(pivoted)
        for col in ["product", "place", "origin"]:
            assert table.column(col).type == pa.dictionary(pa.int8(), pa.utf8())


class TestSanitizeFilename:
    def test_forward_slash(self):
        assert sanitize_filename("a/b") == "a-b"

    def test_backslash(self):
        assert sanitize_filename("a\\b") == "a-b"

    def test_no_special_chars(self):
        assert sanitize_filename("hello") == "hello"


class TestWriteMonthlyFiles:
    def test_creates_arrow_files(self, sample_df, tmp_output_dir):
        pivoted = pivot_min_max(sample_df)
        pivoted["year"] = pd.to_datetime(pivoted["Date"]).dt.year
        pivoted["month"] = pd.to_datetime(pivoted["Date"]).dt.month
        files = write_monthly_files(pivoted, tmp_output_dir)
        assert len(files) > 0
        for f in files:
            assert (tmp_output_dir / f).exists()

    def test_arrow_files_are_readable(self, sample_df, tmp_output_dir):
        pivoted = pivot_min_max(sample_df)
        pivoted["year"] = pd.to_datetime(pivoted["Date"]).dt.year
        pivoted["month"] = pd.to_datetime(pivoted["Date"]).dt.month
        files = write_monthly_files(pivoted, tmp_output_dir)
        for f in files:
            table = ipc.open_file(tmp_output_dir / f).read_all()
            assert len(table) > 0

    def test_different_origins_in_separate_files(self, tmp_output_dir):
        """Fix 2: Products with KRAJOWE and IMPORTOWANE origins must not be
        mixed into the same Arrow file. Each origin should produce a
        separate file (e.g., prices_2024_01_Gruszki_KRAJOWE.arrow)."""
        df = pd.DataFrame({
            "Product": ["Gruszki", "Gruszki", "Gruszki", "Gruszki"],
            "Place": ["Bronisze", "Bronisze", "Bronisze", "Bronisze"],
            "Date": ["2024-01-15", "2024-01-15", "2024-01-15", "2024-01-15"],
            "Origin": ["KRAJOWE", "KRAJOWE", "IMPORTOWANE", "IMPORTOWANE"],
            "Statistic": ["Max", "Min", "Max", "Min"],
            "Price": [5.0, 3.0, 8.0, 6.0],
            "Unit": ["kg", "kg", "kg", "kg"],
        })
        pivoted = pivot_min_max(df)
        pivoted["year"] = pd.to_datetime(pivoted["Date"]).dt.year
        pivoted["month"] = pd.to_datetime(pivoted["Date"]).dt.month
        files = write_monthly_files(pivoted, tmp_output_dir)

        # Each file should contain only one origin
        for f in files:
            table = ipc.open_file(tmp_output_dir / f).read_all()
            origins_in_file = set(table.column("origin").to_pylist())
            assert len(origins_in_file) == 1, (
                f"File {f} contains mixed origins: {origins_in_file}"
            )


class TestBuildManifest:
    def test_manifest_structure(self, sample_df):
        pivoted = pivot_min_max(sample_df)
        pivoted["year"] = pd.to_datetime(pivoted["Date"]).dt.year
        manifest = build_manifest(pivoted, ["file1.arrow"])
        assert "years" in manifest
        assert "products" in manifest
        assert "lastUpdate" in manifest
        assert isinstance(manifest["years"], list)
        assert isinstance(manifest["products"], list)

    def test_manifest_years(self, sample_df):
        pivoted = pivot_min_max(sample_df)
        pivoted["year"] = pd.to_datetime(pivoted["Date"]).dt.year
        manifest = build_manifest(pivoted, [])
        assert 2024 in manifest["years"]


class TestPivotMinMaxUnitPreserved:
    """Fix 1: pivot_min_max must not drop the Unit column.

    BUG: pivot_min_max() drops Unit via .drop(columns=["Statistic", "Unit"]).
    This means the unit information is lost after pivoting, so "Rzodkiewka kg"
    and "Rzodkiewka pęczek" become indistinguishable.
    """

    def test_unit_column_preserved_after_pivot(self):
        df = pd.DataFrame({
            "Product": ["Rzodkiewka", "Rzodkiewka"],
            "Place": ["Bronisze", "Bronisze"],
            "Date": ["2024-01-15", "2024-01-15"],
            "Origin": ["KRAJOWE", "KRAJOWE"],
            "Statistic": ["Max", "Min"],
            "Price": [3.0, 1.5],
            "Unit": ["kg", "kg"],
        })
        result = pivot_min_max(df)
        assert "Unit" in result.columns, "Unit column must be preserved after pivot"
        assert result["Unit"].iloc[0] == "kg"

    def test_different_units_stay_separate(self):
        """Rzodkiewka sold by kg and pęczek are different products."""
        df = pd.DataFrame({
            "Product": ["Rzodkiewka", "Rzodkiewka", "Rzodkiewka", "Rzodkiewka"],
            "Place": ["Bronisze", "Bronisze", "Bronisze", "Bronisze"],
            "Date": ["2024-01-15", "2024-01-15", "2024-01-15", "2024-01-15"],
            "Origin": ["KRAJOWE", "KRAJOWE", "KRAJOWE", "KRAJOWE"],
            "Statistic": ["Max", "Min", "Max", "Min"],
            "Price": [3.0, 1.5, 5.0, 2.5],
            "Unit": ["kg", "kg", "pęczek", "pęczek"],
        })
        result = pivot_min_max(df)
        units = set(result["Unit"].dropna())
        assert units == {"kg", "pęczek"}, "Different units must remain as separate rows"
        # After pivot, each (Product, Place, Date, Origin, Unit) combo = 1 row
        # So 2 units = 2 rows
        assert len(result) == 2, "kg and pęczek should produce separate rows after pivot"


class TestPivotMinMaxOriginPreserved:
    """Fix 2: pivot_min_max must not merge rows with different origins.

    BUG: The merge uses on=["Product", "Place", "Date", "Origin"], but when
    the same product exists with both KRAJOWE and IMPORTOWANE origins for the
    same Place and Date, they should stay as separate rows, not be merged.
    """

    def test_different_origins_stay_separate(self):
        """Gruszki KRAJOWE and Gruszki IMPORTOWANE are different products."""
        df = pd.DataFrame({
            "Product": ["Gruszki", "Gruszki", "Gruszki", "Gruszki"],
            "Place": ["Bronisze", "Bronisze", "Bronisze", "Bronisze"],
            "Date": ["2024-01-15", "2024-01-15", "2024-01-15", "2024-01-15"],
            "Origin": ["KRAJOWE", "KRAJOWE", "IMPORTOWANE", "IMPORTOWANE"],
            "Statistic": ["Max", "Min", "Max", "Min"],
            "Price": [5.0, 3.0, 8.0, 6.0],
            "Unit": ["kg", "kg", "kg", "kg"],
        })
        result = pivot_min_max(df)
        origins = set(result["Origin"].dropna())
        assert origins == {"KRAJOWE", "IMPORTOWANE"}, "Different origins must remain as separate rows"
        assert len(result) == 2, "KRAJOWE and IMPORTOWANE should produce separate rows"

    def test_origin_not_lost_during_merge(self):
        """Origin must be preserved in the output, not dropped or mixed."""
        df = pd.DataFrame({
            "Product": ["Jabłka", "Jabłka", "Jabłka", "Jabłka"],
            "Place": ["Bronisze", "Bronisze", "Bronisze", "Bronisze"],
            "Date": ["2024-01-15", "2024-01-15", "2024-01-15", "2024-01-15"],
            "Origin": ["KRAJOWE", "KRAJOWE", "IMPORTOWANE", "IMPORTOWANE"],
            "Statistic": ["Max", "Min", "Max", "Min"],
            "Price": [4.0, 2.0, 6.0, 4.0],
            "Unit": ["kg", "kg", "kg", "kg"],
        })
        result = pivot_min_max(df)
        krajowe_row = result[result["Origin"] == "KRAJOWE"].iloc[0]
        import_row = result[result["Origin"] == "IMPORTOWANE"].iloc[0]
        assert krajowe_row["price_max"] == 4.0, "KRAJOWE price_max must not be mixed with IMPORTOWANE"
        assert import_row["price_max"] == 6.0, "IMPORTOWANE price_max must not be mixed with KRAJOWE"
