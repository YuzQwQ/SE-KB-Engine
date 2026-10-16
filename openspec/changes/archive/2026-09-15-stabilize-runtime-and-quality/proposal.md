## Why

The project cannot yet prove that it installs, imports, compiles, and runs consistently across its declared environments. Encoding drift, conflicting Python/dependency declarations, import-time side effects, and a minimal test suite make every later optimization risky, so a reproducible baseline and offline safety net must come first.

## What Changes

- Standardize supported Python versions, UTF-8 source encoding, dependency groups, and lock-file usage.
- Make formal modules compile and import without network access, paid API calls, or data writes.
- Establish deterministic offline unit, contract, smoke, lint, type, and encoding checks behind one developer command.
- Inventory repository artifacts and prevent runtime data, caches, secrets, and platform binaries from entering normal source workflows accidentally.
- Preserve and verify the quality work already present in the working tree before extending it.

Non-goals: redesigning crawler behavior, changing public API contracts, splitting the MCP monolith, migrating user data, or deleting tracked/untracked artifacts.

Prerequisites: none. This change is the prerequisite for all other optimization changes.

## Capabilities

### New Capabilities
- `runtime-compatibility`: The project has an explicit, reproducible Python and dependency contract across Windows development and Linux containers.
- `offline-quality-gates`: Contributors and automation can validate source encoding, imports, behavior, typing, and tests without network or paid services.

### Modified Capabilities

None.

## Impact

Primarily affects `pyproject.toml`, dependency/lock files, text encoding, test configuration, quality scripts, `.gitignore`, `.gitattributes`, `.editorconfig`, entry-point initialization, and developer documentation. No external network or paid model execution is required. Existing user data and generated materials remain untouched.
