# Service boundary security

## Authentication

Set comma-separated `KB_READ_KEYS` and `KB_ADMIN_KEYS`. Protected endpoints accept exactly one
`Authorization: Bearer <token>` header. Raw keys, malformed schemes, duplicate values, and an empty
key configuration are denied. Administrative MCP tools expose `authorization` and optional
`correlation_id` arguments and require an admin key.

The Web console stores its entered key only in browser `sessionStorage`. State-changing requests
also require the same-origin `Origin` plus the double-submit `kb_csrf` cookie/header. Configure exact
browser origins with `CORS_ORIGINS`; wildcards are intentionally unsupported.

## Public errors and audit events

REST/Web errors use an `error` object containing stable `code`, safe `message`, and
`correlation_id`, with an optional `field`. The same correlation ID is returned in the
`X-Correlation-ID` response header. Server diagnostics record exception classes and redacted audit
context, not client exception text, request credentials, or key prefixes.

Authentication and administrative outcomes are written to the `se-kb.audit` logger. Deployments
should route this logger to append-only operator storage with normal retention controls.

## Request and fetch limits

Defaults can be tightened with:

- `MAX_REQUEST_BYTES`, `MAX_QUERY_CHARS`, `MAX_CONTENT_CHARS`, `MAX_URL_CHARS`, `MAX_TOP_K`,
  `MAX_TASK_LIMIT`, `MAX_LIST_ITEMS`;
- `REQUESTS_PER_MINUTE`, `MAX_REQUEST_CONCURRENCY`;
- `FETCH_MAX_REDIRECTS`, `FETCH_MAX_COMPRESSED_BYTES`, `FETCH_MAX_DECOMPRESSED_BYTES`,
  `FETCH_MAX_IMAGE_PIXELS`, `FETCH_TOTAL_SECONDS`, and the connect/read/write/pool timeout variables.

User-controlled URLs allow only HTTP(S), reject credentials and malformed ports, resolve IDNs, and
reject any DNS answer that is loopback, private, link-local, reserved, multicast, unspecified, or a
configured metadata address. Redirects and Playwright subrequests are revalidated. A rejected or
oversized stream is closed and is not passed to artifact writing.

## Trusted private-network mode and residual risk

`ALLOW_PRIVATE_NETWORK_FETCH=true` is an explicit trusted-deployment escape hatch for intranet
crawling. It still blocks metadata ranges, multicast, unspecified, loopback, link-local, and reserved
addresses. Enabling it materially expands SSRF reach and should be combined with egress firewall
rules and a dedicated low-privilege network identity.

The HTTP libraries may resolve a hostname again after policy resolution, leaving a DNS rebinding
time-of-check/time-of-use window where address pinning is unavailable. Redirects are still checked,
but production deployments must treat network-layer egress controls as the final boundary. Model,
search-provider, Tor, and proxy endpoints are administrator configuration trust boundaries rather
than user URL inputs.

## Offline verification

Run `scripts/quality.ps1`. The gate blocks outbound network during pytest and includes the encoding,
dependency-drift, secret/static boundary, Ruff, mypy, and contract/security test suites. Live browser,
Tor, model, and penetration tests remain opt-in and must target systems you are authorized to test.
