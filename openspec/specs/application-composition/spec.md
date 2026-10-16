# Application composition

## Purpose

Define explicit dependency assembly, managed resource lifecycles, thin runtime adapters, and compatibility during incremental modularization.

## Requirements

### Requirement: Explicit dependency assembly
Each runtime surface SHALL obtain settings, clients, stores, application services, clock, and logger from an explicit composition root rather than creating hidden global dependencies.

#### Scenario: Offline test composition
- **WHEN** a test constructs an application with fake clients and temporary stores
- **THEN** handlers execute without importing or contacting real external services

### Requirement: Managed lifecycle
Resources with startup or shutdown behavior SHALL be initialized lazily or during explicit startup and closed during explicit shutdown.

#### Scenario: Failed partial startup
- **WHEN** one dependency fails during startup
- **THEN** already-created resources are closed and the affected capability is reported unavailable

### Requirement: Thin runtime adapters
MCP, REST, Web, and CLI adapters SHALL be limited to transport parsing, authorization, application-service invocation, and response mapping.

#### Scenario: Shared operation
- **WHEN** equivalent operations are invoked through two adapters
- **THEN** both call the same application service and differ only in transport representation

### Requirement: Incremental compatibility
Existing public MCP tool names and supported response contracts SHALL remain available while implementation moves behind application services.

#### Scenario: Extracted MCP tool
- **WHEN** a previously supported tool is invoked after extraction
- **THEN** its characterization contract still passes through the compatibility adapter
