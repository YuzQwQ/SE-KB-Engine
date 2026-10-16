## Context

The frontend is server-rendered Flask, with no separate Node build. The REST application is another Flask process. Both standalone scripts use port 8000. Tkinter is available in the current Python installation.

## Goals / Non-Goals

Goals: one window, independent process lifecycle, configurable loopback ports, bounded logs, HTTP startup checks and useful failures. Non-goals: production serving, arbitrary shell commands, package installation and IDE debugger attachment.

## Decisions

- Use standard-library Tkinter/ttk rather than introduce Qt or Electron. Keep supervision independent of Tk for offline testing.
- Spawn an explicit Python module with the project interpreter, unbuffered UTF-8 output and no shell. A small worker imports the appropriate Flask application and binds only 127.0.0.1. Existing scripts retain their defaults.
- Debug mode enables Flask debug behavior and detailed logs with the interactive debugger and automatic reloader disabled. The restart action reloads code explicitly and keeps ownership of one process per service.
- Validate ports before starting; never terminate an external listener. Track only owned children and stop their trees on close. Run blocking IO in workers and marshal updates through a bounded queue to the Tk thread.
- HTTP liveness indicates startup; REST retrieval readiness is a separate capability and may remain degraded when model/index configuration is absent.
- Redact known environment secrets and bearer values from captured output. Logs are memory-only and bounded.

## Risks / Trade-offs

- Windows process termination may interrupt in-flight work → show this on close, allow cancellation of close, and document stopping only after jobs finish.
- Missing Tk or API extras → report prerequisite commands without automatic downloads.
- Port preflight can race another application → surface actual child exit and startup timeout as failures.

## Migration Plan

Additive launcher and Windows entry point; rollback is to use the existing standalone commands. Verify supervisor failures and lifecycle with fake processes and a real local fixture, and exercise window creation with Tk. No data migration is required.
