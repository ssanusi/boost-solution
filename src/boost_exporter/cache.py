from __future__ import annotations

import time
from collections import OrderedDict
from typing import Tuple


class ExportCache:
    """In-memory cache with a TTL (default: 1 hour) and LRU eviction.

    Stores export results keyed by a hash of the input data and format.
    Implements LRU eviction when max_size is reached to prevent unbounded memory growth.

    Thread Safety:
        This implementation is not thread-safe. For multi-threaded environments,
        external synchronization (e.g., locks) must be used when accessing the cache.
    """

    def __init__(self, ttl_seconds: int = 3600, max_size: int = 1000) -> None:
        """Initialize cache with TTL and size limit.

        Args:
            ttl_seconds: Time-to-live in seconds (default: 3600 = 1 hour).
            max_size: Maximum number of entries before LRU eviction (default: 1000).
        """
        self._store: OrderedDict[str, Tuple[float, str]] = OrderedDict()
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size

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
