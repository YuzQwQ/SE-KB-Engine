## Why

Developers currently start the Web console and REST API in separate terminals, and both entry points default to port 8000. A desktop launcher should make local startup, shutdown and diagnosis accessible in one window.

## What Changes

- Add a Tkinter window with start/stop/restart controls, per-service status, live logs and browser shortcuts.
- Run Web on loopback port 8000 and REST on 8001 by default, with editable ports, optional Flask debug mode and explicit restart to reload code.
- Add a double-click Windows entry point using the existing project environment.
- Preserve existing standalone entry points.

## Capabilities

### New Capabilities
- `desktop-dev-launcher`: Window-based local development process management and diagnostics.

### Modified Capabilities
None.

## Impact

New launcher modules, Windows entry point, offline tests and developer documentation. Requires the existing Python environment with the API extra and Tkinter; no new package dependency. Non-goals: production deployment, Docker management, IDE breakpoint integration, data migration or dependency installation. Starting local services does not itself trigger paid model calls or remote crawling. Shutdown targets only launcher-owned process trees.
