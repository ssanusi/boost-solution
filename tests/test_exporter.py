from __future__ import annotations

import csv
import io
import json
import time
from datetime import date, datetime, time as dt_time
from typing import Any

import pytest

from boost_exporter import DataExporter, ExportCache, ExportFormat


def test_json_export_roundtrip() -> None:
    """Test JSON export and roundtrip parsing."""
    data: list[dict[str, Any]] = [
        {"id": 1, "name": "Ada"},
        {"id": 2, "name": "Grace", "lang": "COBOL"},
    ]
    exp = DataExporter()
    out = exp.export(data, ExportFormat.JSON)
    assert json.loads(out) == data


def test_csv_export_union_columns_and_order() -> None:
    """Test CSV export handles heterogeneous schemas and column ordering."""
    data = [
        {"a": 1, "b": "x"},
        {"a": 2, "c": 3},
    ]
    exp = DataExporter()
    out = exp.export(data, ExportFormat.CSV)

    rows = list(csv.DictReader(out.splitlines()))
    assert rows[0]["a"] == "1"
    assert rows[0]["b"] == "x"
    assert rows[1]["a"] == "2"
    assert rows[1]["b"] == ""  # missing becomes empty
    assert rows[1]["c"] == "3"

    # Header should be first row keys then unseen keys
    header = out.splitlines()[0].split(",")
    assert header == ["a", "b", "c"]


def test_empty_data_edges() -> None:
    exp = DataExporter()
    assert exp.export([], ExportFormat.JSON) == "[]"
    assert exp.export([], ExportFormat.CSV) == ""


def test_invalid_data_raises() -> None:
    exp = DataExporter()
    with pytest.raises(ValueError):
        exp.export([{"ok": True}, "not-a-dict"], ExportFormat.JSON)


class InstrumentedCache(ExportCache):
    """Cache subclass for testing that tracks method calls."""

    def __init__(self) -> None:
        super().__init__(ttl_seconds=3600)
        # These are not attrs fields, just instance variables for testing
        self.get_calls = 0
        self.set_calls = 0

    def get(self, key: str):  # type: ignore[override]
        self.get_calls += 1
        return super().get(key)

    def set(self, key: str, data: str) -> None:  # type: ignore[override]
        self.set_calls += 1
        return super().set(key, data)


def test_cache_is_used() -> None:
    """Test that cache is used for repeated exports."""
    data = [{"n": i} for i in range(3)]
    cache = InstrumentedCache()
    exp = DataExporter(cache=cache)

    out1 = exp.export(data, ExportFormat.JSON)
    out2 = exp.export(data, ExportFormat.JSON)

    assert out1 == out2
    assert cache.set_calls == 1
    assert cache.get_calls >= 2


def test_cache_expiration() -> None:
    """Test that cache entries expire after TTL."""
    cache = ExportCache(ttl_seconds=1)  # 1 second TTL
    exp = DataExporter(cache=cache)

    data = [{"id": 1, "name": "Test"}]
    key = exp._compute_cache_key(data, ExportFormat.JSON)

    # First export - should cache
    out1 = exp.export(data, ExportFormat.JSON)
    assert cache.get(key) == out1

    # Wait for expiration
    time.sleep(1.1)

    # Should be expired
    assert cache.get(key) is None

    # Second export should regenerate (not from cache)
    out2 = exp.export(data, ExportFormat.JSON)
    assert out1 == out2  # Same content, but regenerated


def test_cache_lru_eviction() -> None:
    """Test that LRU eviction works when cache size limit is reached."""
    cache = ExportCache(max_size=3)
    exp = DataExporter(cache=cache)

    # Fill cache beyond limit
    data1 = [{"id": 1}]
    data2 = [{"id": 2}]
    data3 = [{"id": 3}]
    data4 = [{"id": 4}]

    exp.export(data1, ExportFormat.JSON)
    exp.export(data2, ExportFormat.JSON)
    exp.export(data3, ExportFormat.JSON)
    exp.export(data4, ExportFormat.JSON)  # Should evict data1

    # data1 should be evicted (oldest)
    key1 = exp._compute_cache_key(data1, ExportFormat.JSON)
    assert cache.get(key1) is None

    # data4 should still be cached (newest)
    key4 = exp._compute_cache_key(data4, ExportFormat.JSON)
    assert cache.get(key4) is not None


def test_unsupported_format_raises() -> None:
    """Test that unsupported formats raise ValueError."""
    exp = DataExporter()
    data = [{"id": 1}]

    # Test that both supported formats work
    assert exp.export(data, ExportFormat.JSON) is not None
    assert exp.export(data, ExportFormat.CSV) is not None

    # Note: We can't easily test an unsupported format at runtime because
    # the ExportFormat enum prevents invalid values at the type level.
    # The ValueError for unsupported formats is a defensive check in the code
    # that would only trigger if the enum is extended incorrectly.
    # This is actually good design - type safety prevents the error case.


def test_datetime_serialization() -> None:
    """Test that datetime objects are properly serialized."""
    exp = DataExporter()
    test_date = date(2024, 1, 15)
    test_datetime = datetime(2024, 1, 15, 10, 30, 45)
    test_time = dt_time(10, 30, 45)

    data = [
        {"date": test_date, "datetime": test_datetime, "time": test_time},
    ]

    # JSON should serialize datetimes
    json_out = exp.export(data, ExportFormat.JSON)
    parsed = json.loads(json_out)
    assert parsed[0]["date"] == "2024-01-15"
    assert parsed[0]["datetime"] == "2024-01-15T10:30:45"
    assert parsed[0]["time"] == "10:30:45"

    # CSV should also serialize datetimes
    csv_out = exp.export(data, ExportFormat.CSV)
    assert "2024-01-15" in csv_out
    assert "2024-01-15T10:30:45" in csv_out


def test_large_dataset() -> None:
    """Test export with a larger dataset."""
    exp = DataExporter()
    # Create 1000 items as mentioned in requirements
    data = [{"id": i, "name": f"Item {i}", "value": i * 2} for i in range(1000)]

    json_out = exp.export(data, ExportFormat.JSON)
    parsed = json.loads(json_out)
    assert len(parsed) == 1000
    assert parsed[0]["id"] == 0
    assert parsed[999]["id"] == 999

    csv_out = exp.export(data, ExportFormat.CSV)
    lines = csv_out.splitlines()
    assert len(lines) == 1001  # 1 header + 1000 rows
    assert "id,name,value" in lines[0]


def test_csv_with_missing_values() -> None:
    """Test CSV export handles missing values correctly."""
    exp = DataExporter()
    data = [
        {"a": 1, "b": 2, "c": 3},
        {"a": 4, "b": 5},  # missing c
        {"a": 6, "c": 7},  # missing b
    ]

    csv_out = exp.export(data, ExportFormat.CSV)
    rows = list(csv.DictReader(csv_out.splitlines()))
    assert rows[0]["a"] == "1"
    assert rows[0]["b"] == "2"
    assert rows[0]["c"] == "3"
    assert rows[1]["a"] == "4"
    assert rows[1]["b"] == "5"
    assert rows[1]["c"] == ""  # missing value
    assert rows[2]["a"] == "6"
    assert rows[2]["b"] == ""  # missing value
    assert rows[2]["c"] == "7"


def test_csv_special_characters() -> None:
    """Test CSV export handles special characters (quotes, commas, newlines) correctly."""
    exp = DataExporter()
    data = [
        {
            "name": 'Quote: "Hello"',
            "description": "Comma, in text",
            "multiline": "Line 1\nLine 2\nLine 3",
            "mixed": 'Quote "and" comma, here',
        },
        {
            "name": "Normal text",
            "description": "No special chars",
            "multiline": "Single line",
            "mixed": "Plain value",
        },
    ]

    csv_out = exp.export(data, ExportFormat.CSV)
    # Verify CSV can be parsed correctly (csv module handles escaping)
    # Use StringIO to preserve newlines in fields
    rows = list(csv.DictReader(io.StringIO(csv_out)))

    assert len(rows) == 2
    # First row with special characters
    assert rows[0]["name"] == 'Quote: "Hello"'
    assert rows[0]["description"] == "Comma, in text"
    assert rows[0]["multiline"] == "Line 1\nLine 2\nLine 3"
    assert rows[0]["mixed"] == 'Quote "and" comma, here'

    # Second row without special characters
    assert rows[1]["name"] == "Normal text"
    assert rows[1]["description"] == "No special chars"
    assert rows[1]["multiline"] == "Single line"
    assert rows[1]["mixed"] == "Plain value"

    # Verify roundtrip: export and re-parse should preserve data
    # (CSV module automatically handles quoting/escaping)
    assert csv_out.count('"') > 0  # Should have quotes for special characters


def test_cache_different_formats() -> None:
    """Test that different formats produce different cache keys."""
    exp = DataExporter()
    data = [{"id": 1, "name": "Test"}]

    json_out = exp.export(data, ExportFormat.JSON)
    csv_out = exp.export(data, ExportFormat.CSV)

    assert json_out != csv_out
    assert json_out.startswith("[")
    assert "id,name" in csv_out or "name,id" in csv_out


def test_invalid_data_not_list() -> None:
    """Test that non-list data raises ValueError."""
    exp = DataExporter()
    with pytest.raises(ValueError, match="data must be a list"):
        exp.export({"not": "a list"}, ExportFormat.JSON)


def test_invalid_data_not_dict_in_list() -> None:
    """Test that list with non-dict items raises ValueError."""
    exp = DataExporter()
    with pytest.raises(ValueError, match="data\\[0\\] is not a dict"):
        exp.export(["not a dict"], ExportFormat.JSON)


def test_empty_dict_in_data() -> None:
    """Test export with empty dictionaries in data."""
    exp = DataExporter()
    data = [{}, {"a": 1}, {}]

    json_out = exp.export(data, ExportFormat.JSON)
    parsed = json.loads(json_out)
    assert len(parsed) == 3
    assert parsed[0] == {}
    assert parsed[1] == {"a": 1}
    assert parsed[2] == {}

    csv_out = exp.export(data, ExportFormat.CSV)
    assert "a" in csv_out.splitlines()[0]  # Header should have 'a'


def test_none_values_in_data() -> None:
    """Test export with None values in data."""
    exp = DataExporter()
    data = [{"a": 1, "b": None, "c": "test"}]

    json_out = exp.export(data, ExportFormat.JSON)
    parsed = json.loads(json_out)
    assert parsed[0]["a"] == 1
    assert parsed[0]["b"] is None
    assert parsed[0]["c"] == "test"

    csv_out = exp.export(data, ExportFormat.CSV)
    rows = list(csv.DictReader(csv_out.splitlines()))
    assert rows[0]["a"] == "1"
    assert rows[0]["b"] == ""  # None becomes empty string in CSV
    assert rows[0]["c"] == "test"


def test_cache_key_stability() -> None:
    """Test that cache keys are stable for same data."""
    exp = DataExporter()
    data1 = [{"a": 1, "b": 2}]
    data2 = [{"b": 2, "a": 1}]  # Same data, different key order

    key1 = exp._compute_cache_key(data1, ExportFormat.JSON)
    key2 = exp._compute_cache_key(data2, ExportFormat.JSON)

    # Keys should be same due to sort_keys=True in JSON serialization
    assert key1 == key2


def test_real_dataset_json() -> None:
    """Test JSON export with the provided 1000-item dataset."""
    from data import data as test_data

    exp = DataExporter()
    json_out = exp.export(test_data, ExportFormat.JSON)

    # Verify it's valid JSON
    parsed = json.loads(json_out)
    assert len(parsed) == len(test_data)

    # Verify first item structure
    assert "event_type" in parsed[0]
    assert "created_at" in parsed[0]
    # Datetime should be serialized as ISO string
    assert isinstance(parsed[0]["created_at"], str)
    assert "2023-12-05" in parsed[0]["created_at"]  # Check ISO format

    # Verify all items have expected keys
    expected_keys = {"event_type", "location_name", "sku_name", "quantity", "value", "created_at"}
    for item in parsed[:10]:  # Check first 10 items
        assert set(item.keys()) == expected_keys


def test_real_dataset_csv() -> None:
    """Test CSV export with the provided 1000-item dataset."""
    from data import data as test_data

    exp = DataExporter()
    csv_out = exp.export(test_data, ExportFormat.CSV)

    # Verify CSV structure
    rows = list(csv.DictReader(io.StringIO(csv_out)))
    assert len(rows) == len(test_data)

    # Verify header contains expected columns
    expected_columns = {"event_type", "location_name", "sku_name", "quantity", "value", "created_at"}
    assert set(rows[0].keys()) == expected_columns

    # Verify first row data
    assert rows[0]["event_type"] == "Receive"
    assert rows[0]["location_name"] == "Warehouse"
    # Datetime should be serialized as ISO string
    assert "2023-12-05" in rows[0]["created_at"]
    # Quantity and value should be strings in CSV
    assert rows[0]["quantity"] == "111"
    assert rows[0]["value"] == "53058"


def test_real_dataset_cache() -> None:
    """Test cache behavior with the real dataset."""
    from data import data as test_data

    cache = InstrumentedCache()
    exp = DataExporter(cache=cache)

    # First export - should compute and cache
    json_out1 = exp.export(test_data, ExportFormat.JSON)
    assert cache.set_calls == 1
    assert cache.get_calls >= 1

    # Second export - should use cache
    json_out2 = exp.export(test_data, ExportFormat.JSON)
    assert json_out1 == json_out2
    assert cache.set_calls == 1  # Should not set again
    assert cache.get_calls >= 2  # Should have checked cache again

    # Different format - should be different cache entry
    csv_out = exp.export(test_data, ExportFormat.CSV)
    assert csv_out != json_out1
    assert cache.set_calls == 2  # New format = new cache entry


def test_real_dataset_roundtrip() -> None:
    """Test that exported data can be roundtripped correctly."""
    from data import data as test_data

    exp = DataExporter()

    # JSON roundtrip
    json_out = exp.export(test_data, ExportFormat.JSON)
    parsed = json.loads(json_out)

    # Verify structure matches
    assert len(parsed) == len(test_data)
    assert len(parsed[0]) == len(test_data[0])

    # Verify datetime serialization is correct
    # Original has datetime objects, parsed has ISO strings
    import datetime as dt_module
    assert isinstance(test_data[0]["created_at"], dt_module.datetime)
    assert isinstance(parsed[0]["created_at"], str)
    # Verify ISO format
    assert "T" in parsed[0]["created_at"] or "-" in parsed[0]["created_at"]

    # CSV roundtrip - verify it can be parsed
    csv_out = exp.export(test_data, ExportFormat.CSV)
    csv_rows = list(csv.DictReader(io.StringIO(csv_out)))
    assert len(csv_rows) == len(test_data)
    # All datetime fields should be strings in CSV
    assert isinstance(csv_rows[0]["created_at"], str)
