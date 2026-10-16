# Container operations, upgrade, and rollback

The image is built in stages from hashed `requirements-prod.txt`, runs as UID/GID 10001, and contains only the API runtime packages. The root filesystem is read-only. Data, cache, output, logs, and index are separate writable volumes; `/tmp` is a bounded tmpfs. Secrets are injected as environment values and no broad `.env` file is mounted.

Before startup, provide `KB_READ_KEYS` and `KB_ADMIN_KEYS`. Build and run the API with `docker compose -f deploy/docker-compose.yml up --build kb-api`. The healthcheck uses Python from the guaranteed runtime and calls readiness. Verify `/live`, `/ready`, denied fake-key access, allowed test-key access, degraded readiness with an unavailable index, and SIGTERM completion within the 30-second graceful timeout.

The default Gunicorn budget is two workers × four threads, a 60-second hard timeout, and 30-second graceful timeout. It is intentionally conservative for a 2 GiB container. Change it only after measuring resident memory, concurrent latency, and downstream limits.

The optional Nginx profile binds `127.0.0.1:8080` by default, overwrites untrusted forwarded-IP headers, and bounds body size, rates, and timeouts. It is plain HTTP. A public bind without a separately validated TLS terminator is unsupported; absent TLS configuration therefore fails closed by remaining loopback-only.

Upgrade procedure:

1. Back up named volumes and record their immutable snapshot IDs.
2. Dry-run artifact/index migrations against new targets and preserve reports.
3. Build a new immutable image tag and SBOM; never reuse the previous tag.
4. Start it against temporary copies, verify health/auth/degraded/shutdown behavior, then validate artifacts and index.
5. Stop the old container gracefully and switch traffic/index pointers atomically.
6. Retain the old image and volume snapshots until the rollback window closes.

Rollback reverses traffic and the active index pointer to the prior validated image/index, restores volume snapshots only if a write migration occurred, verifies readiness and a fake-key smoke query, and quarantines the failed target. Never delete the only validated index or source corpus. `scripts/exercise_release_rollback.py` rehearses pointer upgrade/rollback and byte-identical artifact preservation exclusively in a temporary directory.

With Docker available, run `uv run python scripts/exercise_container_release.py --project sekbexercise-local`. The script builds uniquely tagged old/new images, starts both against isolated named volumes, verifies non-root/read-only execution and health/auth, copies the temporary index during upgrade, rolls back to the old tag and pointer, compares SHA-256 digests, then removes only the validated `sekbexercise-*` project volumes and image tags. CI runs the same cross-platform command for the explicitly selected `container` external suite and uploads the JSON evidence for 14 days.
