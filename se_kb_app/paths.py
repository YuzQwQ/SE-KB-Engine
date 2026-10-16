from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    project: Path
    config: Path
    data: Path
    cache: Path
    output: Path

    @classmethod
    def resolve(
        cls,
        project_root: str | Path | None = None,
        *,
        config_root: str | Path | None = None,
        data_root: str | Path | None = None,
        cache_root: str | Path | None = None,
        output_root: str | Path | None = None,
    ) -> "ProjectPaths":
        project = (
            Path(project_root).expanduser().resolve()
            if project_root is not None
            else Path(__file__).resolve().parents[1]
        )

        def under(value: str | Path | None, default: str) -> Path:
            candidate = Path(value).expanduser() if value is not None else Path(default)
            return candidate.resolve() if candidate.is_absolute() else (project / candidate).resolve()

        return cls(
            project=project,
            config=under(config_root, "config"),
            data=under(data_root, "data"),
            cache=under(cache_root, ".cache"),
            output=under(output_root, "output"),
        )
