
## 2024-05-18 - Optimize bulk database inserts
**Learning:** Calling `session.add()` and `session.flush()` inside a loop for each record results in poor performance due to repeated flush overhead. Creating an `add_many()` method that builds a list of models and calls `session.add_all(models)` followed by a single `session.flush()` significantly improves bulk insert performance.
**Action:** Implemented `add_many()` on `DocumentChunkRepository`, `DocumentTagRepository`, and `DocumentArtifactRepository` and used them in `cortex_parse/service.py` to optimize document ingestion.
