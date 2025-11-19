import os
from typing import Any, Tuple

import attrs
import redis


def validate_positive_int(instance: Any, attribute: attrs.Attribute, value: int) -> None:
    """Validate that an integer value is positive (> 0)."""
    if value <= 0:
        raise ValueError(f"{attribute.name} must be positive, got {value}")


@attrs.define(slots=True, repr=True, eq=False)
class ExportCache:
    """Redis-backed cache with a TTL (default: 1 hour).

    This implementation uses Redis for storage, providing persistence and
    shared caching across multiple instances.

    Configuration:
        Uses REDIS_URL environment variable if set, otherwise defaults to localhost.
    """

    ttl_seconds: int = attrs.field(
        default=3600,
        validator=validate_positive_int,
        metadata={"description": "Time-to-live in seconds"},
    )
    _redis: redis.Redis = attrs.field(
        init=False,
        metadata={"description": "Redis client instance"},
    )

    def __attrs_post_init__(self) -> None:
        """Initialize Redis connection."""
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        self._redis = redis.from_url(redis_url, decode_responses=True)

    def get(self, key: str) -> str | None:
        """Get a cached export if present and not expired.

        Args:
            key: Cache key.

        Returns:
            Cached value if present, None otherwise.
        """
        try:
            return self._redis.get(key)
        except redis.RedisError:
            # Fail gracefully if Redis is down
            return None

    def set(self, key: str, data: str) -> None:
        """Cache an export value with a TTL.

        Args:
            key: Cache key.
            data: Value to cache.
        """
        try:
            self._redis.set(key, data, ex=self.ttl_seconds)
        except redis.RedisError:
            # Fail gracefully if Redis is down
            pass
