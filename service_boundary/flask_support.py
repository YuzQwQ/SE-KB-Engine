from __future__ import annotations

import logging
import os
import secrets
import threading
import time
from collections import defaultdict, deque
from functools import wraps
from typing import Callable, ParamSpec, TypeVar

from flask import Flask, Response, g, jsonify, request
from flask_cors import CORS

from service_boundary.audit import audit_event, redact
from service_boundary.auth import Role, authenticate
from service_boundary.errors import PublicError, correlation_id, public_error, public_error_payload
from service_boundary.inputs import InputLimits
from se_kb_app.observability import METRICS, push_event_context, reset_event_context

P = ParamSpec("P")
R = TypeVar("R")
LOGGER = logging.getLogger("se-kb.boundary")
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


class RequestLimiter:
    def __init__(self, limit: int, window_seconds: float, *, clock: Callable[[], float] = time.monotonic):
        self.limit = limit
        self.window_seconds = window_seconds
        self.clock = clock
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = self.clock()
        with self._lock:
            history = self._requests[key]
            while history and history[0] <= now - self.window_seconds:
                history.popleft()
            if len(history) >= self.limit:
                return False
            history.append(now)
            return True


class ConcurrencyLimiter:
    def __init__(self, maximum: int):
        self._semaphore = threading.BoundedSemaphore(maximum)

    def acquire(self) -> bool:
        return self._semaphore.acquire(blocking=False)

    def release(self) -> None:
        self._semaphore.release()


def configured_origins() -> tuple[str, ...]:
    defaults = "http://127.0.0.1:8000,http://localhost:8000,http://127.0.0.1:8001,http://localhost:8001"
    return tuple(
        origin.rstrip("/")
        for origin in os.getenv("CORS_ORIGINS", defaults).split(",")
        if origin.strip()
    )


def install_flask_boundary(app: Flask, *, cors: bool = True) -> None:
    limits = InputLimits.from_environment()
    app.config.setdefault("MAX_CONTENT_LENGTH", limits.request_bytes)
    app.config.setdefault("BOUNDARY_RATE_LIMIT", int(os.getenv("REQUESTS_PER_MINUTE", "120")))
    app.config.setdefault("BOUNDARY_MAX_CONCURRENCY", int(os.getenv("MAX_REQUEST_CONCURRENCY", "16")))
    limiter = RequestLimiter(app.config["BOUNDARY_RATE_LIMIT"], 60.0)
    concurrency = ConcurrencyLimiter(app.config["BOUNDARY_MAX_CONCURRENCY"])

    if cors:
        CORS(
            app,
            origins=list(configured_origins()),
            methods=["GET", "POST"],
            allow_headers=["Authorization", "Content-Type", "X-CSRF-Token", "X-Correlation-ID"],
            expose_headers=["X-Correlation-ID"],
            supports_credentials=True,
        )

    @app.before_request
    def boundary_before_request():
        g.correlation_id = correlation_id(request.headers.get("X-Correlation-ID"))
        g.telemetry_context_token = push_event_context(
            correlation_id=g.correlation_id,
            stage="http_request",
        )
        g.request_started = time.perf_counter()
        METRICS.increment("requests_total", method=request.method, endpoint=request.endpoint or "unknown")
        if request.endpoint == "static" or request.method == "OPTIONS":
            return None
        if request.content_length and request.content_length > limits.request_bytes:
            raise public_error("body_too_large")
        client = request.remote_addr or "unknown"
        if not limiter.allow(f"{client}:{request.endpoint}"):
            raise public_error("rate_limited")
        if not concurrency.acquire():
            raise public_error("rate_limited")
        g.boundary_concurrency_acquired = True
        return None

    @app.after_request
    def boundary_after_request(response: Response):
        if getattr(g, "boundary_concurrency_acquired", False):
            concurrency.release()
            g.boundary_concurrency_acquired = False
        response.headers["X-Correlation-ID"] = getattr(g, "correlation_id", correlation_id())
        started = getattr(g, "request_started", None)
        if started is not None:
            METRICS.observe(
                "request_duration_ms",
                (time.perf_counter() - started) * 1000,
                method=request.method,
                outcome="success" if response.status_code < 400 else "failure",
            )
        return response

    @app.teardown_request
    def boundary_teardown(_error):
        if getattr(g, "boundary_concurrency_acquired", False):
            concurrency.release()
            g.boundary_concurrency_acquired = False
        token = getattr(g, "telemetry_context_token", None)
        if token is not None:
            reset_event_context(token)
            g.telemetry_context_token = None

    @app.errorhandler(PublicError)
    def handle_public_error(error: PublicError):
        request_id = getattr(g, "correlation_id", correlation_id())
        METRICS.increment("request_errors_total", code=error.code)
        return jsonify(public_error_payload(error, request_id)), error.status

    @app.errorhandler(413)
    def handle_large_body(_error):
        error = public_error("body_too_large")
        return jsonify(public_error_payload(error, getattr(g, "correlation_id", correlation_id()))), 413

    @app.errorhandler(404)
    def handle_not_found(_error):
        error = public_error("not_found")
        return jsonify(public_error_payload(error, getattr(g, "correlation_id", correlation_id()))), 404

    @app.errorhandler(500)
    def handle_internal(error):
        request_id = getattr(g, "correlation_id", correlation_id())
        LOGGER.error("request failed correlation_id=%s cause=%s", request_id, redact(type(error).__name__))
        public = public_error("internal_error")
        return jsonify(public_error_payload(public, request_id)), 500


def require_role(required: Role):
    def decorator(function: Callable[P, R]) -> Callable[P, R]:
        @wraps(function)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            request_id = getattr(g, "correlation_id", correlation_id())
            try:
                role = authenticate(request.headers.getlist("Authorization"), required)
            except PublicError:
                audit_event("authentication", "denied", request_id, required=required.name.lower())
                raise
            g.service_role = role
            audit_event(
                "authentication",
                "granted",
                request_id,
                required=required.name.lower(),
                role=role.name.lower(),
            )
            return function(*args, **kwargs)

        return wrapped

    return decorator


def audit_operation(function: Callable[P, R]) -> Callable[P, R]:
    @wraps(function)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        request_id = getattr(g, "correlation_id", correlation_id())
        try:
            result = function(*args, **kwargs)
        except Exception:
            audit_event("administrative_operation", "failed", request_id, endpoint=request.endpoint)
            raise
        audit_event("administrative_operation", "succeeded", request_id, endpoint=request.endpoint)
        return result

    return wrapped


def issue_csrf_cookie(response: Response) -> Response:
    if not request.cookies.get("kb_csrf"):
        response.set_cookie(
            "kb_csrf",
            secrets.token_urlsafe(32),
            httponly=False,
            secure=request.is_secure,
            samesite="Strict",
        )
    return response


def require_browser_mutation(function: Callable[P, R]) -> Callable[P, R]:
    @wraps(function)
    @require_role(Role.ADMIN)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        allowed = set(configured_origins()) | {request.host_url.rstrip("/")}
        origin = request.headers.get("Origin", "").rstrip("/")
        csrf_header = request.headers.get("X-CSRF-Token", "")
        csrf_cookie = request.cookies.get("kb_csrf", "")
        if origin not in allowed or not csrf_header or not secrets.compare_digest(csrf_header, csrf_cookie):
            audit_event(
                "browser_mutation",
                "denied",
                getattr(g, "correlation_id", correlation_id()),
                origin=origin,
            )
            raise public_error("csrf_rejected")
        request_id = getattr(g, "correlation_id", correlation_id())
        try:
            result = function(*args, **kwargs)
        except Exception:
            audit_event("browser_mutation", "failed", request_id, endpoint=request.endpoint)
            raise
        audit_event("browser_mutation", "succeeded", request_id, endpoint=request.endpoint)
        return result

    return wrapped
