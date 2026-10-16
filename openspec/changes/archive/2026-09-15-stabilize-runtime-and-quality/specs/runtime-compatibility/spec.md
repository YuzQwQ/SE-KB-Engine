## ADDED Requirements

### Requirement: Explicit supported runtime
The project SHALL declare one Python support range consistently across package metadata, tooling, local setup, CI, and containers.

#### Scenario: Runtime declarations agree
- **WHEN** an operator compares the supported-version declarations
- **THEN** the package, type checker, linter, version file, CI, and container describe compatible Python versions

### Requirement: Reproducible dependency installation
The project SHALL maintain one authoritative dependency model with explicit optional groups and a reproducible lock or generated production export.

#### Scenario: Clean core installation
- **WHEN** a contributor installs the locked core environment on a supported Python version
- **THEN** installation completes without implicitly installing browser, Tor, or unrelated production-only tools

#### Scenario: Declaration drift
- **WHEN** generated dependency artifacts no longer match the authoritative declaration
- **THEN** an offline quality check fails with the files and regeneration command

### Requirement: UTF-8 formal sources
All formal source, configuration, specification, and documentation files SHALL be valid UTF-8 and all formal Python sources SHALL compile.

#### Scenario: Invalid source encoding
- **WHEN** a checked text file contains UTF-16 or invalid UTF-8 bytes
- **THEN** the encoding check fails and identifies the file without modifying it

### Requirement: Side-effect-free import baseline
Importing a formal module for validation SHALL NOT require secrets, access the public network, invoke a paid model, or write user data.

#### Scenario: Empty environment import
- **WHEN** smoke imports run with secrets removed and data roots redirected to a temporary directory
- **THEN** supported modules import or report an explicitly optional missing capability without external side effects
