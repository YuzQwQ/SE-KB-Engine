from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable, Sequence
from urllib.parse import quote, urlencode

from se_kb_app.domain import Cancellation
from se_kb_app.errors import ApplicationError, ErrorKind
from se_kb_app.obsidian.canvas import generate_canvas
from se_kb_app.obsidian.models import ExportPlan, ExportResult, RelationshipEdge, RelationshipKind, VaultAvailability, VaultStatus
from se_kb_app.obsidian.paths import VaultPathPolicy, inspect_vault
from se_kb_app.obsidian.planning import ExportPlanner
from se_kb_app.obsidian.projection import KnowledgeProjector, ProjectionResult
from se_kb_app.obsidian.publishing import VaultBusyError, VaultPublisher
from se_kb_app.obsidian.relationships import RelationshipPage, RelationshipQueryService, explicit_edges
from se_kb_app.obsidian.source import ArtifactKnowledgeSource, KnowledgeReadResult, KnowledgeSelection
from se_kb_app.obsidian.state_store import ExportStateStore, StateLoadResult
from se_kb_app.settings import AppSettings


SemanticProvider = Callable[[KnowledgeReadResult], Sequence[RelationshipEdge]]


@dataclass(frozen=True)
class VaultBuild:
    read: KnowledgeReadResult
    projection: ProjectionResult
    relationships: tuple[RelationshipEdge, ...]
    state: StateLoadResult
    plan: ExportPlan


@dataclass(frozen=True)
class NoteLocation:
    identifier: str
    logical_path: str
    obsidian_uri: str


class ObsidianVaultService:
    def __init__(
        self,
        settings: AppSettings,
        *,
        artifact_root: Path | None = None,
        semantic_provider: SemanticProvider | None = None,
    ) -> None:
        self.settings = settings
        self.obsidian = settings.obsidian
        self.artifact_root = artifact_root or settings.paths.project / "se_kb" / "artifacts"
        self.semantic_provider = semantic_provider
        self._policy: VaultPathPolicy | None = None
        self._state_store: ExportStateStore | None = None
        self._publisher: VaultPublisher | None = None
        if self.obsidian.enabled:
            self._policy = VaultPathPolicy.from_settings(self.obsidian)
            self._state_store = ExportStateStore(self._policy)
            self._publisher = VaultPublisher(self._policy, self._state_store)

    def status(self) -> VaultStatus:
        status = inspect_vault(self.obsidian)
        if not status.configured or self._state_store is None or status.availability is VaultAvailability.UNAVAILABLE:
            return status
        loaded = self._state_store.load()
        if loaded.read_only:
            return replace(
                status,
                availability=VaultAvailability.READ_ONLY,
                available=False,
                diagnostic=loaded.diagnostic,
            )
        state = loaded.state
        if state is None:
            return status
        return replace(
            status,
            managed_notes=len(state.notes),
            last_exported_at=state.exported_at,
            corpus_fingerprint=state.corpus_fingerprint,
        )

    def preview(self, selection: KnowledgeSelection, *, offset: int = 0, limit: int = 100) -> ExportPlan:
        return self._build(selection, offset=offset, limit=limit).plan

    def export(
        self,
        selection: KnowledgeSelection,
        *,
        cancellation: Cancellation | None = None,
        progress: Callable[[int, int, str], None] | None = None,
    ) -> ExportResult:
        reporter = progress or (lambda _completed, _total, _message: None)
        reporter(10, 100, "Reading artifacts")
        build = self._build(selection, offset=0, limit=None)
        if build.state.read_only:
            raise self._error("obsidian_state_read_only", "The Vault export state requires operator review.")
        if cancellation is not None:
            cancellation.checkpoint()
        reporter(45, 100, "Publishing managed notes")
        assert self._publisher is not None
        try:
            result = self._publisher.publish(
                build.plan,
                vault_name=self.obsidian.vault_name or self._required_policy().vault_root.name,
                previous=build.state.state,
                cancellation=cancellation,
            )
        except VaultBusyError as error:
            raise self._error("obsidian_export_busy", "A Vault export is already active.", cause=error) from error
        reporter(100, 100, "Vault export completed")
        return result

    def relationships(
        self,
        selection: KnowledgeSelection,
        *,
        node: str | None = None,
        kind: RelationshipKind | None = None,
        source: str | None = None,
        minimum_score: float = 0.0,
        offset: int = 0,
        limit: int = 100,
    ) -> RelationshipPage:
        build = self._build(selection, offset=0, limit=1)
        query = RelationshipQueryService(
            build.read.records,
            build.relationships,
            path_map=build.projection.path_map,
            maximum_limit=self.obsidian.graph_node_limit,
        )
        return query.query(
            node=node,
            kind=kind,
            source=source,
            minimum_score=minimum_score,
            offset=offset,
            limit=limit,
        )

    def note_location(self, identifier: str) -> NoteLocation:
        self._require_ready()
        assert self._state_store is not None
        loaded = self._state_store.load()
        if loaded.state is None:
            raise self._error("obsidian_note_not_found", "The requested exported note does not exist.")
        note = next((item for item in loaded.state.notes if item.identifier == identifier), None)
        if note is None:
            raise self._error("obsidian_note_not_found", "The requested exported note does not exist.")
        vault_name = self.obsidian.vault_name or self._required_policy().vault_root.name
        uri = "obsidian://open?" + urlencode(
            {"vault": vault_name, "file": note.logical_path},
            quote_via=quote,
        )
        return NoteLocation(identifier, note.logical_path, uri)

    def close(self) -> None:
        return None

    def _build(self, selection: KnowledgeSelection, *, offset: int, limit: int | None) -> VaultBuild:
        self._require_ready()
        state_store = self._required_state_store()
        loaded = state_store.load()
        read = ArtifactKnowledgeSource(self.artifact_root).read(selection)
        relations = list(explicit_edges(read.records))
        if self.obsidian.semantic_edges and self.semantic_provider is not None:
            relations.extend(self.semantic_provider(read))
        prior_titles = {
            item.identifier: item.title for item in loaded.state.notes
        } if loaded.state else {}
        projection = KnowledgeProjector().project(
            read.records,
            relationships=tuple(relations),
            previous_titles=prior_titles,
        )
        if self.obsidian.canvas_enabled:
            canvas = generate_canvas(
                read.records,
                projection.path_map,
                tuple(relations),
                maximum_nodes=self.obsidian.graph_node_limit,
            )
            projection = ProjectionResult(
                (*projection.notes, canvas),
                {**projection.path_map, canvas.identity.identifier: canvas.logical_path},
                projection.diagnostics,
            )
        configuration = {
            "managed_directory": self.obsidian.managed_directory,
            "entity_kinds": self.obsidian.entity_kinds,
            "semantic_edges": self.obsidian.semantic_edges,
            "semantic_min_score": self.obsidian.semantic_min_score,
            "semantic_max_neighbors": self.obsidian.semantic_max_neighbors,
            "canvas_enabled": self.obsidian.canvas_enabled,
        }
        plan = ExportPlanner(self._required_policy()).plan(
            projection.notes,
            loaded.state,
            configuration=configuration,
            offset=offset,
            limit=limit,
        )
        diagnostics = tuple(sorted(set((*plan.diagnostics, *read.diagnostics, *projection.diagnostics))))
        if diagnostics != plan.diagnostics:
            plan = replace(plan, diagnostics=diagnostics)
        return VaultBuild(read, projection, tuple(relations), loaded, plan)

    def _require_ready(self) -> None:
        status = inspect_vault(self.obsidian)
        if status.availability is VaultAvailability.NOT_CONFIGURED:
            raise self._error("obsidian_not_configured", "Obsidian integration is not configured.")
        if status.availability is VaultAvailability.UNAVAILABLE:
            raise self._error("obsidian_unavailable", "The configured Obsidian Vault is unavailable.")
        if status.availability is VaultAvailability.READ_ONLY:
            raise self._error("obsidian_read_only", "The configured Obsidian Vault is read-only.")

    def _required_policy(self) -> VaultPathPolicy:
        if self._policy is None:
            raise self._error("obsidian_not_configured", "Obsidian integration is not configured.")
        return self._policy

    def _required_state_store(self) -> ExportStateStore:
        if self._state_store is None:
            raise self._error("obsidian_not_configured", "Obsidian integration is not configured.")
        return self._state_store

    @staticmethod
    def _error(code: str, message: str, *, cause: BaseException | None = None) -> ApplicationError:
        return ApplicationError(ErrorKind.STORAGE, code, message, retryable=False, cause=cause)


def create_obsidian_service(settings: AppSettings) -> ObsidianVaultService:
    return ObsidianVaultService(settings)
