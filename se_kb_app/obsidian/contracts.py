from __future__ import annotations

from typing import Protocol, Sequence

from se_kb_app.domain import Cancellation
from se_kb_app.obsidian.models import ExportPlan, ExportResult, ProjectedNote, RelationshipEdge
from se_kb_app.obsidian.state import ExportState


class VaultPlanner(Protocol):
    def plan(self, notes: Sequence[ProjectedNote], previous: ExportState | None, **kwargs) -> ExportPlan: ...


class VaultRenderer(Protocol):
    def render(self, *args, **kwargs) -> tuple[ProjectedNote, tuple[str, ...]]: ...


class VaultRelationshipProvider(Protocol):
    def edges(self, *args, **kwargs) -> Sequence[RelationshipEdge]: ...


class VaultStateStore(Protocol):
    def load(self): ...
    def save(self, state: ExportState) -> None: ...


class VaultPublisherContract(Protocol):
    def publish(
        self,
        plan: ExportPlan,
        *,
        vault_name: str,
        previous: ExportState | None = None,
        cancellation: Cancellation | None = None,
    ) -> ExportResult: ...

