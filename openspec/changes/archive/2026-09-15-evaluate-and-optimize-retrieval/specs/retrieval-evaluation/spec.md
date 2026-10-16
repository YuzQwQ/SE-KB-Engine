## ADDED Requirements

### Requirement: Versioned retrieval benchmark
The project SHALL maintain a reviewable offline benchmark with query, intent, relevant item judgments, hard negatives, and no-answer cases plus a dataset version.

#### Scenario: Benchmark run without services
- **WHEN** the evaluator runs with fixture embeddings/indexes
- **THEN** it completes without network or paid APIs and produces deterministic ranking metrics

### Requirement: Multidimensional measurement
Each candidate retrieval configuration SHALL report Recall@k, MRR, nDCG, no-answer accuracy, p50/p95 latency, peak memory, token usage, and estimated cost where applicable.

#### Scenario: Candidate comparison
- **WHEN** a candidate is compared with baseline
- **THEN** the report identifies metric deltas, configuration fingerprints, dataset version, and whether gates passed

### Requirement: Reproducible benchmark artifact
Benchmark outputs SHALL include commit/dirty state, environment, dependency, data, chunker, embedding, index, query-planner, and random-seed metadata.

#### Scenario: Missing fingerprint
- **WHEN** required reproducibility metadata cannot be determined
- **THEN** the run is marked incomplete rather than accepted as a release baseline
