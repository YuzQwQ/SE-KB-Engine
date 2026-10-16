## 1. Characterize public boundaries

- [x] 1.1 Inventory every REST route, Web mutation, MCP tool, URL-taking parameter, auth rule, response shape, and current failure/degraded behavior.
- [x] 1.2 Add Flask and MCP contract fixtures plus tests for current success shapes before intentional hardening changes.
- [x] 1.3 Define shared input limits and a public error catalog with stable code, safe message, correlation ID, and transport mapping.

## 2. Authentication and browser mutation policy

- [x] 2.1 Refactor bearer parsing into one tested component covering missing, malformed, read, admin, duplicate, and invalid credentials.
- [x] 2.2 Use constant-time candidate comparison and add tests proving credentials and prefixes never enter responses or captured logs.
- [x] 2.3 Apply read/admin authorization consistently to API, Web, and MCP administrative operations.
- [x] 2.4 Disable debug mode by default and replace open CORS with configured exact origins, methods, and headers.
- [x] 2.5 Add same-origin/CSRF protection for browser mutations and tests that rejected requests do not change state.
- [x] 2.6 Emit redacted audit events for authentication and administrative success/failure.

## 3. Safe URL fetching

- [x] 3.1 Implement a shared URL parser/policy for HTTP(S), credentials, host syntax, ports, IDNs, and prohibited schemes with table-driven tests.
- [x] 3.2 Resolve target hosts and reject loopback, private, link-local, reserved, multicast, unspecified, and configured metadata ranges for IPv4/IPv6.
- [x] 3.3 Revalidate DNS/address policy on every redirect and add local fake-resolver tests for public-to-private and mixed-address cases.
- [x] 3.4 Apply the policy to manual crawl, search results, images, Playwright navigation, MCP fetch tools, and every secondary resource path.
- [x] 3.5 Add redirect, connect/read/write/pool, compressed/decompressed body, media type, image dimension, and total-operation limits.
- [x] 3.6 Ensure limit/policy failure closes resources and cannot publish a successful partial artifact.

## 4. Contract and output hardening

- [x] 4.1 Add typed validation for queries, URLs, enums, booleans, dates, path components, request bodies, `top_k`, and task limits.
- [x] 4.2 Replace client-visible `str(e)` and stack/path leakage with public error mapping while retaining correlated sanitized diagnostics.
- [x] 4.3 Separate liveness and readiness behavior for missing retriever/model/browser/Tor capabilities.
- [x] 4.4 Sanitize any server content inserted into the Web DOM and add regression tests for HTML/script payloads.
- [x] 4.5 Add request-body and rate/concurrency limits to exposed endpoints with deterministic local tests.
- [x] 4.6 Run boundary tests with outbound networking blocked, run secret/static/dependency scans, and document residual trusted-private-network risk.
