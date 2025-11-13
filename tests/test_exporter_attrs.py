"""Tests for attrs-enhanced DataExporter class."""

from __future__ import annotations

from boost_exporter import DataExporter, ExportCache, ExportFormat


def test_exporter_creation_with_defaults() -> None:
    """Test creating DataExporter with default values."""
    exporter = DataExporter()
    assert isinstance(exporter.cache, ExportCache)
    assert exporter.validate_input is False


def test_exporter_creation_with_custom_cache() -> None:
    """Test creating DataExporter with custom cache."""
    custom_cache = ExportCache(ttl_seconds=7200, max_size=500)
    exporter = DataExporter(cache=custom_cache)
    assert exporter.cache is custom_cache
    assert exporter.cache.ttl_seconds == 7200


def test_exporter_creation_with_validation() -> None:
    """Test creating DataExporter with validation enabled."""
    exporter = DataExporter(validate_input=True)
    assert exporter.validate_input is True


def test_exporter_repr() -> None:
    """Test that attrs generates a readable __repr__."""
    exporter = DataExporter(validate_input=True)
    repr_str = repr(exporter)

    # Should include class name
    assert "DataExporter" in repr_str
    # Should include validate_input
    assert "validate_input=True" in repr_str


def test_exporter_functionality_unchanged() -> None:
    """Test that exporter functionality still works after attrs conversion."""
    exporter = DataExporter()

    data = [
        {"id": 1, "name": "Test"},
        {"id": 2, "name": "Test2"},
    ]

    # Test JSON export
    json_result = exporter.export(data, ExportFormat.JSON)
    assert json_result is not None
    assert "Test" in json_result

    # Test CSV export
    csv_result = exporter.export(data, ExportFormat.CSV)
    assert csv_result is not None
    assert "id,name" in csv_result or "name,id" in csv_result


def test_exporter_with_custom_cache_functionality() -> None:
    """Test exporter with custom cache still works."""
    custom_cache = ExportCache(ttl_seconds=60, max_size=5)
    exporter = DataExporter(cache=custom_cache)

    data = [{"id": 1, "value": "test"}]

    # First export should cache
    result1 = exporter.export(data, ExportFormat.JSON)

    # Second export should use cache
    result2 = exporter.export(data, ExportFormat.JSON)

    assert result1 == result2
    assert len(exporter.cache._store) == 1

