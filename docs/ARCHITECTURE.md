# Application architecture

## Dependency direction

```text
adapters (server.py, api/, web/, scripts/)
    -> application (se_kb_app/services, composition)
        -> domain (se_kb_app/domain, errors, settings values)
            <- infrastructure implementations (existing utils/, vectorizer/, model/Tor factories)
```

Adapters may import application/domain and boundary policy. Application services may import domain
protocols and DTOs but not Flask, MCP, CLI parsing, or concrete browser transports. Domain modules
must not import `flask`, `mcp`, `httpx`, `requests`, `playwright`, `openai`, `chromadb`, or Tor/process
implementations. Infrastructure implements domain protocols and is constructed only by the
composition root.

## Current import/dependency map

| Layer | Modules | Allowed outward dependencies |
| --- | --- | --- |
| adapters | `server.py`, `api/`, `web/app.py`, CLI scripts | `se_kb_app`, `service_boundary`, transport framework |
| application | `se_kb_app/composition.py`, `se_kb_app/services/` | domain contracts, settings, injected collaborators |
| domain | `se_kb_app/domain.py`, `se_kb_app/errors.py` | Python standard library only |
| infrastructure | `se_kb_app/factories.py`, `utils/`, `vectorizer/`, existing extractors/writers | external SDKs plus domain protocols |

`tests/test_architecture_boundaries.py` enforces the domain import ban and prevents application services from
importing Flask or MCP. Existing legacy modules are migration sources and are not falsely labeled as
domain.

## Composition and lifecycle

`AppSettings.from_sources()` resolves immutable configuration in this order: defaults, TOML/JSON
configuration, environment, then explicit overrides. `ApplicationBuilder` accepts fake or real
factories, stores, services, a clock, and a logger. Resources are lazy unless `Application.start()`
is called. A failed startup transaction closes resources created by that transaction in reverse
order and records safe capability readiness codes. `Application.close()` owns normal shutdown.

The default OpenAI, HTTP, vector, browser, and Tor constructors live in `se_kb_app/factories.py`.
They import optional SDKs only inside the factory call. The Tor controller does not inspect ports or
launch a process during import or construction.

## Compatibility shims and removal criteria

| Shim | Owner | Remove when |
| --- | --- | --- |
| `server.configure_application()` and lazy processor caches | MCP adapter | all MCP tools resolve collaborators through `Application` and golden tool contracts pass |
| `api.app.create_app(initialize_services=...)` | REST adapter | deployments always pass an application and REST contract tests pass |
| `web.app.bind_application()` | Web adapter | the Web package exposes only an application-based factory and Web contract tests pass |
| `start_web.main(application=None)` subprocess path | CLI adapter | launch scripts construct and close one application explicitly |

Retrieval is the first shared vertical slice: MCP and REST use the same injected
`RetrievalService`, and Web uses it when bound. Legacy vector calls remain as a fallback until every
deployment supplies the composition root.

## Migration rule

Extract one vertical service, retain a compatibility facade, run characterization/boundary/import
tests, then point another adapter at the same service. Deletion is allowed only after all listed
callers migrate and their golden contracts pass. A `src/` package relocation is deferred until these
imports are stable; moving files now would combine structural churn with behavioral extraction.
