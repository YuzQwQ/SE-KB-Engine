from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from se_kb_app.errors import ApplicationError
from se_kb_app.obsidian.models import NoteIdentity, RelationshipEdge, RelationshipKind
from se_kb_app.obsidian.paths import (
    VaultPathPolicy,
    build_note_path_map,
    inspect_vault,
    sanitize_note_title,
)
from se_kb_app.obsidian.state import ExportState
from se_kb_app.settings import AppSettings


FIXTURES = Path(__file__).parent / "fixtures" / "obsidian_state"
SCHEMA = Path(__file__).parents[1] / "schemas" / "obsidian-export-state-v1.schema.json"


@pytest.mark.unit
def test_obsidian_settings_are_disabled_by_default_and_accept_nested_configuration(tmp_path: Path):
    disabled = AppSettings.from_sources(environ={}, overrides={"project_root": tmp_path})
    assert disabled.obsidian.enabled is False
    assert inspect_vault(disabled.obsidian).availability.value == "not_configured"

    vault = tmp_path / "vault"
    vault.mkdir()
    config = tmp_path / "application.toml"
    config.write_text(
        "[obsidian]\n"
        f'vault_root = "{vault.as_posix()}"\n'
        'vault_name = "Research"\n'
        'managed_directory = "Generated/SE-KB"\n'
        'entity_kinds = ["concept", "rule"]\n'
        "semantic_edges = false\n"
        "semantic_min_score = 0.8\n"
        "semantic_max_neighbors = 3\n"
        "graph_node_limit = 250\n",
        encoding="utf-8",
    )
    settings = AppSettings.from_sources(config_file=config, environ={})
    assert settings.obsidian.enabled is True
    assert settings.obsidian.vault_root == vault.resolve()
    assert settings.obsidian.managed_directory == "Generated/SE-KB"
    assert settings.obsidian.entity_kinds == ("concept", "rule")
    assert settings.obsidian.semantic_edges is False


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("obsidian_managed_directory", "../outside"),
        ("obsidian_entity_kinds", []),
        ("obsidian_semantic_min_score", 1.5),
        ("obsidian_semantic_max_neighbors", 101),
        ("obsidian_graph_node_limit", 2),
    ],
)
def test_invalid_obsidian_settings_return_safe_configuration_errors(tmp_path: Path, field, value):
    with pytest.raises(ApplicationError) as caught:
        AppSettings.from_sources(environ={}, overrides={"project_root": tmp_path, field: value})
    assert caught.value.public_code == "invalid_configuration"
    assert caught.value.metadata["setting"] == field
    assert str(tmp_path) not in str(caught.value)


@pytest.mark.unit
def test_obsidian_models_are_immutable_and_semantic_edges_require_provenance():
    identity = NoteIdentity("concept_a", "概念 A", "concept")
    with pytest.raises(FrozenInstanceError):
        setattr(identity, "title", "changed")
    edge = RelationshipEdge(
        "concept_a",
        "concept_b",
        "similar_to",
        RelationshipKind.SEMANTIC,
        score=0.91,
        method="cosine",
    )
    assert edge.kind is RelationshipKind.SEMANTIC
    with pytest.raises(ValueError, match="score and method"):
        RelationshipEdge("a", "b", "similar_to", RelationshipKind.SEMANTIC)


@pytest.mark.unit
def test_export_state_schema_and_parser_accept_current_and_reject_bad_fixtures():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    accepted = json.loads((FIXTURES / "accepted.json").read_text(encoding="utf-8"))
    validator.validate(accepted)
    state = ExportState.from_dict(accepted)
    assert state.notes[0].identifier == "doc_example"

    for name in ("unsupported-newer.json", "malformed.json"):
        value = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
        assert list(validator.iter_errors(value))
        with pytest.raises(ValueError):
            ExportState.from_dict(value)
    with pytest.raises(json.JSONDecodeError):
        json.loads((FIXTURES / "partial.json").read_text(encoding="utf-8"))


@pytest.mark.unit
@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("  A  B  ", "A-B"),
        ("CON", "note-CON"),
        ("..", "untitled"),
        ("数据：[测试] / 图谱", "数据-测试-图谱"),
        ("ＡＢＣ", "ABC"),
    ],
)
def test_note_title_sanitization_is_cross_platform_and_deterministic(title, expected):
    assert sanitize_note_title(title) == expected


@pytest.mark.unit
def test_note_path_map_is_stable_collision_safe_and_bounded():
    identities = [
        NoteIdentity("doc_1", "Same", "source"),
        NoteIdentity("doc_2", "same", "source"),
        NoteIdentity("concept_1", "x" * 500, "concept"),
    ]
    first = build_note_path_map(identities, maximum_path=140)
    second = build_note_path_map(reversed(identities), maximum_path=140)
    assert first == second
    assert len({path.casefold() for path in first.values()}) == 3
    assert all(len(path) <= 140 and path.endswith(".md") for path in first.values())


@pytest.mark.security
def test_vault_path_policy_rejects_traversal_absolute_and_link_escape(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()
    settings = AppSettings.from_sources(
        environ={},
        overrides={"project_root": tmp_path, "obsidian_vault_root": vault},
    ).obsidian
    policy = VaultPathPolicy.from_settings(settings)
    assert policy.destination("Sources/note.md") == vault / "SE-KB" / "Sources" / "note.md"
    for unsafe in ("../note.md", "/absolute.md", "C:/outside.md", "Sources/a.txt", "Sources/\x00.md"):
        with pytest.raises(ValueError):
            policy.destination(unsafe)

    outside = tmp_path / "outside"
    outside.mkdir()
    policy.managed_root.mkdir()
    linked = policy.managed_root / "linked"
    try:
        linked.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symbolic links are unavailable on this host")
    with pytest.raises(ValueError, match="escapes"):
        policy.destination("linked/note.md")


@pytest.mark.unit
def test_vault_status_is_redacted_for_missing_root(tmp_path: Path):
    missing = tmp_path / "private" / "vault"
    settings = AppSettings.from_sources(
        environ={},
        overrides={"project_root": tmp_path, "obsidian_vault_root": missing},
    ).obsidian
    status = inspect_vault(settings)
    assert status.availability.value == "unavailable"
    assert status.diagnostic == "vault_unavailable"
    assert str(missing) not in repr(status)
