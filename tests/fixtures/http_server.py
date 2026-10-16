from __future__ import annotations

import gzip
import socket
import time
from collections import Counter
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Iterator
from urllib.parse import parse_qs, urlsplit


class FixtureHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    counts: Counter[str] = Counter()

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        path = parsed.path
        type(self).counts[path] += 1
        if path in {"/ok", "/article"}:
            body = b"reliable content" if path == "/ok" else b"reliable content for offline acquisition"
            self._send(200, b"<html><title>Fixture</title><article>" + body + b"</article></html>")
        elif path == "/article-redirect":
            self.send_response(302)
            self.send_header("Location", "/article")
            self.send_header("Content-Length", "0")
            self.end_headers()
        elif path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/ok")
            self.send_header("Content-Length", "0")
            self.end_headers()
        elif path == "/retry":
            if type(self).counts[path] == 1:
                self._send(503, b"retry", {"Retry-After": "0"})
            else:
                self._send(200, b"recovered")
        elif path == "/etag":
            if self.headers.get("If-None-Match") == '"fixture-v1"':
                self._send(304, b"", {"ETag": '"fixture-v1"'})
            else:
                self._send(200, b"conditional content", {"ETag": '"fixture-v1"'})
        elif path in {"/delay", "/article-delay"}:
            delay = min(float(parse_qs(parsed.query).get("seconds", ["0.05"])[0]), 0.2)
            time.sleep(delay)
            self._send(200, b"delayed" if path == "/delay" else b"<article>delayed useful content for offline acquisition</article>")
        elif path in {"/gzip", "/article-gzip"}:
            body = b"compressed content" if path == "/gzip" else b"<article>compressed useful content for offline acquisition</article>"
            self._send(200, gzip.compress(body), {"Content-Encoding": "gzip"})
        elif path == "/malformed-encoding":
            self._send(200, b"valid-prefix-\xff-invalid", {"Content-Type": "text/plain; charset=ascii"})
        elif path == "/large":
            self._send(200, b"x" * (2 * 1024 * 1024))
        elif path == "/challenge":
            self._send(403, b"<html><title>Just a moment...</title>captcha challenge</html>")
        elif path == "/disconnect":
            self.send_response(200)
            self.send_header("Content-Length", "100")
            self.end_headers()
            self.wfile.write(b"short")
            self.wfile.flush()
            self.close_connection = True
            self.connection.shutdown(socket.SHUT_RDWR)
        else:
            self._send(404, b"missing")

    def _send(self, status: int, body: bytes, headers: dict[str, str] | None = None) -> None:
        self.send_response(status)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *_args: object) -> None:
        return None

    def handle_one_request(self) -> None:
        try:
            super().handle_one_request()
        except (BrokenPipeError, ConnectionResetError, OSError):
            self.close_connection = True


@contextmanager
def local_http_fixture() -> Iterator[tuple[str, Counter[str]]]:
    FixtureHandler.counts = Counter()
    server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
    thread = Thread(target=server.serve_forever, name="http-fixture", daemon=True)
    thread.start()
    try:
        raw_host, raw_port = server.server_address[:2]
        host = raw_host.decode() if isinstance(raw_host, bytes) else str(raw_host)
        port = int(raw_port)
        yield f"http://{host}:{port}", FixtureHandler.counts
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
