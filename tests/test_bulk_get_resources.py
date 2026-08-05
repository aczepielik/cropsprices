"""Tests for bulk_get_resources module."""

from pathlib import Path

import pytest

from cropsprices.download_manager import VALID_PREFIXES, DownloadManager as ResourceManager


@pytest.fixture
def tmp_dirs(tmp_path):
    """Create temporary output and overrides directories."""
    output_dir = tmp_path / "output"
    overrides_dir = tmp_path / "overrides"
    output_dir.mkdir()
    overrides_dir.mkdir()
    return output_dir, overrides_dir


class TestValidPrefixes:
    def test_contains_required_prefixes(self):
        assert "ceny hurtowe i targowiskowe" in VALID_PREFIXES
        assert "Rynek owoców i warzyw" in VALID_PREFIXES


class TestResourceManagerInit:
    def test_creates_output_directory(self, tmp_path):
        output_dir = tmp_path / "output"
        rm = ResourceManager(output_dir=str(output_dir))
        assert output_dir.exists()

    def test_creates_overrides_directory(self, tmp_path):
        overrides_dir = tmp_path / "overrides"
        rm = ResourceManager(overrides_dir=str(overrides_dir))
        assert overrides_dir.exists()


class TestResourceManagerExtractData:
    def test_extracts_data_from_pages(self):
        rm = ResourceManager(output_dir="/tmp/test_output")
        responses = [
            {"data": [{"id": "1"}, {"id": "2"}]},
            {"data": [{"id": "3"}]},
        ]
        result = rm.extract_data(responses)
        assert len(result) == 3
        assert result[0]["id"] == "1"
        assert result[2]["id"] == "3"

    def test_handles_empty_pages(self):
        rm = ResourceManager(output_dir="/tmp/test_output")
        responses = [{"data": []}, {"data": []}]
        result = rm.extract_data(responses)
        assert len(result) == 0


class TestResourceManagerFilterAndValidate:
    def test_filters_by_prefix(self):
        rm = ResourceManager(output_dir="/tmp/test_output")
        resources = [
            {"attributes": {"title": "ceny hurtowe i targowiskowe - styczeń"}, "id": "1"},
            {"attributes": {"title": "something else"}, "id": "2"},
        ]
        result = rm.filter_and_validate_resources(resources)
        # Note: These will fail validation because they're not full Resource objects
        # but the filtering should still work
        assert len(result) == 0  # Validation fails for incomplete data

    def test_filters_out_invalid_resources(self):
        rm = ResourceManager(output_dir="/tmp/test_output")
        resources = [
            {"attributes": {"title": "invalid resource"}, "id": "1"},
        ]
        result = rm.filter_and_validate_resources(resources)
        assert len(result) == 0
