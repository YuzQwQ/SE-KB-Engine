from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Mapping


def capability_status(*, retriever: object | None) -> dict[str, str]:
    model_ready = bool(os.getenv("OPENAI_API_KEY") and os.getenv("MODEL"))
    browser_ready = importlib.util.find_spec("playwright") is not None
    tor_enabled = os.getenv("USE_TOR", "").lower() in {"1", "true", "yes"}
    tor_path = os.getenv("TOR_EXECUTABLE_PATH", "")
    tor_ready = bool(tor_enabled and tor_path and Path(tor_path).is_file())
    return {
        "retriever": "available" if retriever is not None else "unavailable",
        "model": "available" if model_ready else "unconfigured",
        "browser": "available" if browser_ready else "unavailable",
        "tor": "available" if tor_ready else "unavailable" if tor_enabled else "disabled",
    }


def readiness_status(*, retriever: object | None) -> tuple[bool, Mapping[str, str]]:
    capabilities = capability_status(retriever=retriever)
    required_ready = capabilities["retriever"] == "available"
    return required_ready, capabilities
