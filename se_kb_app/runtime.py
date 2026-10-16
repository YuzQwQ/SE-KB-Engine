from __future__ import annotations

from threading import Lock

from se_kb_app.composition import Application, create_application


_default_application: Application | None = None
_lock = Lock()


def get_default_application() -> Application:
    """Compatibility shim for legacy entry points; new code injects Application."""
    global _default_application
    if _default_application is None:
        with _lock:
            if _default_application is None:
                _default_application = create_application()
    return _default_application


def set_default_application(application: Application) -> None:
    global _default_application
    with _lock:
        _default_application = application
