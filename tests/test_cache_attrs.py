"""Tests for attrs-enhanced ExportCache class."""

from __future__ import annotations

import pytest

from boost_exporter import ExportCache


def test_cache_creation_with_defaults() -> None:
    """Test creating ExportCache with default values."""
    cache = ExportCache()
    assert cache.ttl_seconds == 3600
    assert cache.max_size == 1000
    assert len(cache._store) == 0


def test_cache_creation_with_custom_values() -> None:
    """Test creating ExportCache with custom values."""
    cache = ExportCache(ttl_seconds=7200, max_size=500)
    assert cache.ttl_seconds == 7200
    assert cache.max_size == 500


def test_cache_validator_positive_ttl() -> None:
    """Test that ttl_seconds must be positive."""
    # Valid positive value
    cache = ExportCache(ttl_seconds=1)
    assert cache.ttl_seconds == 1

    # Zero should fail
    with pytest.raises(ValueError, match="ttl_seconds must be positive"):
        ExportCache(ttl_seconds=0)

    # Negative should fail
    with pytest.raises(ValueError, match="ttl_seconds must be positive"):
        ExportCache(ttl_seconds=-1)


def test_cache_validator_positive_max_size() -> None:
    """Test that max_size must be positive."""
    # Valid positive value
    cache = ExportCache(max_size=1)
    assert cache.max_size == 1

    # Zero should fail
    with pytest.raises(ValueError, match="max_size must be positive"):
        ExportCache(max_size=0)

    # Negative should fail
    with pytest.raises(ValueError, match="max_size must be positive"):
        ExportCache(max_size=-1)


def test_cache_repr() -> None:
    """Test that attrs generates a readable __repr__."""
    cache = ExportCache(ttl_seconds=7200, max_size=500)
    repr_str = repr(cache)

    # Should include class name and key attributes
    assert "ExportCache" in repr_str
    assert "ttl_seconds=7200" in repr_str
    assert "max_size=500" in repr_str


def test_cache_functionality_unchanged() -> None:
    """Test that cache functionality still works after attrs conversion."""
    cache = ExportCache(ttl_seconds=3600, max_size=10)

    # Test set and get
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"

    # Test cache miss
    assert cache.get("nonexistent") is None

    # Test multiple entries
    cache.set("key2", "value2")
    assert cache.get("key1") == "value1"
    assert cache.get("key2") == "value2"

