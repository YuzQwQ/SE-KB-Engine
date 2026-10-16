# Artifact inventory (read-only, 2026-09-15)

No corpus file was changed while producing this inventory.

| Root | Files | JSON | Bytes | Observed variants | Integrity result |
| --- | ---: | ---: | ---: | --- | --- |
| `data/` | 1,626 | 1,619 | 193,672,244 | raw/parsed pages, URL index, embedding/cache JSON, Chroma data | 0 corrupt/missing issues; 4 byte-identical groups |
| `se_kb/` | 957 | 839 | 33,841,946 | artifact batches, refined type JSON, schemas, rules/mappings, Chroma SQLite/HNSW | 156 legacy metadata/parsed records; 0 corrupt/missing issues; 37 duplicate groups |
| `output/` | 27 | 0 | 5,143,298 | generated DOCX/PDF/Markdown/images | outside knowledge-manifest migration scope |

The current corpus has no versioned batch manifests. The operational legacy artifact variant is a
directory containing `metadata.json`, `parsed.json`, optional trace/metrics/error JSON, and one or
more type-specific knowledge JSON files. Standalone refined knowledge JSON and vector inputs form a
second consumer-facing variant. Chroma databases and HNSW binary files are derived indexes and must
be rebuilt or copied as explicitly derived data, never interpreted as source manifests.

Observed JSON parsed successfully in the read-only scan. Duplicate groups are candidates, not an
authorization to delete: identical bytes or shared content identity may represent intentional
provenance from separate crawl runs. The fixture corpus additionally covers corrupt, incomplete,
duplicate, orphan, current-v1, and legacy-v0 cases so scanner behavior is exercised even though the
real snapshot did not contain parse corruption.

## Consumers

- `utils/webpage_storage.py` and `writers/artifacts_writer.py` create raw, parsed, and artifact files.
- `extractors/` and `scripts/universal_knowledge_processor.py` produce type-specific structured data.
- `refiner/` reads artifacts and produces merged/refined knowledge.
- `vectorizer/` and `scripts/build_vector_index.py` consume refined/type JSON into Chroma indexes.
- `web/services.py`, MCP tools in `server.py`, and diagnostic/query scripts enumerate or expose them.

New manifests therefore use dual-read migration: legacy input remains byte-identical; v1 output is
written to a separate target; the manifest is the final commit marker; vector indexes remain
rebuildable derived state.
