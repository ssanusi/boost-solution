# Code Review Preparation Guide

This guide is designed to help you explain your solution confidently during your code review. It covers the architectural choices, a line-by-line breakdown of key components, and answers to potential interview questions.

## 1. Executive Summary

**Selected Options:**

1.  **Option 1: Multi-format support** (CSV & JSON)
2.  **Option 2: Caching support** (In-memory with TTL & LRU)

**Key Technologies:**

- **`uv`**: For fast, modern dependency management (as requested).
- **`attrs`**: For writing concise, correct classes with less boilerplate (validation, `__repr__`, `__init__`).
- **`pytest`**: For comprehensive testing.

---

## 2. Code Walkthrough

### A. `src/boost_exporter/exporter.py` (The Core)

This is the main entry point.

- **Lines 1-15**: Imports. Note `from __future__ import annotations` for modern type hinting.
- **Lines 22-48 (`DataExporter` class definition)**:
  - Uses `@attrs.define`. `slots=True` for memory efficiency, `eq=False` because it holds mutable state (the cache).
  - `cache`: Injected dependency. Defaults to a new `ExportCache`. This allows for easy testing (mocking) and flexibility (swapping cache backends).
  - `validate_input`: Feature flag to enable strict schema validation using `attrs` models.
- **Lines 50-86 (`export` method)**:
  - **Validation**: Calls `_validate_data` (basic list-of-dicts check) and optionally `validate_and_convert_records` (strict schema).
  - **Caching**: Computes a key -> checks cache -> returns if hit.
  - **Logic**: Dispatches to `_to_json` or `_to_csv`.
  - **Write-through**: Saves result to cache before returning.
- **Lines 106-122 (`_compute_cache_key`)**:
  - **Strategy**: Canonical JSON string + Format Name -> SHA-256.
  - **Why?**: Ensures that `{a:1, b:2}` and `{b:2, a:1}` produce the same key (`sort_keys=True`).
  - **Trade-off**: Serialization for the key can be expensive for massive datasets, but guarantees correctness.
- **Lines 154-173 (`_to_csv`)**:
  - **Robustness**: It doesn't just assume all rows have the same keys. It iterates _all_ rows to build a superset of all keys (`seen` set) to ensure no data is lost if schemas are heterogeneous.
  - **Ordering**: Preserves order of keys from the first row, then appends new ones.

### B. `src/boost_exporter/cache.py` (The Cache)

- **Lines 17-45 (`ExportCache` class)**:
  - **Storage**: Uses `OrderedDict`. This is the "secret sauce" for easy LRU (Least Recently Used) implementation.
  - **TTL**: `ttl_seconds` determines how long an item stays valid.
  - **Max Size**: `max_size` prevents memory leaks.
- **Lines 47-71 (`get`)**:
  - Checks if key exists.
  - **Lazy Expiration**: Checks TTL _on access_. If expired, removes it.
  - **LRU Logic**: `self._store.move_to_end(key)` marks it as recently used.
- **Lines 73-95 (`set`)**:
  - **Eviction**: If full (`len >= max_size`), `popitem(last=False)` removes the _oldest_ (least recently used) item.

### C. `src/boost_exporter/models.py` (The "Bonus" - Structured Data)

- **Why this exists**: Shows you go beyond basic requirements. It uses `attrs` for runtime validation and type conversion.
- **Features**:
  - **Converters**: `"10"` (str) -> `10` (int).
  - **Validators**: `quantity` must be positive.
  - **Metadata**: Field descriptions.

---

## 3. Anticipated Interview Questions & Answers

### Q1: Why did you choose `attrs` instead of standard Python `dataclasses` or Pydantic?

**Answer:**
"I chose `attrs` because it offers a great balance of features and performance. While `dataclasses` are built-in, `attrs` provides more powerful features like validators, converters, and slot classes by default (which save memory). Pydantic is excellent but can be heavier; `attrs` fits this 'library' use case perfectly where we want lightweight but robust objects. Plus, the prompt mentioned Boost are fans of it!"

### Q2: Is your cache implementation thread-safe?

**Answer:**
"Yes, it is. I implemented thread safety using a `threading.RLock` (Reentrant Lock) in the `ExportCache` class. Both `get` and `set` operations acquire this lock to ensure that the underlying `OrderedDict` is accessed atomically. This allows the `DataExporter` to be safely shared across multiple threads in a web server environment."

### Q3: How does your CSV exporter handle 1 million rows?

**Answer:**
"Currently, `_to_csv` builds the entire string in memory using `io.StringIO`. For 1 million rows, this would likely cause an `MemoryError`. To fix this, I would:

1.  Change the API to return a **generator** or **iterator** instead of a single string.
2.  Stream the output row-by-row.
3.  For the 'header discovery' problem (needing to know all keys upfront), I'd either require the user to provide a schema or perform a 'two-pass' approach (one pass to find keys, one to write)."

### Q4: Why do you hash the _entire_ dataset for the cache key? Isn't that slow?

**Answer:**
"Yes, it's O(N). For a 'reporting tool' use case, correctness is paramount—we must ensure the cached result exactly matches the input. If we only hashed an ID or timestamp, we might miss subtle data changes. However, for very large datasets, this is a bottleneck. A better approach in a real system might be to require the caller to provide a unique `version_id` or `hash` if they already have one, or use a content-addressable storage system."

### Q5: Explain the `uv` choice.

**Answer:**
"`uv` is an extremely fast, modern Python package manager written in Rust. It replaces `pip`, `pip-tools`, and `virtualenv`. It ensures reproducible builds via `uv.lock` and makes setup for other developers instantaneous. It aligns with the requirement for a standalone, easily runnable solution."

---

## 4. Areas for Improvement (Self-Critique)

If asked "What would you do differently if you had more time?", use these:

1.  **Streaming Support**: As mentioned, return iterators/generators for large files.
2.  **Async I/O**: If fetching data from a DB, `async def export(...)` would allow non-blocking operations.
3.  **Pluggable Backends**: Define an abstract `CacheBackend` protocol so users can easily swap `InMemoryCache` for `RedisCache` or `Memcached` without changing the `DataExporter` code.
4.  **Configuration**: Load TTL and max_size from environment variables or a config file.

---

## 5. Additional Study Topics

To ace the "Senior" part of the interview, be prepared to discuss these broader concepts:

### Python Internals

- **GIL (Global Interpreter Lock)**: Why it exists and how it affects CPU-bound vs I/O-bound tasks. (Your exporter is CPU-bound during serialization, so threading only helps if you were doing I/O).
- **Memory Management**: Reference counting vs Garbage Collection.
- **Generators**: How `yield` works and why it's crucial for memory efficiency with large datasets.

### System Design

- **Caching Strategies**:
  - **Write-through** (what you implemented): Data is written to cache and DB/Storage at the same time.
  - **Write-back**: Data written to cache first, then async to DB (faster, riskier).
  - **Cache Stampede**: What happens if 100 requests hit a missing cache key at once? (Solution: Locking or "Probabilistic Early Expiration").
- **Scaling**: How would this module run in a distributed system? (You'd need a shared cache like Redis instead of in-memory `OrderedDict`).

### Testing

- **Mocking**: When to mock (external services) vs when not to (logic).
- **TDD**: Did you write tests first? (Even if you didn't, knowing the philosophy helps).
- **Fixtures**: How `pytest` fixtures help keep tests clean.

### General Engineering

- **SOLID Principles**: Be able to map your code to these (e.g., **S**ingle Responsibility: `DataExporter` exports, `ExportCache` caches).
- **Big O Notation**:
  - Cache Access: O(1)
  - Export: O(N) where N is number of records.
  - Cache Key Generation: O(N) (This is the most expensive part of your cache logic).

---

## 6. Further Reading & References

### Project Specifics

- **attrs**: [attrs by Example](https://www.attrs.org/en/stable/examples.html) - Essential since you used it heavily.
- **uv**: [uv Documentation](https://docs.astral.sh/uv/) - Read the "Why uv?" section to explain your choice.
- **Python Threading**: [An Intro to threading](https://realpython.com/intro-to-python-threading/) - To explain your `RLock` implementation.

### General Interview Prep

- **System Design**: [The System Design Primer](https://github.com/donnemartin/system-design-primer) - The gold standard for "How would you scale this?" questions.
- **Python GIL**: [What is the Python GIL?](https://realpython.com/python-gil/) - Crucial for explaining why threading doesn't make your CPU-bound export faster.
- **Caching**: [Caching Strategies and Patterns](https://aws.amazon.com/caching/best-practices/) - Good overview of write-through vs write-back.

---

## 7. Mock Reviewer Critique

If I were reviewing your code, here is exactly what I would say. Use this to prepare your defense!

### The Good (Strengths)

- **"Great choice on `attrs`."**: It shows you care about reducing boilerplate and enforcing correctness without me having to ask for it.
- **"Clean, readable code."**: The type hints are consistent, and the method names (`_to_csv`, `_compute_cache_key`) are self-explanatory.
- **"Solid testing."**: You didn't just test the happy path; you tested edge cases like empty data and missing keys.

### The "Nitpicks" (Constructive Criticism)

- **Memory Usage in CSV**: "I noticed `_to_csv` writes to a `StringIO` and returns the whole string. If we export 100k rows, that's going to spike memory. In a real production app, I'd ask you to yield lines or write to a file-like object directly."
  - _Your Defense_: "Agreed. For this exercise, I prioritized simplicity and the requested `-> str` signature. For production, I'd switch to a generator."
- **Cache Key Performance**: "Hashing the entire JSON dump is O(N). For large datasets, we spend more time hashing than we save by caching. Have you considered allowing the caller to pass a `version_id`?"
  - _Your Defense_: "That's a valid point. I chose correctness over raw speed here to guarantee the cache never serves stale data, but a `version_id` override would be a great optimization."
- **Lock Contention**: "The `RLock` makes it thread-safe, but it locks the _entire_ cache for every read/write. Under high load, this could become a bottleneck."
  - _Your Defense_: "True. For higher concurrency, I'd move to Redis (as implemented in the feature branch) or use a sharded in-memory cache to reduce lock contention."

### The "Senior" Challenge Question

**"If this module causes a memory leak in production, how would you debug it?"**

- _Answer_: "I'd use `tracemalloc` to compare memory snapshots, or check if the `ExportCache` is growing indefinitely (though the `max_size` should prevent that). I'd also check if we are holding references to large strings in the `_store`."
