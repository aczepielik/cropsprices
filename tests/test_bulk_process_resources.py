"""Tests for bulk_process_resources module."""

import shutil
from pathlib import Path

import pytest

from cropsprices.bulk_process_resources import DataManager

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def tmp_dirs(tmp_path):
    """Create temporary raw and parsed directories."""
    raw_dir = tmp_path / "raw"
    parsed_dir = tmp_path / "parsed"
    raw_dir.mkdir()
    parsed_dir.mkdir()
    return raw_dir, parsed_dir


class TestDataManagerSheetNames:
    def test_vegetable_sheet_names(self):
        dm = DataManager()
        assert "ceny hurt_warz" in dm.VEG_SHEET_NAMES
        assert "HURT WARZ" in dm.VEG_SHEET_NAMES
        assert "WK" in dm.VEG_SHEET_NAMES

    def test_fruit_sheet_names(self):
        dm = DataManager()
        assert "ceny hurt_owoc" in dm.FRUIT_SHEET_NAMES
        assert "HURT OWOC" in dm.FRUIT_SHEET_NAMES
        assert "OK" in dm.FRUIT_SHEET_NAMES


class TestDataManagerInit:
    def test_creates_directories(self, tmp_path):
        raw_dir = tmp_path / "raw"
        parsed_dir = tmp_path / "parsed"
        dm = DataManager(raw_dir=str(raw_dir), parsed_dir=str(parsed_dir))
        assert raw_dir.exists()
        assert parsed_dir.exists()

    def test_default_directories(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        dm = DataManager()
        assert dm.raw_dir == Path("data/raw")
        assert dm.parsed_dir == Path("data/parsed")


class TestDataManagerProcessSheet:
    def test_process_old_format_file(self, tmp_dirs):
        raw_dir, parsed_dir = tmp_dirs
        shutil.copy(FIXTURES / "old_format.xlsx", raw_dir / "old_format.xlsx")

        dm = DataManager(raw_dir=str(raw_dir), parsed_dir=str(parsed_dir))
        dm._process_single_file(raw_dir / "old_format.xlsx")

        csv_files = list(parsed_dir.glob("*.csv"))
        assert len(csv_files) > 0

    def test_process_new_format_file(self, tmp_dirs):
        raw_dir, parsed_dir = tmp_dirs
        shutil.copy(FIXTURES / "new_format.xlsx", raw_dir / "new_format.xlsx")

        dm = DataManager(raw_dir=str(raw_dir), parsed_dir=str(parsed_dir))
        dm._process_single_file(raw_dir / "new_format.xlsx")

        csv_files = list(parsed_dir.glob("*.csv"))
        assert len(csv_files) > 0
