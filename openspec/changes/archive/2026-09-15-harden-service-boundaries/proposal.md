## Why

The REST, Web, MCP, and arbitrary-URL fetch surfaces currently have inconsistent validation and error behavior, while debug mode, broad CORS, administrative mutations, and URL fetching create avoidable exposure. These boundaries must be secured before broader refactoring or production deployment.

## What Changes

- Define a consistent API error envelope, parameter limits, status semantics, and degraded behavior.
- Harden bearer-token handling, role checks, secret redaction, administrative authorization, CSRF/CORS policy, and audit events.
- Add SSRF-resistant URL validation before every request and after redirects, plus response/time/redirect limits.
- Prevent internal exceptions, file paths, credentials, upstream bodies, and unsafe HTML from leaking to clients or logs.
- Add offline boundary and contract tests for REST, Web, MCP, and fetch behavior.

Non-goals: introducing end-user accounts, OAuth, a public multi-tenant service, changing the knowledge schema, or performing live penetration tests against third-party sites.

Prerequisites: `stabilize-runtime-and-quality` must provide the deterministic test and configuration baseline.

## Capabilities

### New Capabilities
- `service-auth`: Service and administrative operations enforce a documented role and secret-handling policy.
- `safe-url-fetching`: All user-controlled URL fetching is constrained against SSRF, redirect bypasses, unbounded responses, and unsupported schemes.
- `api-contracts`: REST, Web, and MCP boundaries expose validated inputs and stable success, failure, and degraded-mode contracts.

### Modified Capabilities

None.

## Impact

Affects `api/`, `web/`, MCP tool adapters in `server.py`, crawler URL handling, logging filters, configuration, and their tests. Some previously accepted unsafe inputs will receive 4xx responses. No user data migration or external security scanning is performed by default.
