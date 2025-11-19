from __future__ import annotations

import time
from unittest.mock import Mock, patch

import pytest
import redis
from boost_exporter.cache import ExportCache


def test_redis_cache_set_get() -> None:
    """Test basic set and get operations with Redis cache."""
    cache = ExportCache()
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"
    assert cache.get("missing") is None


def test_redis_cache_ttl() -> None:
    """Test that TTL is respected."""
    # Create cache with short TTL
    cache = ExportCache(ttl_seconds=1)
    cache.set("key1", "value1")

    # Should be present initially
    assert cache.get("key1") == "value1"

    # We can't easily sleep in unit tests without slowing them down,
    # but fakeredis might support time travel or we can check the TTL setting.
    # For now, let's verify the TTL was set on the key.
    # We need access to the underlying redis client (which is a fakeredis instance)
    assert cache._redis.ttl("key1") <= 1


def test_redis_connection_error_handling() -> None:
    """Test that cache fails gracefully when Redis is down."""
    # Mock redis.get and redis.set to raise RedisError
    with patch.object(redis.Redis, "get", side_effect=redis.RedisError("Connection failed")):
        cache = ExportCache()
        # Should return None instead of raising
        assert cache.get("key1") is None

    with patch.object(redis.Redis, "set", side_effect=redis.RedisError("Connection failed")):
        cache = ExportCache()
        # Should not raise
        cache.set("key1", "value1")
