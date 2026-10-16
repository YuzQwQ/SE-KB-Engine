from __future__ import annotations

import json
from pathlib import Path

import pytest

from extractors.type_registry import KnowledgeType, TypeRegistry
from utils.env_loader import load_env_file
from utils.html_cleaner import clean_html_content, is_html_content
from utils.web_deduplication import WebDeduplication
from validators.jsonschema_validator import make_validator
from vectorizer.chunker import KnowledgeChunker


@pytest.mark.unit
def test_env_loader_respects_existing_values_and_override(tmp_path: Path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("EXISTING=file\nNEW_VALUE=loaded\nEMPTY=\n# comment\n", encoding="utf-8")
    monkeypatch.delenv("SE_KB_SKIP_DOTENV", raising=False)
    monkeypatch.setenv("EXISTING", "process")
    monkeypatch.delenv("NEW_VALUE", raising=False)
    assert load_env_file(env_file) == {"EXISTING": "file", "NEW_VALUE": "loaded"}
    assert load_env_file(env_file, override=False)["EXISTING"] == "file"
    assert __import__("os").environ["EXISTING"] == "process"
    load_env_file(env_file, override=True)
    assert __import__("os").environ["EXISTING"] == "file"


@pytest.mark.unit
def test_env_loader_can_be_disabled(tmp_path: Path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("DO_NOT_LOAD=secret\n", encoding="utf-8")
    monkeypatch.setenv("SE_KB_SKIP_DOTENV", "1")
    monkeypatch.delenv("DO_NOT_LOAD", raising=False)
    assert load_env_file(env_file, override=True) == {}
    assert "DO_NOT_LOAD" not in __import__("os").environ


@pytest.mark.unit
def test_url_normalization_removes_tracking_preserves_query_order(tmp_path: Path):
    dedup = WebDeduplication(str(tmp_path / "dedup.sqlite"))
    normalized = dedup.normalize_url(
        "HTTPS://Example.COM:443/path?b=2&utm_source=test&a=1#fragment"
    )
    assert normalized == "https://example.com/path?b=2&a=1"


@pytest.mark.unit
def test_url_and_content_deduplication_use_temporary_database(tmp_path: Path):
    dedup = WebDeduplication(str(tmp_path / "dedup.sqlite"))
    url = "https://example.com/article"
    content = "A stable piece of knowledge with enough words."
    assert dedup.check_and_add(url, content, "first")["should_skip"] is False
    duplicate = dedup.check_and_add(f"{url}?utm_source=again", content, "second")
    assert duplicate["url_duplicate"] is True
    assert duplicate["should_skip"] is True


@pytest.mark.unit
def test_html_detection_and_cleaning_preserve_article_text():
    source = "<html><body><nav>menu</nav><article><h1>标题</h1><p>正文内容</p></article></body></html>"
    assert is_html_content(source) is True
    cleaned = clean_html_content(source)
    assert "标题" in cleaned
    assert "正文内容" in cleaned
    assert "<article>" not in cleaned


@pytest.mark.unit
def test_concept_chunking_has_stable_id_and_metadata(tmp_path: Path):
    source = tmp_path / "concepts.json"
    source.write_text(
        json.dumps({"elements": [{"id": "entity", "name": "外部实体", "definition": "系统边界之外"}]}),
        encoding="utf-8",
    )
    chunks = KnowledgeChunker().chunk_file(source, "diagrams.dfd.concepts")
    assert [chunk.id for chunk in chunks] == ["concepts_entity"]
    assert chunks[0].metadata["knowledge_type"] == "diagrams.dfd.concepts"
    assert "系统边界之外" in chunks[0].text


@pytest.mark.unit
def test_jsonschema_validator_reports_nested_failure(tmp_path: Path):
    schema = tmp_path / "schema.json"
    schema.write_text(
        json.dumps(
            {
                "type": "object",
                "required": ["item"],
                "properties": {"item": {"type": "object", "required": ["name"]}},
            }
        ),
        encoding="utf-8",
    )
    validate = make_validator()
    assert validate({"item": {"name": "ok"}}, str(schema)) == (True, [])
    valid, errors = validate({"item": {}}, str(schema))
    assert valid is False
    assert errors and "name" in errors[0]


@pytest.mark.unit
def test_type_registry_filters_disabled_types():
    registry = TypeRegistry()
    disabled = KnowledgeType(
        type_id="fixture.disabled",
        name="Disabled",
        brief="fixture",
        description="fixture",
        schema_path=None,
        prompt_path=None,
        enabled=False,
    )
    registry.register(disabled)
    assert registry.get("fixture.disabled") is disabled
    assert disabled not in registry.get_enabled()
