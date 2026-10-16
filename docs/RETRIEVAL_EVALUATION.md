# Offline retrieval evaluation and index operations

## Benchmark contract

The retrieval benchmark is deliberately local, deterministic, and free of paid or
network dependencies. Its reviewable dataset is version `1.0.0`:

- `tests/fixtures/retrieval/documents.jsonl` contains minimal licensed or desensitized
  DFD/software-engineering passages with stable IDs, type, source, date, and quality.
- `tests/fixtures/retrieval/queries.jsonl` contains Chinese, English, mixed, ambiguous,
  long, and no-answer queries with intent, graded relevance, hard negatives, and a
  `dev` or `holdout` split.
- `schemas/retrieval-document-v1.schema.json` and
  `schemas/retrieval-query-v1.schema.json` define the row formats.

Changes to text or judgments require review, a dataset-version increment, and a fresh
baseline. Add real failure clusters after desensitization; do not copy private corpus
content into the fixture. Tune on `dev` only and inspect `holdout` only for a promotion
decision.

Run the promoted configuration with:

```powershell
.\.venv\Scripts\python.exe scripts\run_retrieval_benchmark.py --candidate hybrid --quiet
```

Use `--split holdout` for the holdout, or omit `--quiet` for the complete JSON report.
The report includes commit and dirty state, Python/platform, dependency-lock hash,
dataset/configuration/index/seed fingerprints, and per-query rankings. A missing
required fingerprint marks the report incomplete.

## Metrics

- Recall@k measures how much judged relevant material is present in the first `k`.
- MRR emphasizes the rank of the first relevant result.
- nDCG@k incorporates graded relevance and ordering.
- No-answer accuracy checks that unsupported questions return an explainable empty or
  low-confidence result.
- p50/p95 latency and peak traced memory measure local resource use.
- Input tokens and estimated cost expose model work; all current offline candidates
  have zero model cost.

The default no-answer threshold is `0.01`. Results below it are not presented as
knowledge. Candidate hits retain explanations such as lexical match, hash-vector
cosine, reciprocal-rank fusion, and modality-diversity rescue.

## Experiments and promotion decision

The vector-only/direct-query report is the frozen baseline. Experiments cover document
and 40/10 and 80/20 chunking, structural source/parent metadata, BM25 lexical retrieval,
weighted hybrid fusion, filters, bounded planning, and deterministic reranking. Reports
and comparison artifacts live in `docs/baseline/retrieval-*-2026-09-15.json`.

Promotion gates were declared before selection: no Recall@5 or MRR regression, at most
`0.01` absolute nDCG regression, no-answer accuracy at least `0.8`, p95 latency at most
50 ms, peak traced memory at most 32 MiB, and estimated cost of zero. Both `dev` and
`holdout` must pass.

The `hybrid` candidate is promoted as the offline default. It passed both splits,
retained holdout Recall@5/MRR/nDCG, and improved holdout no-answer accuracy from `0.667`
to `1.0`. Pure lexical and hybrid-rerank passed `dev` but failed the holdout recall/nDCG
gates; their reports are retained as negative evidence and they are not defaults.

Compare any candidate with the same declared gates:

```powershell
.\.venv\Scripts\python.exe scripts\compare_retrieval_reports.py <baseline.json> <candidate.json>
```

## Filters and query bounds

Supported filters are `kind`, exact `source`, inclusive `date_from`/`date_to`, and
`min_quality`. Unknown filters fail closed. Filtering is applied before scoring and
cannot expand a result set or change a document's declared metadata.

Default query bounds are top-k 20, four subqueries, two concurrent searches, two
seconds, 512 whitespace-estimated input tokens, and 20 rerank candidates. Excessive
top-k is clamped; invalid top-k and oversized inputs are rejected. Empty plans fall back
to the original query. Timeouts and dependency failures use the direct-query fallback,
and the response records that fallback.

## Index compatibility and lifecycle

`schemas/index-manifest-v1.schema.json` defines an index manifest binding the source
manifest, chunker version, embedding model and dimension, normalization, distance
metric, schema version, and collection mapping. Loaders reject any mismatch with an
instruction to rebuild into a new target; mixed vectors are never queried.

The index command defaults to a write-free dry run:

```powershell
.\.venv\Scripts\python.exe scripts\build_retrieval_index.py <index-root> <index-id>
```

Available modes are `dry-run`, `full`, `incremental`, and `validate-only`. Full and
incremental builds require an explicit `--mode`; add `--switch` only when the validated
new index should atomically become active. Builds preflight disk space, create a new
index directory, track source IDs, remove stale IDs deterministically from the new
snapshot, write an `INVALID` marker during construction, validate after construction,
and atomically replace the active pointer. Existing active indexes are never overwritten
or automatically deleted.

Readers resolve the active pointer under a process lock and therefore observe a complete
old or complete new snapshot during concurrent builds and switches. A failed build keeps
the prior pointer and leaves the new target marked `INVALID`.

Rollback means atomically switching the pointer back to the prior validated index ID.
After readers confirm the old index, quarantine the failed/new target according to the
artifact retention policy. Do not delete the only validated index. The index manager has
only been exercised against temporary test roots in this change; the repository's active
Chroma store was not modified.

## Reproduction and maintenance

The full offline quality command runs the promoted benchmark and all fault/concurrency
tests:

```powershell
.\.venv\Scripts\python.exe scripts\quality.py
```

When changing chunking, embeddings, collection mappings, query planning, thresholds,
filters, fusion, or reranking: assign a new version/fingerprint, build separately, run
both splits, retain passing and failing reports, and promote only after every gate passes.
