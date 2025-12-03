import os
import json
import hashlib
from pathlib import Path
from datetime import datetime

class ArtifactsWriter:
    def _slug(self, title: str, url: str) -> str:
        t = (title or "untitled").strip().replace(" ", "-")
        h = hashlib.md5((url or "").encode("utf-8")).hexdigest()[:8]
        return f"{t[:60]}-{h}"

    def _base_dir(self) -> Path:
        return Path("se_kb/artifacts")

    def write(self, domain: str, title: str, parsed: dict, document_text: str, t: str, artifact: dict, trace: dict, metadata: dict, metrics: dict, errors: list = None) -> dict:
        now = datetime.now()
        base = self._base_dir() / now.strftime("%Y") / now.strftime("%m") / now.strftime("%d") / (domain or "unknown")
        slug = self._slug(title, parsed.get("source_url") or parsed.get("url") or "")
        out = base / slug
        out.mkdir(parents=True, exist_ok=True)
        (out / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        (out / "parsed.json").write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
        (out / "document.md").write_text(document_text or "", encoding="utf-8")
        (out / "trace.json").write_text(json.dumps(trace or {}, ensure_ascii=False, indent=2), encoding="utf-8")
        (out / "metrics.json").write_text(json.dumps(metrics or {}, ensure_ascii=False, indent=2), encoding="utf-8")
        if errors is not None:
            (out / "errors.json").write_text(json.dumps(errors, ensure_ascii=False, indent=2), encoding="utf-8")
        if artifact is not None:
            (out / f"{t}.json").write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"dir": str(out), "type": t}