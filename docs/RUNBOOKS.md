# Operational runbooks

Always capture the correlation/job ID, safe error code, deployment version, readiness result, and recent low-cardinality metrics. Never paste credentials, private URLs, page text, prompts, or model bodies into tickets.

## Missing keys or model failure

Confirm only whether the relevant variable is configured, not its value. `/live` may remain healthy while readiness or a stage reports unconfigured/dependency-failed. Inject the key through the secret manager, restart gracefully, and run a bounded fake-data probe. For 401/403 rotate or correct the credential; for model incompatibility restore the previous model/config fingerprint.

## Proxy, Tor, or browser failure

Check `USE_TOR`, executable existence, proxy reachability, and Playwright installation separately. Keep private-network fetch disabled. Fall back to permitted static HTTP when policy allows. Do not disable SSRF checks to diagnose a proxy. External tests are explicit CI suites.

## Index failure

Inspect `/ready` and admin diagnostics, validate the index manifest/dimension/model/schema, and run validate-only. Build into a new target; never rebuild over the active index. On failed switch, select the prior validated ID and quarantine the `INVALID` target.

## Rate limit or exhausted budget

Use correlation and the `budget_events_total`/request metrics to identify the named limit. Reduce concurrency/work, wait for provider reset, or raise a limit only after capacity and cost review. Never add unbounded retries.

## Low disk or memory

Stop accepting new jobs, preserve active writes, and identify data by retention owner. Do not delete artifacts, logs, caches, indexes, or backups automatically. Expand storage or perform an approved, recoverable cleanup. Validate indexes/artifacts after recovery.

## Corrupt artifacts

Run `scripts/scan_artifacts.py <root> --json`. Quarantine affected new targets, keep scanning after errors, restore from backup if required, and preserve the report. Never repair the only copy in place; follow `ARTIFACT_LIFECYCLE.md`.

## Stuck jobs

Read the job state/events and queue depth. Request cooperative cancellation, allow the graceful deadline, and only then restart. Recovery marks abandoned running jobs interrupted; it must not report them as still running or silently resubmit paid/network work.

## Rollback

Stop new mutations, route traffic to the prior image, switch to the prior validated index, and verify liveness/readiness/auth and a fake-data query. Restore data only from the recorded pre-upgrade backup when migration changed it. Keep the failed state quarantined for diagnosis.
