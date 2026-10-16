## Context

The system accepts tokens, queries, administrative commands, and arbitrary URLs through multiple adapters. Security policy is duplicated or absent, and error strings can cross trust boundaries. A shared policy layer must precede handler-level cleanup.

## Goals / Non-Goals

**Goals:** central validation and error mapping; constant-time secret comparison and role policy; protected mutations; SSRF-safe redirects and bounded bodies; safe logging/output; contract tests.

**Non-Goals:** identity management, OAuth, multi-tenancy, public deployment, or attacking third-party systems.

## Decisions

1. Validate external inputs into typed request objects before application services. Keep Flask/MCP adapters thin.
2. Centralize authentication policy while preserving bearer-token compatibility. Use constant-time comparison and separate read/admin key sets.
3. Resolve and validate every URL hop. Permit only HTTP(S); reject non-public resolved addresses, credentials in URLs, excessive redirects, and DNS rebinding between validation and connect where the client permits pinning.
4. Return stable public error codes and correlation IDs; retain sanitized diagnostic cause server-side.
5. Make CORS origins explicit and protect browser mutations with same-origin/CSRF controls. Do not rely on CORS as authentication.

## Risks / Trade-offs

- [Legitimate private-site crawling stops] → make private-network access a separate explicit trusted deployment mode, disabled by default.
- [DNS changes after validation] → validate each redirect and connection target; document residual rebinding limits.
- [Contract hardening breaks callers] → preserve success shapes where possible and document rejected unsafe inputs.

## Migration Plan

Add tests around existing boundaries; introduce shared validators/errors; apply to API then Web then MCP/fetchers; enable restrictive defaults with documented local overrides. Roll back per adapter while retaining tests.

## Open Questions

- Is private intranet crawling a required trusted-mode capability?
- Which browser origins are needed in deployed environments?
