# boost-exporter

Data export module implementing:

- **Option 1**: Multi-format support (CSV and JSON)
- **Option 2**: Caching support with a 1-hour TTL and LRU eviction

## Features

- **Multi-format export**: Supports CSV and JSON formats with proper type handling
- **Intelligent caching**: SHA-256 based cache keys with configurable TTL (default: 1 hour)
- **LRU eviction**: Prevents unbounded memory growth with configurable cache size limit (default: 1000 entries)
- **Robust error handling**: Validates input data and provides clear error messages
- **Edge case handling**: Handles empty datasets, missing values, heterogeneous schemas, and datetime objects
- **Structured data validation** (optional): Uses `attrs` for runtime validation and type safety (Boost's preferred approach)

## Quick Start

### Prerequisites

Install `uv` (see [uv documentation](https://docs.astral.sh/uv/)).

### Setup

1. **Create virtual environment** (optional; uv can also run ephemeral envs):
   ```bash
   uv venv
   ```

2. **Install dependencies** (installs project and test deps):
   ```bash
   uv sync --extra dev
   ```

3. **Run tests**:
   ```bash
   uv run -m pytest -q
   ```

### Example Usage

```python
from boost_exporter import DataExporter, ExportFormat

data = [
    {"id": 1, "name": "Ada"},
    {"id": 2, "name": "Grace", "lang": "COBOL"},
]

exp = DataExporter()
print(exp.export(data, ExportFormat.JSON))  # JSON string
print(exp.export(data, ExportFormat.CSV))   # CSV string
```

### Advanced Usage

```python
from boost_exporter import DataExporter, ExportCache, ExportFormat

# Custom cache with different TTL and size limit
cache = ExportCache(ttl_seconds=7200, max_size=500)
exporter = DataExporter(cache=cache)

data = [{"id": i, "value": i * 2} for i in range(100)]
result = exporter.export(data, ExportFormat.JSON)
```

### Structured Data Validation (attrs)

The solution includes optional structured data validation using `attrs`, which is commonly used in Boost codebases:

```python
from boost_exporter import DataExporter, ExportFormat, ExportRecord, validate_and_convert_records
from datetime import datetime

# Option 1: Use structured ExportRecord models
records = [
    ExportRecord(
        event_type="Receive",
        location_name="Warehouse",
        sku_name="Product ABC",
        quantity=10,
        value=1000,
        created_at=datetime.now()
    )
]

# Convert to dicts for export
data = [r.to_dict() for r in records]
exporter = DataExporter()
result = exporter.export(data, ExportFormat.JSON)

# Option 2: Enable validation in exporter
exporter = DataExporter(validate_input=True)
# This will validate data structure matches ExportRecord schema
result = exporter.export(data, ExportFormat.JSON)

# Option 3: Use validate_and_convert_records for conversion/validation
validated_data = validate_and_convert_records(raw_data, strict=False)
# Or convert to ExportRecord objects
records = validate_and_convert_records(raw_data, strict=True)
```

## Design Notes

### Export Behavior

- `DataExporter.export()` returns a string for both formats, leaving persistence/IO to callers
- CSV header is derived from the first row's keys; unseen keys in later rows are appended to preserve a stable, human-friendly order
- Handles heterogeneous schemas gracefully by union-ing all keys across rows

### Caching

- Cache keys are computed as SHA-256 hashes of a canonical JSON representation of the input data plus the format
- Export results are cached for 1 hour by default (configurable via `ExportCache(ttl_seconds=...)`)
- LRU eviction prevents memory issues when cache size limit is reached (default: 1000 entries)
- Cache keys are stable: same data with different key order produces the same cache key

### Edge Cases

- **Empty data**: JSON returns `"[]"`; CSV returns `""` (no header can be inferred)
- **Missing values**: CSV handles missing keys by outputting empty strings
- **None values**: JSON preserves `null`; CSV converts to empty string
- **Datetime objects**: Automatically serialized to ISO 8601 format in both JSON and CSV
- **Large datasets**: Tested with 1000+ items; cache prevents redundant processing

### Type Safety

- Full type hints throughout using modern Python 3.9+ syntax (`list[dict[str, Any]]`)
- Input validation ensures data is a list of dictionaries
- Clear error messages for invalid inputs
- **Optional structured validation**: Uses `attrs` for runtime validation and data transformation (Boost's preferred approach)
  - `ExportRecord` class provides immutable, validated data models
  - `validate_and_convert_records()` function for structured validation/conversion
  - Can be enabled via `DataExporter(validate_input=True)` for automatic validation

## Project Layout

```
boost-solution/
├── src/boost_exporter/    # Package code
│   ├── __init__.py
│   ├── exporter.py         # DataExporter class
│   ├── cache.py            # ExportCache class
│   ├── formats.py          # ExportFormat enum
│   └── models.py           # ExportRecord (attrs) and validation utilities
├── tests/                  # pytest unit tests
│   ├── test_exporter.py
│   └── test_models.py      # Tests for attrs models
├── pyproject.toml          # Project metadata and dependencies
└── README.md
```

## Testing

The test suite includes:

- Basic export functionality (JSON and CSV)
- Cache hit/miss behavior
- Cache expiration (TTL)
- LRU eviction
- Edge cases (empty data, missing values, None values)
- Datetime serialization
- Large dataset handling (1000+ items)
- Input validation
- Cache key stability
- Structured data validation (attrs models)

Run tests with:
```bash
uv run -m pytest -q
```

## Requirements Met

✅ Multi-format support (CSV and JSON)
✅ Caching with 1-hour TTL
✅ Edge case handling (empty data)
✅ Clear type hints throughout
✅ Comprehensive test coverage
✅ Well-documented code with docstrings
✅ README with setup instructions
✅ `pyproject.toml` for dependency management
✅ Uses `uv` for package management
