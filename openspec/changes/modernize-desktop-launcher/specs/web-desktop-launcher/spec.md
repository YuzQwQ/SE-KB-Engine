## ADDED Requirements

### Requirement: Bundled styled desktop console
The launcher SHALL render a responsive dark HTML console in a native desktop window with service cards, editable ports, debug controls and readable filtered logs, without relying on running Web/API services or external UI assets.

#### Scenario: Offline startup
- **WHEN** the desktop extra and renderer are installed and both services are stopped
- **THEN** the launcher displays its complete UI with enabled startup controls

### Requirement: Restricted bridge
The bridge SHALL allow only known services, actions, validated ports, boolean debug flags and fixed loopback browser destinations. Logs SHALL be bounded, redacted and rendered as text.

#### Scenario: Invalid command
- **WHEN** a caller supplies an unknown service, duplicate ports or invalid types
- **THEN** the bridge rejects the request without spawning or stopping processes

#### Scenario: Untrusted log content
- **WHEN** output contains HTML-like text or a known secret
- **THEN** the interface displays literal text and redacts the secret

### Requirement: Retained ownership and close behavior
The desktop window SHALL retain independent and combined service operations and SHALL confirm close when services are active, preserve cancellation and keep the UI alive if cleanup fails.

#### Scenario: Cancel exit
- **WHEN** the user cancels the styled exit confirmation
- **THEN** the window and owned processes continue running

#### Scenario: Stop failure
- **WHEN** an owned process cannot be stopped during exit
- **THEN** the window stays open and reports the error

### Requirement: Recoverable desktop setup
The launcher SHALL provide installation guidance when desktop dependencies are unavailable and SHALL retain an explicit Tk fallback.

#### Scenario: Tk fallback
- **WHEN** the user runs start_launcher.py with --tk
- **THEN** the previous Tk launcher runs without importing pywebview
