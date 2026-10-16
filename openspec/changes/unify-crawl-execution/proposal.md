## Why

Production crawl entrypoints do not share the tested fetch policies, cancellation or content contracts. The approved crawl review reproduced credential forwarding, policy fallthrough, lost code/tables, overwritten snapshots and cross-job output.

## What Changes

- Unify Web, MCP and CLI acquisition behind a bounded, cancellable crawl service and preserve adapter contracts.
- Close redirect, transport, DNS, browser subrequest, body-size and deadline boundaries. Disable implicit third-party forwarding.
- Preserve ordered technical content and publish unique atomic snapshots; use conservative URL identity.
- Bound job/cache histories and add site policies, real production-cleaner quality measurements and offline regressions.

## Capabilities

### New Capabilities
- `unified-crawl-execution`: Safe shared acquisition, scoped jobs, faithful content and measurable offline acceptance.

### Modified Capabilities
None. Existing public tool names and Web response bodies remain compatible.

## Impact

Prerequisites are the existing domain, boundary, crawl and job modules. Changes affect their production wiring plus legacy facades, cleaner, extraction preparation and developer docs. No data migration or deletion, new framework, external queue, automatic indexing or paid/live calls. Browser and live validation remain explicit opt-ins. Candidate parser replacement is conditional on measurements, not part of the default rollout. Rollback is per adapter while retaining corrected security boundaries and original user data.
