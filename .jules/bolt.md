## 2024-06-25 - ZepToolsService caching
**Learning:** `ZepToolsService` is instantiated per API request in the Flask application, making instance-level decorators like `@lru_cache` ineffective for cross-request caching.
**Action:** Use a thread-safe, class-level cache (`_nodes_cache`, `_edges_cache` with `threading.Lock()`) in `ZepToolsService` to enable data sharing across instances and avoid redundant, slow API calls.

## 2026-11-01 - Eliminate N+1 query in ProjectRepository
**Learning:** In SQLAlchemy raw text queries, loading associated child records (like the latest completed ontology per project) iteratively in a Python loop incurs O(N) database round-trips.
**Action:** Use a SQL CTE with window function `ROW_NUMBER() OVER (PARTITION BY project_id ORDER BY updated_at DESC, id DESC)` and `bindparam("project_ids", expanding=True)` to batch-load the latest record per parent in a single O(1) query.
