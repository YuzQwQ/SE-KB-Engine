## Context

Process supervision is already separate from Tk. pywebview provides a native WebView2 window on Windows with a Python bridge. The desktop UI must work without the project Web/API processes running.

## Goals / Non-Goals

Goals: refined dark interface, readable bounded color-coded logs, accessible controls and retained lifecycle behavior. Non-goals: remote UI content, an additional HTTP control server or arbitrary command execution.

## Decisions

- Bundle plain HTML, CSS and JavaScript and embed them as a single document via `html=`. No CDN, remote fonts, build tool or listening launcher port. CSP denies network, frames, forms and external navigation.
- Expose only state polling, validated service actions, log clearing and fixed local browser shortcuts. Reuse ServiceProcess; guard all mutations with one operation lock and preserve failures.
- Poll snapshots and log cursors with non-overlapping asynchronous calls. Keep a bounded Python ring and DOM buffer. Insert log data as text. Provide source/severity/search filters, pause/follow and an empty state.
- Intercept native close. If services are active, cancel native close and display a styled confirmation; stop owned services in the bridge before destroying the window. Failure keeps the window alive. The native close guard also handles operations in progress.
- Install pywebview behind the desktop extra. Retain `--tk`; missing renderer/dependency errors show actionable instructions. Standard window chrome retains native resizing and accessibility.

## Risks / Trade-offs

- WebView2 runtime availability → report the desktop prerequisite and allow explicit Tk fallback.
- Privileged bridge → no remote navigation, narrow fixed service/action allowlists, strict types and offline assets.
- Windows termination can interrupt jobs → retain close confirmation and failed-stop reporting.

## Migration Plan

Switch start_launcher.py default to webview; VBS stays unchanged. Regenerate the dependency lock and exported requirements. Verify bridge failure/concurrency tests, browser rendering and real native WebView2 interaction. Roll back with `--tk`.
