## ADDED Requirements

### Requirement: Public HTTP URL policy
User-controlled fetch targets SHALL use HTTP or HTTPS and SHALL resolve only to allowed public addresses unless trusted private-network mode is explicitly enabled.

#### Scenario: Cloud metadata target
- **WHEN** a target resolves to loopback, private, link-local, reserved, multicast, or cloud metadata space
- **THEN** the fetch is rejected before content is requested

### Requirement: Redirect revalidation
Every redirect target SHALL be re-parsed and revalidated under the same URL and address policy with a bounded redirect count.

#### Scenario: Public-to-private redirect
- **WHEN** an allowed public URL redirects to a prohibited address
- **THEN** the fetch stops and returns a safe policy error

### Requirement: Bounded remote content
Fetchers SHALL enforce connect/read/write/pool timeouts and configured limits for redirects, compressed bytes, decompressed bytes, media type, image dimensions, and total processing time.

#### Scenario: Oversized response
- **WHEN** a response exceeds its configured limit
- **THEN** reading stops, resources close, and no partial artifact is published as successful
