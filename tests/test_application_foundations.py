from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from se_kb_app.domain import FetchRequest, RetrievalRequest, SearchRequest
from se_kb_app.errors import ApplicationError, ErrorKind, configuration_error, wrap_error
from se_kb_app.paths import ProjectPaths
from se_kb_app.retry import should_retry
from se_kb_app.settings import AppSettings, SearchEngine


@pytest.mark.unit
def test_settings_precedence_is_defaults_then_file_then_environment_then_explicit(tmp_path: Path):
    config = tmp_path / "application.toml"
    config.write_text(
        'search_engine = "bing"\nhttp_timeout_seconds = 10\nhttp_max_retries = 1\n',
        encoding="utf-8",
    )
    settings = AppSettings.from_sources(
        config_file=config,
        environ={"DEFAULT_SEARCH_ENGINE": "baidu", "HTTP_TIMEOUT_SECONDS": "15"},
        overrides={"search_engine": "duckduckgo", "project_root": tmp_path},
    )
    assert settings.search_engine is SearchEngine.DUCKDUCKGO
    assert settings.http_timeout_seconds == 15
    assert settings.http_max_retries == 1
    with pytest.raises(FrozenInstanceError):
        settings.http_max_retries = 2  # type: ignore[misc]


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("http_timeout_seconds", "secret-invalid-timeout"),
        ("http_max_retries", 99),
        ("model_base_url", "file:///secret"),
        ("search_engine", "unknown"),
        ("use_tor", "sometimes"),
    ],
)
def test_invalid_settings_are_safe_and_actionable(field, value, tmp_path: Path):
    marker = "secret-invalid-timeout"
    with pytest.raises(ApplicationError) as caught:
        AppSettings.from_sources(overrides={"project_root": tmp_path, field: value})
    assert caught.value.kind is ErrorKind.CONFIGURATION
    assert "Invalid setting" in str(caught.value)
    assert caught.value.metadata["setting"] == field
    assert marker not in str(caught.value)


@pytest.mark.unit
def test_sensitive_setting_is_excluded_from_repr(tmp_path: Path):
    settings = AppSettings.from_sources(
        environ={},
        overrides={"project_root": tmp_path, "model_api_key": "never-print-this"},
    )
    assert "never-print-this" not in repr(settings)


@pytest.mark.unit
def test_paths_do_not_depend_on_process_working_directory(tmp_path: Path, monkeypatch):
    project = tmp_path / "project"
    elsewhere = tmp_path / "elsewhere"
    project.mkdir()
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    paths = ProjectPaths.resolve(project, data_root="runtime/data", output_root="artifacts")
    assert paths.project == project.resolve()
    assert paths.data == project / "runtime" / "data"
    assert paths.output == project / "artifacts"
    assert Path.cwd() == elsewhere


@pytest.mark.unit
def test_typed_error_retains_safe_contract_retryability_metadata_and_cause():
    cause = TimeoutError("private upstream detail")
    error = wrap_error(
        ErrorKind.NETWORK,
        "upstream_timeout",
        "The upstream service timed out.",
        retryable=True,
        cause=cause,
        metadata={"operation": "fetch"},
    )
    assert error.public_code == "upstream_timeout"
    assert error.retryable is True
    assert error.metadata == {"operation": "fetch"}
    assert error.cause is cause
    assert "private upstream detail" not in str(error)


@pytest.mark.unit
def test_retry_decision_never_matches_exception_messages():
    retryable = wrap_error(
        ErrorKind.NETWORK,
        "network_failed",
        "Network request failed.",
        retryable=True,
        cause=RuntimeError("anything"),
    )
    non_retryable = configuration_error("url", "Use HTTP or HTTPS.")
    misleading = RuntimeError("proxy timeout connection reset retry me")
    assert should_retry(retryable) is True
    assert should_retry(non_retryable) is False
    assert should_retry(misleading) is False


@pytest.mark.unit
def test_boundary_dtos_are_immutable_values():
    assert SearchRequest("q", 3).limit == 3
    assert FetchRequest("https://example.com").save is False
    assert RetrievalRequest("q").top_k == 5
