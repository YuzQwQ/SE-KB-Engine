# Supply-chain and static-security triage

Required offline CI checks dependency-lock drift and the repository's static security rules. The scheduled/manual supply-chain workflow generates a CycloneDX SBOM, audits locked production dependencies, inventories licenses, and retains evidence for 30 days.

Triage findings by exploitability, reachability, data sensitivity, and availability of a fixed compatible version:

- Critical/high with a reachable runtime path: block release, rotate affected secrets if relevant, upgrade the lock, and rerun all gates.
- Critical/high not reachable: document the evidence and compensating control with an owner and expiry; do not silently ignore it.
- Medium/low: create a dated remediation item and reassess at every lock update.
- License uncertainty: block redistribution until ownership and compatibility are resolved.
- Secret finding: remove it from current files and history as appropriate, rotate immediately, and treat logs/artifacts as exposed.

False positives require a narrow, reviewed suppression containing tool/rule, exact package/path, rationale, reviewer, and expiration. Broad directory exclusions are prohibited. Ruff/mypy exclusions are categorized in `pyproject.toml`; new exclusions require a smaller scope than the code they cover and a ratchet/removal task.
