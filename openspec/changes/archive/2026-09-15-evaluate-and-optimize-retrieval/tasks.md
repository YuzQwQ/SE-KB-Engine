## 1. Evaluation corpus and metrics

- [x] 1.1 Define reviewable JSONL schemas for documents, queries, intents, graded relevance, hard negatives, no-answer cases, splits, and dataset version.
- [x] 1.2 Create a small desensitized seed corpus covering DFD terminology, Chinese/English variants, ambiguity, long questions, and no-answer cases.
- [x] 1.3 Implement deterministic Recall@k, MRR, nDCG, no-answer accuracy, p50/p95 latency, peak-memory, token, and estimated-cost calculations with unit tests.
- [x] 1.4 Build an offline benchmark CLI that emits JSON with commit/dirty, environment, dependency, dataset, configuration, index, and seed fingerprints.
- [x] 1.5 Run and preserve the current vector-only/direct-query baseline without modifying the active index.

## 2. Index identity and lifecycle

- [x] 2.1 Define an index manifest covering source manifest, chunker, embedding model/dimension, normalization, distance, schema, and collection mapping.
- [x] 2.2 Validate index compatibility at load time and test dimension/model/schema mismatch failure with rebuild guidance.
- [x] 2.3 Implement full, incremental, validate-only, and dry-run build modes against temporary targets.
- [x] 2.4 Track source IDs so updated/deleted documents remove stale chunks and vectors deterministically.
- [x] 2.5 Add disk preflight, partial-build invalidation, post-build validation, and atomic active-index switch with rollback.
- [x] 2.6 Test concurrent readers during build/switch/reload and preserve the prior validated index on failure.

## 3. Controlled retrieval experiments

- [x] 3.1 Benchmark chunk sizes/overlap and structural metadata while preserving stable parent/source relationships.
- [x] 3.2 Implement and benchmark a lexical/BM25 baseline using the same evaluation contract.
- [x] 3.3 Implement and benchmark hybrid fusion with calibrated scores across collections.
- [x] 3.4 Add type, source, date, and quality filters and test that filters cannot expand or mislabel results.
- [x] 3.5 Bound query-planner subqueries, concurrency, time, tokens, and failure fallback; compare short, explicit-intent, and complex queries.
- [x] 3.6 Evaluate optional reranking only after measuring remaining recall/ranking errors.
- [x] 3.7 Calibrate a no-answer threshold and expose explainable low-confidence behavior.

## 4. Promotion gates and documentation

- [x] 4.1 Define quality non-regression, latency, memory, and cost budgets before selecting a candidate.
- [x] 4.2 Generate before/after reports for every candidate and retain failed experiments as evidence without enabling them.
- [x] 4.3 Promote only a candidate that passes all declared gates; keep a configuration/index rollback path.
- [x] 4.4 Add the offline retrieval benchmark to the appropriate quality/CI tier with no paid or network requirement.
- [x] 4.5 Document benchmark curation, metric meaning, index compatibility/build/switch, query bounds, and reproduction commands.
