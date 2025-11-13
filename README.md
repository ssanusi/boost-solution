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

## Project Layout

```
boost-solution/
├── src/boost_exporter/    # Package code
│   ├── __init__.py
│   ├── exporter.py         # DataExporter class
│   ├── cache.py            # ExportCache class
│   └── formats.py          # ExportFormat enum
├── tests/                  # pytest unit tests
│   └── test_exporter.py
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
