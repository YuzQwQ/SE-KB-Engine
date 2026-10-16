## Why

Retrieval changes cannot be called improvements without a stable relevance dataset and measurements for quality, latency, memory, and model cost. The current chunking, embedding, collection merging, query planning, and no-answer behavior need reproducible evaluation before optimization.

## What Changes

- Build a versioned offline evaluation set with queries, intents, relevance judgments, hard negatives, and no-answer cases.
- Measure Recall@k, MRR, nDCG, no-answer accuracy, p50/p95 latency, memory, token use, and estimated cost.
- Version chunk, embedding, index, distance, and collection metadata and reject incompatible index reuse.
- Evaluate chunking, metadata filters, hybrid retrieval, collection score calibration, bounded query planning, and optional reranking.
- Add incremental/full/dry-run index workflows, stale-vector cleanup, concurrency safety, and before/after regression gates.

Non-goals: selecting improvements by anecdote, requiring paid online evaluation in CI, replacing ChromaDB without evidence, or silently rebuilding the user's only index.

Prerequisites: `stabilize-runtime-and-quality` and `version-artifacts-and-extraction`; application seams from `modularize-application-core` are required for replaceable test components.

## Capabilities

### New Capabilities
- `retrieval-evaluation`: Retrieval behavior is measured reproducibly against versioned relevance, latency, memory, and cost baselines.
- `retrieval-optimization`: Chunking, indexing, planning, recall, ranking, filtering, and no-answer behavior improve behind compatibility and regression gates.

### Modified Capabilities

None.

## Impact

Affects `vectorizer/`, index build/query scripts, embedding caches, evaluation fixtures, benchmark reports, API/MCP retrieval responses, and related documentation. Existing vector stores are not overwritten without an explicit backup and migration step.
