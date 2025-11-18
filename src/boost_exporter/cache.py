from __future__ import annotations

import time
from collections import OrderedDict
from typing import Any, Tuple

import attrs


def validate_positive_int(instance: Any, attribute: attrs.Attribute, value: int) -> None:
    """Validate that an integer value is positive (> 0)."""
    if value <= 0:
        raise ValueError(f"{attribute.name} must be positive, got {value}")


@attrs.define(slots=True, repr=True, eq=False)  # eq=False since cache has mutable state
class ExportCache:
    """In-memory cache with a TTL (default: 1 hour) and LRU eviction.

    This class uses attrs to eliminate boilerplate while maintaining mutable state
    for the internal cache store. attrs generates __init__ and __repr__ automatically.

    Stores export results keyed by a hash of the input data and format.
    Implements LRU eviction when max_size is reached to prevent unbounded memory growth.

    Thread Safety:
        This implementation is not thread-safe. For multi-threaded environments,
        external synchronization (e.g., locks) must be used when accessing the cache.
    """

    ttl_seconds: int = attrs.field(
        default=3600,
        validator=validate_positive_int,
        metadata={"description": "Time-to-live in seconds"},
    )
    max_size: int = attrs.field(
        default=1000,
        validator=validate_positive_int,
        metadata={"description": "Maximum number of cache entries before LRU eviction"},
    )
    _store: OrderedDict[str, Tuple[float, str]] = attrs.field(
        init=False,
        factory=OrderedDict,
        metadata={"description": "Internal cache storage"},
    )

    def get(self, key: str) -> str | None:
        """Get a cached export if present and not expired.

        Moves the entry to the end (most recently used) if found.

        Args:
            key: Cache key.

        Returns:
            Cached value if present and not expired, None otherwise.
        """
        entry = self._store.get(key)
        if not entry:
            return None

        ts, value = entry
        now = time.time()
        if now - ts > self.ttl_seconds:
            # expired - remove it
            self._store.pop(key, None)
            return None

        # Move to end (most recently used) for LRU
        self._store.move_to_end(key)
        return value

    def set(self, key: str, data: str) -> None:
        """Cache an export value with a timestamp for expiration checks.

        Evicts least recently used entry if max_size is reached.
        Note: This implementation is not thread-safe. For multi-threaded use,
        external synchronization is required.

        Args:
            key: Cache key.
            data: Value to cache.
        """
        # If key exists, update it and move to end (most recently used)
        if key in self._store:
            self._store.move_to_end(key)
            self._store[key] = (time.time(), data)
            return

        # For new keys, evict oldest if we're at capacity before adding
        if len(self._store) >= self.max_size:
            self._store.popitem(last=False)  # Remove oldest (first) item

        # Add new entry
        self._store[key] = (time.time(), data)
