from __future__ import annotations

import logging

import pytest

from service_boundary.audit import audit_event, install_secret_redaction, redact
from service_boundary.auth import Role, authenticate, parse_bearer
from service_boundary.errors import PublicError, correlation_id, public_error, public_error_payload
from service_boundary.inputs import (
    InputLimits,
    boolean_field,
    confined_path,
    date_field,
    integer_field,
    object_body,
    path_component,
    string_field,
    string_list_field,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    "headers",
    [[], [""], ["token"], ["Basic token"], ["Bearer"], ["Bearer one two"], ["Bearer a,b"]],
)
def test_bearer_parser_rejects_missing_malformed_and_duplicate_values(headers):
    with pytest.raises(PublicError) as caught:
        parse_bearer(headers)
    assert caught.value.code == "unauthorized"


@pytest.mark.unit
def test_authentication_distinguishes_read_admin_and_invalid(monkeypatch):
    monkeypatch.setenv("KB_READ_KEYS", "read-key, second-read")
    monkeypatch.setenv("KB_ADMIN_KEYS", "admin-key")
    assert authenticate(["Bearer read-key"], Role.READ) is Role.READ
    assert authenticate(["bearer admin-key"], Role.READ) is Role.ADMIN
    assert authenticate(["Bearer admin-key"], Role.ADMIN) is Role.ADMIN
    with pytest.raises(PublicError) as denied:
        authenticate(["Bearer read-key"], Role.ADMIN)
    assert denied.value.code == "forbidden"
    with pytest.raises(PublicError) as invalid:
        authenticate(["Bearer read-key-prefix"], Role.READ)
    assert invalid.value.code == "unauthorized"


@pytest.mark.unit
def test_authentication_defaults_to_deny_when_no_keys_are_configured(monkeypatch):
    monkeypatch.delenv("KB_READ_KEYS", raising=False)
    monkeypatch.delenv("KB_ADMIN_KEYS", raising=False)
    with pytest.raises(PublicError):
        authenticate(["Bearer anything"], Role.READ)


@pytest.mark.unit
def test_credentials_and_prefixes_never_enter_audit_logs(monkeypatch, caplog):
    secret = "prefix-very-secret-value"
    monkeypatch.setenv("KB_READ_KEYS", secret)
    caplog.set_level(logging.INFO, logger="se-kb.audit")
    with pytest.raises(PublicError):
        authenticate([f"Bearer {secret}-wrong"], Role.READ)
    audit_event("authentication", "denied", "request-123", authorization=f"Bearer {secret}")
    output = caplog.text
    assert secret not in output
    assert "prefix-very" not in output
    assert "Bearer [REDACTED]" in redact(f"Bearer {secret}")


@pytest.mark.unit
def test_global_log_filter_redacts_configured_secret_and_prefix(monkeypatch, caplog):
    secret = "abcdefgh-super-secret"
    monkeypatch.setenv("OPENAI_API_KEY", secret)
    install_secret_redaction()
    caplog.set_level(logging.ERROR)
    logging.getLogger("arbitrary.component").error("upstream echoed %s and abcdefgh", secret)
    assert secret not in caplog.text
    assert "abcdefgh" not in caplog.text


@pytest.mark.unit
def test_public_error_envelope_is_stable_and_safe():
    request_id = correlation_id("request-123")
    payload = public_error_payload(public_error("invalid_field", field="top_k"), request_id)
    assert payload == {
        "error": {
            "code": "invalid_field",
            "message": "A request field is invalid.",
            "correlation_id": "request-123",
            "field": "top_k",
        }
    }
    assert correlation_id("bad id") != "bad id"


@pytest.mark.unit
def test_typed_input_validation_covers_common_external_fields():
    limits = InputLimits()
    body = object_body(
        {"query": " search ", "top_k": 5, "enabled": True, "types": ["concept"]}
    )
    assert string_field(body, "query", required=True, max_length=limits.query_chars) == "search"
    assert integer_field(body, "top_k", default=3, minimum=1, maximum=limits.top_k_max) == 5
    assert boolean_field(body, "enabled", default=False) is True
    assert string_list_field(body, "types", maximum=limits.list_items_max) == ["concept"]
    assert date_field("2026/09/15") == "2026/09/15"
    assert path_component("12_30_00", "time") == "12_30_00"


@pytest.mark.unit
def test_output_paths_are_confined_to_the_configured_root(tmp_path):
    root = tmp_path / "knowledge"
    assert confined_path(root, "batch") == root / "batch"
    with pytest.raises(PublicError):
        confined_path(root, "../outside")


@pytest.mark.unit
@pytest.mark.parametrize(
    ("function", "args"),
    [
        (object_body, ([],)),
        (integer_field, ({"top_k": True}, "top_k")),
        (boolean_field, ({"enabled": "yes"}, "enabled")),
        (date_field, ("../../etc",)),
        (path_component, ("../secret", "time")),
    ],
)
def test_typed_input_validation_rejects_ambiguous_values(function, args):
    kwargs = {}
    if function is integer_field:
        kwargs = {"default": 5, "minimum": 1, "maximum": 100}
    elif function is boolean_field:
        kwargs = {"default": False}
    with pytest.raises(PublicError):
        function(*args, **kwargs)
