## Why

The functional Tk launcher needs a refined interface matching the knowledge workspace. HTML/CSS inside a native pywebview window supports consistent typography, responsive cards and readable logs while retaining process supervision.

## What Changes

- Make a bundled, offline HTML/CSS/JavaScript console the default desktop interface.
- Connect validated service actions and bounded log polling through a narrow Python bridge.
- Add a desktop dependency extra and keep explicit Tk fallback.
- Preserve the VBS double-click entry and existing process behavior.

## Capabilities

### New Capabilities
- `web-desktop-launcher`: Styled desktop shell, restricted bridge and lifecycle cleanup.

### Modified Capabilities
None. Builds on the unarchived add-desktop-dev-launcher change.

## Impact

Prerequisite: existing launcher supervisor. Adds optional pywebview dependencies, static assets, bridge tests, docs and desktop smoke verification. No data migration, paid API calls or model calls. Installing the dependency extra needs package network access. Non-goals: production serving, remote content in the privileged window, automatic updates or IDE breakpoint attachment. Rollback uses `--tk`.
