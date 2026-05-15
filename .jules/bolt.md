## 2024-05-15 - Flask Service Class Caching
**Learning:** In Flask apps, service classes like `ZepToolsService` are often instantiated per request. This means instance-level caching (like `@lru_cache` on methods) is ineffective for cross-request caching, leading to redundant API calls for data that changes infrequently (like fetching all graph nodes or edges).
**Action:** Use thread-safe class-level variables (e.g., `_nodes_cache`, `threading.Lock()`) with a TTL and `copy.deepcopy` to share cached data across all instances and requests.
