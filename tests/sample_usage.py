"""
Sample usage examples with the real dataset from data.py.

This file demonstrates how to use the DataExporter with the provided 1000-item dataset.
It can be run directly to see the exporter in action.

Run with: uv run python tests/sample_usage.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add parent directory to path to import data module
sys.path.insert(0, str(Path(__file__).parent.parent))

from boost_exporter import DataExporter, ExportCache, ExportFormat

# Import the dataset
from data import data


def example_basic_export() -> None:
    """Basic example: Export data to JSON and CSV."""
    print("=" * 60)
    print("Example 1: Basic Export")
    print("=" * 60)

    exporter = DataExporter()

    # Export to JSON
    json_output = exporter.export(data, ExportFormat.JSON)
    print(f"JSON export: {len(json_output):,} characters")
    print(f"First 150 chars: {json_output[:150]}...\n")

    # Export to CSV
    csv_output = exporter.export(data, ExportFormat.CSV)
    lines = csv_output.splitlines()
    print(f"CSV export: {len(lines)} lines (1 header + {len(lines)-1} data rows)")
    print(f"Header: {lines[0]}")
    print(f"First row: {lines[1][:100]}...\n")


def example_caching() -> None:
    """Example: Demonstrating cache behavior."""
    print("=" * 60)
    print("Example 2: Cache Behavior")
    print("=" * 60)

    exporter = DataExporter()

    # First export - will compute and cache
    print("First export (will compute and cache)...")
    import time
    start = time.time()
    json_output1 = exporter.export(data, ExportFormat.JSON)
    first_time = time.time() - start
    print(f"Time taken: {first_time:.4f} seconds")
    print(f"Output size: {len(json_output1):,} bytes\n")

    # Second export - should use cache (much faster)
    print("Second export (should use cache)...")
    start = time.time()
    json_output2 = exporter.export(data, ExportFormat.JSON)
    second_time = time.time() - start
    print(f"Time taken: {second_time:.4f} seconds")
    print(f"Output size: {len(json_output2):,} bytes")
    print(f"Cache hit: {json_output1 == json_output2}")
    print(f"Speedup: {first_time / second_time:.1f}x faster\n")


def example_custom_cache() -> None:
    """Example: Using a custom cache configuration."""
    print("=" * 60)
    print("Example 3: Custom Cache Configuration")
    print("=" * 60)

    # Create cache with custom TTL (30 minutes) and smaller size limit
    custom_cache = ExportCache(ttl_seconds=1800, max_size=100)
    exporter = DataExporter(cache=custom_cache)

    print(f"Cache TTL: {custom_cache.ttl_seconds} seconds ({custom_cache.ttl_seconds // 60} minutes)")
    print(f"Cache max size: {custom_cache.max_size} entries\n")

    # Export data
    json_output = exporter.export(data, ExportFormat.JSON)
    print(f"Exported {len(data)} items to JSON")
    print(f"Output size: {len(json_output):,} bytes\n")


def example_save_to_files() -> None:
    """Example: Export and save to files."""
    print("=" * 60)
    print("Example 4: Save to Files")
    print("=" * 60)

    exporter = DataExporter()
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    # Export to JSON and save
    json_output = exporter.export(data, ExportFormat.JSON)
    json_file = output_dir / "export.json"
    json_file.write_text(json_output, encoding="utf-8")
    print(f"Saved JSON to: {json_file}")
    print(f"File size: {json_file.stat().st_size:,} bytes\n")

    # Export to CSV and save
    csv_output = exporter.export(data, ExportFormat.CSV)
    csv_file = output_dir / "export.csv"
    csv_file.write_text(csv_output, encoding="utf-8")
    print(f"Saved CSV to: {csv_file}")
    print(f"File size: {csv_file.stat().st_size:,} bytes\n")

    # Verify files can be read back
    print("Verifying files can be read back...")
    loaded_json = json.loads(json_file.read_text(encoding="utf-8"))
    print(f"JSON file contains {len(loaded_json)} items")
    print(f"First item keys: {list(loaded_json[0].keys())}\n")


def example_datetime_handling() -> None:
    """Example: Demonstrating datetime serialization."""
    print("=" * 60)
    print("Example 5: Datetime Handling")
    print("=" * 60)

    exporter = DataExporter()

    # Show original datetime object
    first_item = data[0]
    original_datetime = first_item["created_at"]
    print(f"Original datetime object: {original_datetime}")
    print(f"Type: {type(original_datetime)}\n")

    # Export to JSON - datetime becomes ISO string
    json_output = exporter.export(data, ExportFormat.JSON)
    parsed = json.loads(json_output)
    json_datetime = parsed[0]["created_at"]
    print(f"JSON datetime (ISO string): {json_datetime}")
    print(f"Type: {type(json_datetime)}\n")

    # Export to CSV - datetime becomes ISO string
    csv_output = exporter.export(data, ExportFormat.CSV)
    import csv as csv_module
    import io
    rows = list(csv_module.DictReader(io.StringIO(csv_output)))
    csv_datetime = rows[0]["created_at"]
    print(f"CSV datetime (ISO string): {csv_datetime}")
    print(f"Type: {type(csv_datetime)}\n")


def example_subset_export() -> None:
    """Example: Exporting a subset of the data."""
    print("=" * 60)
    print("Example 6: Exporting Subset")
    print("=" * 60)

    exporter = DataExporter()

    # Export first 10 items
    subset = data[:10]
    json_output = exporter.export(subset, ExportFormat.JSON)
    parsed = json.loads(json_output)

    print(f"Exported {len(subset)} items")
    print(f"Output size: {len(json_output):,} bytes")
    print(f"\nFirst 3 items:")
    for i, item in enumerate(parsed[:3], 1):
        print(f"  {i}. {item['event_type']} - {item['sku_name'][:40]}...")
    print()


def main() -> None:
    """Run all examples."""
    print("\n" + "=" * 60)
    print("DataExporter Sample Usage Examples")
    print(f"Using dataset with {len(data)} items")
    print("=" * 60 + "\n")

    example_basic_export()
    example_caching()
    example_custom_cache()
    example_save_to_files()
    example_datetime_handling()
    example_subset_export()

    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()

