"""Tests for attrs-enhanced ExportCache class."""

from __future__ import annotations

import pytest

from boost_exporter import ExportCache


def test_cache_creation_with_defaults() -> None:
    """Test creating ExportCache with default values."""
    cache = ExportCache()
    assert cache.ttl_seconds == 3600
    # max_size is no longer a field in Redis cache
    # _store is replaced by _redis


def test_cache_creation_with_custom_values() -> None:
    """Test creating ExportCache with custom values."""
    cache = ExportCache(ttl_seconds=7200)
    assert cache.ttl_seconds == 7200


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


def test_cache_repr() -> None:
    """Test that attrs generates a readable __repr__."""
    cache = ExportCache(ttl_seconds=7200)
    repr_str = repr(cache)

    # Should include class name and key attributes
    assert "ExportCache" in repr_str
    assert "ttl_seconds=7200" in repr_str


def test_cache_functionality_unchanged() -> None:
    """Test that cache functionality still works after attrs conversion."""
    cache = ExportCache(ttl_seconds=3600)

    # Test set and get
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"

    # Test cache miss
    assert cache.get("nonexistent") is None

    # Test multiple entries
    cache.set("key2", "value2")
    assert cache.get("key1") == "value1"
    assert cache.get("key2") == "value2"

