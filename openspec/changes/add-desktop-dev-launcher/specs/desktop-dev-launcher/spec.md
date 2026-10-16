## ADDED Requirements

### Requirement: Unified development window
The launcher SHALL expose start, stop, restart, status, logs and browser shortcuts for Web and REST independently and together, using default loopback ports 8000 and 8001.

#### Scenario: Start both services
- **WHEN** both configured ports are available and the user starts all services
- **THEN** each service starts once with its own status and tagged log output

### Requirement: Safe process ownership
The launcher SHALL validate ports, reject duplicate or occupied ports, prevent duplicate starts and stop only processes it owns.

#### Scenario: External listener
- **WHEN** a configured port is occupied by another process
- **THEN** startup reports a conflict without terminating that process

#### Scenario: Close cancellation
- **WHEN** the user cancels closing a window with active services
- **THEN** the window and services remain running

### Requirement: Diagnostics and debug mode
The launcher SHALL show startup errors, HTTP liveness, unexpected exits and bounded redacted logs without blocking its UI. Debug mode SHALL bind loopback, disable the interactive debugger and use explicit restart to reload code.

#### Scenario: Failed startup
- **WHEN** a process exits before its HTTP liveness check passes
- **THEN** the window reports failure and retains its redacted output

#### Scenario: Debug restart
- **WHEN** the user enables debug mode and restarts a service
- **THEN** it restarts in debug mode on the configured port without an automatic reloader child

### Requirement: Offline launch workflow
The launcher SHALL use the installed project environment and provide a double-click Windows entry point without installing packages or invoking models.

#### Scenario: Missing environment
- **WHEN** the Windows entry point cannot find the project interpreter
- **THEN** it explains how to prepare the environment and exits without downloading dependencies
