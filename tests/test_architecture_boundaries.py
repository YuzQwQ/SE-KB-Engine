from __future__ import annotations

import ast
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent.parent
DOMAIN_FILES = [ROOT / "se_kb_app" / "domain.py", ROOT / "se_kb_app" / "errors.py"]
SERVICE_FILES = sorted((ROOT / "se_kb_app" / "services").glob("*.py"))


def imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


@pytest.mark.unit
def test_domain_has_no_transport_or_infrastructure_imports():
    banned = {"flask", "mcp", "httpx", "openai", "chromadb", "playwright", "vectorizer"}
    for path in DOMAIN_FILES:
        assert imported_roots(path).isdisjoint(banned), path


@pytest.mark.unit
def test_application_services_have_no_transport_imports_or_silent_passes():
    for path in SERVICE_FILES:
        assert imported_roots(path).isdisjoint({"flask", "mcp"}), path
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        assert not any(isinstance(node, ast.Pass) for node in ast.walk(tree)), path


@pytest.mark.unit
@pytest.mark.parametrize(
    ("path", "function"),
    [
        (ROOT / "api" / "app.py", "create_app"),
        (ROOT / "web" / "app.py", "bind_application"),
        (ROOT / "start_web.py", "main"),
        (ROOT / "scripts" / "query_knowledge.py", "main"),
        (ROOT / "server.py", "configure_application"),
    ],
)
def test_runtime_entrypoints_accept_an_application_instance(path: Path, function: str):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    definition = next(
        node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function
    )
    argument_names = {argument.arg for argument in (*definition.args.args, *definition.args.kwonlyargs)}
    assert "application" in argument_names or "instance" in argument_names
