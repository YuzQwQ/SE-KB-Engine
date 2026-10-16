# Release readiness report

Status: **engineering gates implemented; public release not authorized**.

| Evidence | Current artifact | Status |
|---|---|---|
| Required CI | `.github/workflows/ci.yml` | Windows/Linux, Python 3.11–3.13 defined |
| Offline quality | `scripts/quality.py` | local full gate required |
| Coverage | `docs/baseline/coverage-2026-09-15.json` | 87.2% over application/boundary packages |
| Retrieval performance | `docs/baseline/retrieval-comparison-hybrid-*.json` | promoted candidate passes dev/holdout |
| Telemetry overhead | `docs/baseline/telemetry-overhead-2026-09-15.json` | bounded payload/latency/memory pass |
| Security | `scripts/check_security.py` | offline rules pass; scheduled audit still required per release |
| SBOM | `docs/baseline/sbom-2026-09-15.cdx.json` | offline lock-derived inventory; CI audit artifact required |
| Migration | artifact and retrieval dry-run reports | no real corpus/index migration authorized |
| Data rollback exercise | `docs/baseline/release-rollback-exercise-2026-09-16.json` | isolated temporary-copy exercise passes with byte-identical source |
| Container rollback exercise | `docs/baseline/container-release-exercise-2026-09-16.json` | Docker Desktop old/new/old exercise passes; non-root, read-only root, health/auth, digest, and cleanup verified |
| Documentation | `scripts/check_docs.py --execute-smoke` | links and offline commands required to pass |
| Delivery configuration | `scripts/check_delivery.py` | static hardening checks required to pass |

Remaining deployment risks: no hosted telemetry backend selected; no public TLS endpoint configured; real provider/network/Tor/browser suites require explicit credentials and cost approval; this environment has not published an image; production volume backup/restore must be demonstrated by the operator. These are deliberate external/manual gates and do not authorize deployment.
