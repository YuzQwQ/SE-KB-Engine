# Retrieval optimization

## Purpose

Define compatible index reuse, safe index lifecycle, bounded queries, and evidence-gated promotion of retrieval improvements.

## Requirements

### Requirement: Compatible index reuse
An index SHALL declare its source, chunker, embedding model, vector dimension, normalization, distance metric, schema, and collection versions and SHALL reject incompatible reuse.

#### Scenario: Embedding dimension mismatch
- **WHEN** a runtime attempts to load an index with a different configured embedding dimension
- **THEN** loading fails safely with a rebuild instruction and does not query mixed vectors

### Requirement: Safe index lifecycle
Index workflows SHALL support full, incremental, validation, dry-run, and stale-item removal modes without overwriting the only validated index.

#### Scenario: Failed index build
- **WHEN** embedding or storage fails during a new build
- **THEN** the active validated index remains available and the partial build is marked invalid

### Requirement: Bounded query execution
Retrieval and planning SHALL bound top-k, subquery count, concurrency, time, token use, filters, and reranking work.

#### Scenario: Excessive requested top-k
- **WHEN** a caller requests work above configured limits
- **THEN** the request is rejected or clamped according to the documented boundary contract

### Requirement: Evidence-gated optimization
A retrieval optimization SHALL be enabled by default only if it meets declared quality non-regression and resource budgets on the versioned benchmark.

#### Scenario: Faster but less relevant candidate
- **WHEN** a candidate improves latency but exceeds the allowed relevance regression
- **THEN** it is not promoted to the default configuration
