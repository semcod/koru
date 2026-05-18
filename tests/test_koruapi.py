"""Tests for koruapi package."""

from __future__ import annotations

from pathlib import Path

import pytest

from koruapi import list_integrations
from koruapi.invoke import InvokeError, invoke_integration


def test_list_integrations_has_dsl_and_scan() -> None:
    ids = {s.id for s in list_integrations()}
    assert "dsl.to_library" in ids
    assert "scan.apply" in ids
    assert "autopilot.drive" in ids


def test_dsl_roundtrip_invoke() -> None:
    result = invoke_integration(
        "dsl.roundtrip",
        project=Path("."),
        body={"dsl": "GOAL: t\nSET a=1\n"},
    )
    assert result["ok"] is True


def test_unknown_integration() -> None:
    with pytest.raises(InvokeError):
        invoke_integration("no.such.integration", project=Path("."))


def test_openapi_document_lists_invoke_path() -> None:
    from koruapi.openapi import build_openapi_document

    doc = build_openapi_document()
    assert doc["openapi"].startswith("3.")
    assert "/api/v1/invoke" in doc["paths"]
    assert "dsl.roundtrip" in doc["paths"]["/api/v1/invoke"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]["properties"]["integration_id"]["enum"]
