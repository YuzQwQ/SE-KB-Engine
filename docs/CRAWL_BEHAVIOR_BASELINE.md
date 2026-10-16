# Crawl behavior baseline

The local fixture server in `tests/fixtures/http_server.py` characterizes success, redirect,
Retry-After, delay, compression, malformed declared encoding, oversized body, challenge/login, and
disconnect behavior without external network access.

## Legacy decision inventory

| Situation | Existing path | Reliability decision retained by the state machine |
| --- | --- | --- |
| acceptable static HTML | HTTP/WebpageCrawler returns parsed content | finish immediately; no retry or browser |
| transient HTTP/transport error | nested HTTP retries | retry only a typed retryable error within the attempt budget |
| static response has too little content | Playwright helper may run | allow one rendered fallback when policy enables it |
| policy-blocked or unsupported URL/media | URL policy rejects | terminal failure; never try proxy, Tor, direct, or browser alternatives |
| challenge or login wall | legacy path could treat HTML as content | classify and report challenge; do not publish as an article |
| proxy/Tor selected | environment and availability decide transport | select transport before execution; do not switch paths after permanent failure |
| direct fallback after proxy error | legacy code sometimes retries without proxy | only an explicit policy transition may permit it; default is disabled |

This baseline intentionally does not attempt CAPTCHA or access-control bypass. Live validation stays
opt-in; the default characterization suite uses loopback only.
