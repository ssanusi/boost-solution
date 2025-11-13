from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import date, datetime, time
from typing import Any

import attrs

from .cache import ExportCache
from .formats import ExportFormat
from .models import validate_and_convert_records


def create_default_cache() -> ExportCache:
    """Factory function to create a default ExportCache instance."""
    return ExportCache()


@attrs.define(slots=True, repr=True, eq=False)  # eq=False since cache is mutable
class DataExporter:
    """Exports list-of-dicts datasets to multiple formats with caching.

    This class uses attrs to eliminate boilerplate while maintaining mutable state
    for the cache. attrs generates __init__ and __repr__ automatically.

    - Supports CSV and JSON.
    - Uses cache with 1-hour TTL by default (can be overridden in ExportCache).
    - Returns text content; callers decide how/where to persist it.

    Thread Safety:
        This class uses ExportCache which is not thread-safe. For multi-threaded
        use, either provide a thread-safe cache implementation or use external
        synchronization when sharing a DataExporter instance across threads.
    """

    cache: ExportCache = attrs.field(
        factory=create_default_cache,
        metadata={"description": "Cache instance for storing export results"},
    )
    validate_input: bool = attrs.field(
        default=False,
        metadata={
            "description": "If True, validate input data structure using attrs (Boost's preferred approach)"
        },
    )

    def export(self, data: list[dict[str, Any]], export_format: ExportFormat) -> str:
        """Export to the requested format with basic validation and caching.

        Args:
            data: list of dictionaries representing rows.
            export_format: ExportFormat.CSV or ExportFormat.JSON.

        Returns:
            The exported textual representation.

        Raises:
            ValueError: when data is not a list[dict] or format unsupported.
            ValueError: when validate_input=True and data structure is invalid.
        """
        self._validate_data(data)

        # Optional validation using attrs (Boost's preferred approach)
        if self.validate_input:
            # This validates data structure matches ExportRecord schema
            # Raises ValueError if structure is invalid
            validate_and_convert_records(data, strict=False)

        # Compute cache key - necessary to check cache, but can be expensive for large datasets
        key = self._compute_cache_key(data, export_format)
        cached = self.cache.get(key)
        if cached is not None:
            return cached

        if export_format == ExportFormat.JSON:
            result = self._to_json(data)
        elif export_format == ExportFormat.CSV:
            result = self._to_csv(data)
        else:
            raise ValueError(f"Unsupported export format: {export_format}")

        self.cache.set(key, result)
        return result

    # -------------------- internals --------------------
    @staticmethod
    def _validate_data(data: Any) -> None:
        """Validate that data is a list of dictionaries."""
        if not isinstance(data, list):
            raise ValueError("data must be a list of dictionaries")
        for idx, row in enumerate(data):
            if not isinstance(row, dict):
                raise ValueError(f"data[{idx}] is not a dict")

    @staticmethod
    def _json_default(obj: Any) -> str:
        """JSON serializer for datetime objects."""
        if isinstance(obj, (datetime, date, time)):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    @staticmethod
    def _compute_cache_key(data: list[dict[str, Any]], export_format: ExportFormat) -> str:
        """Compute a stable key from canonical JSON + format name."""
        try:
            payload = json.dumps(
                data,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                default=DataExporter._json_default,
            )
        except TypeError:
            # For non-JSON-serializable objects, use repr as fallback.
            # This may cause cache misses for equivalent objects with different reprs,
            # but ensures the export can still proceed.
            payload = repr(data)
        raw = f"{export_format.value}:{payload}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    @classmethod
    def _to_json(cls, data: list[dict[str, Any]]) -> str:
        """Convert data to JSON string."""
        if not data:
            return "[]"  # empty edge case
        try:
            return json.dumps(data, ensure_ascii=False, default=cls._json_default)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Failed to encode JSON: {e}") from e

    @staticmethod
    def _to_primitive(value: Any) -> str | int | float | bool:
        """Best-effort conversion for CSV cells.

        - None -> ""
        - primitives unchanged
        - datetime/date/time -> ISO 8601 string
        - other structures JSON-encoded, with str() as last resort
        """
        if value is None:
            return ""
        if isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, (datetime, date, time)):
            return value.isoformat()
        try:
            return json.dumps(value, ensure_ascii=False)
        except TypeError:
            return str(value)

    def _to_csv(self, data: list[dict[str, Any]]) -> str:
        if not data:
            return ""  # empty edge case: schema cannot be inferred

        # Column order: first row's keys, then any new keys appended in discovery order.
        header = list(data[0].keys())
        seen = set(header)
        for row in data:
            for k in row.keys():
                if k not in seen:
                    header.append(k)
                    seen.add(k)

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=header, extrasaction="ignore")
        writer.writeheader()
        for row in data:
            safe_row = {k: self._to_primitive(row.get(k)) for k in header}
            writer.writerow(safe_row)
        return buf.getvalue()
