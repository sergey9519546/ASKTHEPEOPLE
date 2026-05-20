## 2024-06-25 - ZepToolsService caching
**Learning:** `ZepToolsService` is instantiated per API request in the Flask application, making instance-level decorators like `@lru_cache` ineffective for cross-request caching.
**Action:** Use a thread-safe, class-level cache (`_nodes_cache`, `_edges_cache` with `threading.Lock()`) in `ZepToolsService` to enable data sharing across instances and avoid redundant, slow API calls.
