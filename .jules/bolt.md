## 2025-05-11 - Optimize ZepToolsService get_all_nodes and get_all_edges
**Learning:** ZepToolsService is frequently instantiated per API request in the Flask application, meaning instance-level caching methods (like `@lru_cache`) are ineffective.
**Action:** Use a class-level dictionary cache with a lock (`threading.Lock()`) and TTL to share data across instances and significantly reduce redundant API calls to the Zep cloud when resolving graphs.
