import os
from pathlib import Path
from typing import Dict, Optional


def load_env_file(env_path: Optional[Path] = None, override: bool = False) -> Dict[str, str]:
    path = env_path or Path(".env")
    loaded: Dict[str, str] = {}
    if not path.exists():
        return loaded
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if not key or not value:
            continue
        loaded[key] = value
        if override or os.getenv(key) is None:
            os.environ[key] = value
    return loaded
