from __future__ import annotations

from typing import Any

from se_kb_app.obsidian.models import ExportPlan, VaultStatus
from se_kb_app.obsidian.relationships import RelationshipPage
from se_kb_app.obsidian.service import NoteLocation


def status_payload(status: VaultStatus) -> dict[str, Any]:
    return {
        "availability": status.availability.value,
        "configured": status.configured,
        "available": status.available,
        "vault_name": status.vault_name,
        "managed_directory": status.managed_directory,
        "managed_notes": status.managed_notes,
        "conflicts": status.conflicts,
        "stale": status.stale,
        "last_exported_at": status.last_exported_at.isoformat() if status.last_exported_at else None,
        "corpus_fingerprint": status.corpus_fingerprint,
        "diagnostic": status.diagnostic,
    }


def plan_payload(plan: ExportPlan) -> dict[str, Any]:
    return {
        "corpus_fingerprint": plan.corpus_fingerprint,
        "counts": dict(plan.counts),
        "total": plan.total_actions,
        "offset": plan.offset,
        "limit": plan.limit,
        "partial": plan.partial,
        "diagnostics": list(plan.diagnostics),
        "items": [
            {
                "action": item.action.value,
                "identifier": item.identifier,
                "logical_path": item.logical_path,
                "previous_path": item.previous_path,
                "kind": item.note.identity.kind if item.note else None,
                "reason": item.reason,
            }
            for item in plan.actions
        ],
    }


def relationship_payload(page: RelationshipPage) -> dict[str, Any]:
    return {
        "total": page.total,
        "offset": page.offset,
        "limit": page.limit,
        "partial": page.partial,
        "nodes": [
            {
                "id": node.identifier,
                "title": node.title,
                "kind": node.kind,
                "source": node.source_url,
                "logical_path": node.logical_path,
            }
            for node in page.nodes
        ],
        "edges": [
            {
                "source": edge.source_id,
                "target": edge.target_id,
                "relation": edge.relation,
                "kind": edge.kind.value,
                "score": edge.score,
                "method": edge.method,
                "index_version": edge.index_version,
                "metadata": dict(edge.metadata),
            }
            for edge in page.edges
        ],
    }


def location_payload(location: NoteLocation) -> dict[str, str]:
    return {
        "identifier": location.identifier,
        "logical_path": location.logical_path,
        "obsidian_uri": location.obsidian_uri,
    }

