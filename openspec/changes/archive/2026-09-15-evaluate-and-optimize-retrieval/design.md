## Context

The repository has chunking, embedding, Chroma storage, direct retrieval, and query planning but no agreed relevance benchmark. Quality and efficiency must be evaluated together and indexes must advertise compatibility.

## Goals / Non-Goals

**Goals:** offline evaluation; versioned index manifests; safe build modes; evidence-based retrieval improvements; latency/cost gates.

**Non-Goals:** replacing Chroma by preference, online paid CI, or silently mutating the production index.

## Decisions

1. Store a small versioned evaluation corpus and judgments in reviewable JSONL; keep raw licensed content minimal and attributed.
2. Provide one benchmark runner producing machine-readable results with environment/commit/config fingerprints.
3. Index manifests bind embedding model/dimension, normalization, distance, chunker, source manifest, and collection mapping.
4. Evaluate simple baselines first: vector-only, lexical-only, hybrid, then reranking. Adopt only changes that meet declared quality and resource budgets.
5. Build indexes into a new directory and atomically switch a pointer/reference after validation.

## Risks / Trade-offs

- [Small benchmark overfits] → retain a holdout and expand from real failure clusters.
- [Metrics hide user value] → include no-answer and qualitative review alongside ranking metrics.
- [New index doubles disk temporarily] → preflight disk space and never delete old index automatically.

## Migration Plan

Build evaluator and baseline; add index manifests/compatibility checks; test build/swap on temporary copies; run controlled experiments; adopt individually with regression thresholds. Rollback switches to the prior validated index/config.

## Open Questions

- What initial relevance judgments can be reviewed without exposing private corpus content?
