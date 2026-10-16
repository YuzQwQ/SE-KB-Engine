# Repository asset policy and open decisions

## Tracked binary and local-state risks

### `cloudflared.exe`

The approximately 68 MB Windows executable is currently tracked. Keeping it in Git makes checkout self-contained but enlarges clones, obscures provenance, and requires manual security updates. Safer options are a checksummed download script or a signed release asset. Moving it or rewriting history is intentionally deferred until the owner approves a distribution strategy.

### `web_cache.db`

The tracked SQLite file appears to be runtime URL/content state rather than a portable fixture. Keeping it in Git risks nondeterministic behavior and accidental publication of browsing metadata. A future migration should replace it with a tiny synthetic fixture if tests need one, then move runtime state to a configured ignored data root. No data was deleted or rewritten in this change.

### `se_kb/`

The current ignore rule hides the entire knowledge tree even though its comment says schemas, rules, and templates should be versioned. The directory currently contains hundreds of user/data files, so globally unignoring it would flood the working tree and risk accidental commits. The artifact-versioning change must classify public schemas/fixtures versus private/generated corpus before narrowing this rule.

## Ignored runtime classes

Virtual environments, caches, logs, coverage output, `.env`/keys/certificates, local databases, raw crawl data, generated output, Tor state, and vector artifacts remain ignored. Formal `tests/` are no longer ignored; generated `test_output/` remains excluded by the encoding scanner and should be treated as runtime output.

## Required approval

Deleting a tracked binary/database, unignoring or committing the existing corpus, rewriting Git history, or migrating the only data/index copy requires an explicit owner decision and a backup/rollback plan.
